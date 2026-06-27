#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Watch-Youtube Skill Setup Verification                ║"
echo "║     Account: @yapaymeraklisi                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check venv
if [ -d ".venv" ]; then
    echo "✓ Virtual environment exists"
else
    echo "✗ Virtual environment missing"
    exit 1
fi

# Activate venv
source .venv/bin/activate

# Check CLI
echo "Checking CLI..."
watch-youtube --help > /dev/null && echo "✓ CLI functional" || echo "✗ CLI failed"

# Check Groq API key
if [ -f ".env" ]; then
    echo "✓ .env file exists"
    if grep -q "GROQ_API_KEY" .env; then
        echo "✓ Groq API key configured"
    else
        echo "✗ Groq API key missing"
    fi
else
    echo "✗ .env file missing"
fi

# Check config
if [ -f "config.yaml" ]; then
    echo "✓ config.yaml exists"
else
    echo "✗ config.yaml missing"
fi

# Check wiki output directory
WIKI_DIR="/Users/ozgurozturk/ObsidianVaults/SecondBrain/01-PERMANENT/"
if [ -d "$WIKI_DIR" ]; then
    echo "✓ Wiki output directory exists"
else
    echo "✗ Wiki output directory missing"
fi

# Check ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✓ ffmpeg installed"
else
    echo "✗ ffmpeg not found"
fi

# Check spaCy model
python3 -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null && echo "✓ spaCy model loaded" || echo "✗ spaCy model failed"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✓ SETUP COMPLETE - Ready to use                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Usage:"
echo "  source .venv/bin/activate"
echo "  watch-youtube \"https://youtube.com/watch?v=VIDEO_ID\" -o ./output -n 12 -v"
echo ""
