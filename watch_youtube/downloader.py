"""Download YouTube transcripts, audio, and video with multi-strategy fallback."""

import re
import time
import logging
import os
from pathlib import Path
from typing import Optional

import yt_dlp
import webvtt
import requests

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False

from . import DownloadResult, TranscriptEntry

logger = logging.getLogger(__name__)

# Invidious instances (prioritized by speed/reliability)
INVIDIOUS_INSTANCES = [
    "https://invidious.jing.rocks",
    "https://iv.ggtyler.dev",
    "https://invidious.privacyredirect.com",
    "https://inv.vern.cc",
]

_TIMECODE_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d+)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return "unknown"


def _parse_timestamp(ts_str: str) -> float:
    """Parse HH:MM:SS.mmm or MM:SS.mmm to seconds."""
    try:
        parts = ts_str.replace(',', '.').split(':')
        hours = int(parts[0]) if len(parts) > 2 else 0
        minutes = int(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[-1])
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0.0


def _get_transcript_api(video_id: str) -> Optional[list[TranscriptEntry]]:
    """Strategy 1: Use youtube-transcript-api (no bot detection)."""
    if not TRANSCRIPT_API_AVAILABLE:
        logger.debug("youtube-transcript-api not available")
        return None

    try:
        logger.info(f"[1/4] Trying youtube-transcript-api for {video_id}...")
        # Try multiple languages
        transcripts = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=['en', 'tr', 'es', 'fr', 'de', 'pt', 'ja', 'zh-Hans']
        )

        entries = []
        for item in transcripts:
            start = item['start']
            duration = item.get('duration', 0)
            entries.append(TranscriptEntry(
                start_sec=start,
                end_sec=start + duration,
                text=item['text'].strip()
            ))

        logger.info(f"✓ Transcript downloaded via youtube-transcript-api ({len(entries)} segments)")
        return entries if entries else None
    except (TranscriptsDisabled, NoTranscriptFound):
        logger.debug(f"Transcripts disabled or not found for {video_id}")
        return None
    except Exception as e:
        logger.debug(f"youtube-transcript-api failed: {type(e).__name__}: {e}")
        return None


def _get_transcript_ytdlp_oauth(url: str, video_id: str, output_dir: Path) -> Optional[list[TranscriptEntry]]:
    """Strategy 2: Use yt-dlp with OAuth2 cookie (if available)."""
    try:
        cookie_file = os.path.expanduser("~/.youtube_cookies.txt")
        if not os.path.exists(cookie_file):
            logger.debug("No YouTube cookies found at ~/.youtube_cookies.txt")
            return None

        logger.info(f"[2/4] Trying yt-dlp with cookies for {video_id}...")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "allsubtitles": False,
            "subtitleslangs": ["en", "en-US"],
            "subtitlesformat": "vtt",
            "skip_download": True,
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "cookies": cookie_file,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # Look for downloaded subtitle file
        for ext in ("vtt", "srt"):
            matches = list(output_dir.glob(f"{video_id}*.{ext}"))
            if matches:
                result = _parse_transcript_file(matches[0], ext)
                logger.info(f"✓ Transcript downloaded via yt-dlp with cookies")
                return result

    except Exception as e:
        logger.debug(f"yt-dlp cookies failed: {type(e).__name__}: {e}")

    return None


def _get_transcript_invidious(video_id: str) -> Optional[list[TranscriptEntry]]:
    """Strategy 3: Use Invidious proxy (no bot detection, privacy-focused)."""
    logger.info(f"[3/4] Trying Invidious proxy for {video_id}...")

    for instance in INVIDIOUS_INSTANCES:
        try:
            # Invidious API endpoint for video info with captions
            url = f"{instance}/api/v1/videos/{video_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            captions = data.get('captions', [])

            if not captions:
                logger.debug(f"No captions in {instance}")
                continue

            # Get the first English caption track
            caption = next((c for c in captions if c.get('language', '').startswith('English')), captions[0])
            caption_url = f"{instance}{caption['url']}"

            caption_response = requests.get(caption_url, timeout=10)
            caption_response.raise_for_status()

            # Parse VTT captions
            entries = []
            lines = caption_response.text.split('\n')
            current_text = []
            current_start = 0

            for line in lines:
                if '-->' in line:
                    # Timestamp line
                    parts = line.split(' --> ')
                    if len(parts) >= 1:
                        current_start = _parse_timestamp(parts[0].strip())
                elif line.strip() and not line.startswith('WEBVTT'):
                    # Caption text
                    clean_text = _HTML_TAG_RE.sub('', line).strip()
                    if clean_text:
                        entries.append(TranscriptEntry(
                            start_sec=current_start,
                            end_sec=current_start + 1.0,
                            text=clean_text
                        ))

            if entries:
                logger.info(f"✓ Transcript downloaded via Invidious ({instance}, {len(entries)} segments)")
                return entries

        except requests.Timeout:
            logger.debug(f"Invidious {instance} timeout")
        except Exception as e:
            logger.debug(f"Invidious {instance} failed: {type(e).__name__}")

    logger.debug("All Invidious instances exhausted")
    return None


def download_video(url: str, output_dir: Path, groq_api_key: str | None = None) -> DownloadResult:
    """Orchestrate transcript + video download with 3-strategy fallback chain."""
    video_id = extract_video_id(url)

    entries: list[TranscriptEntry] = []
    source = "none"

    # Try transcript download with fallback chain
    logger.info(f"Starting download pipeline for {video_id}...")

    # Strategy 1: youtube-transcript-api
    entries_result = _get_transcript_api(video_id)
    if entries_result:
        entries = entries_result
        source = "youtube-transcript-api"
    else:
        # Strategy 2: yt-dlp with cookies
        entries_result = _get_transcript_ytdlp_oauth(url, video_id, output_dir)
        if entries_result:
            entries = entries_result
            source = "yt-dlp-oauth"
        else:
            # Strategy 3: Invidious proxy
            entries_result = _get_transcript_invidious(video_id)
            if entries_result:
                entries = entries_result
                source = "invidious"
            else:
                # No transcript available — use video frames only
                logger.warning("[3/3] All transcript strategies exhausted. Proceeding with video frames only.")
                source = "none"

    # Download video
    logger.info("Downloading video file...")
    video_path = _download_video_file(url, output_dir)

    return DownloadResult(
        video_path=video_path,
        transcript_entries=entries,
        transcript_source=source,
        temp_dir=output_dir,
        video_id=video_id,
    )


def _download_video_file(url: str, output_dir: Path) -> Path:
    """Download the best quality video file."""
    opts = {
        "format": "best",
        "outtmpl": str(output_dir / "video.%(ext)s"),
        "quiet": False,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"Video download failed: {e}")
        raise

    video_paths = list(output_dir.glob("video.*"))
    if video_paths:
        return video_paths[0]
    raise FileNotFoundError("No video file found after download")


def _parse_transcript_file(path: Path, fmt: str) -> list[TranscriptEntry]:
    """Parse VTT or SRT transcript file into entries."""
    entries = []

    if fmt == "vtt":
        try:
            for caption in webvtt.read(str(path)):
                text = caption.text.replace("\n", " ").strip()
                text = _HTML_TAG_RE.sub("", text)
                text = _WHITESPACE_RE.sub(" ", text)
                start = _parse_timestamp(caption.start)
                entries.append(
                    TranscriptEntry(
                        start_sec=start,
                        end_sec=_parse_timestamp(caption.end),
                        text=text,
                    )
                )
        except Exception as e:
            logger.error(f"VTT parsing failed: {e}")
    elif fmt == "srt":
        # Simple SRT parser
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().strip().split("\n\n")
            for block in lines:
                parts = block.split("\n", 2)
                if len(parts) >= 3:
                    time_range = parts[1]
                    text = parts[2].replace("\n", " ").strip()
                    text = _HTML_TAG_RE.sub("", text)
                    text = _WHITESPACE_RE.sub(" ", text)

                    try:
                        start_str, end_str = time_range.split(" --> ")
                        start = _parse_timestamp(start_str.strip())
                        end = _parse_timestamp(end_str.strip())
                        entries.append(
                            TranscriptEntry(
                                start_sec=start,
                                end_sec=end,
                                text=text,
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse SRT entry: {e}")

    return entries


