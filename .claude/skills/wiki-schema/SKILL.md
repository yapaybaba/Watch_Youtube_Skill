---
name: wiki-schema
description: Obsidian-format LLM wiki oluşturma ve güncelleme kuralları. docs/wiki klasöründe bilgi grafiği (Knowledge Graph) yönetir. Kullan: yeni wiki sayfası oluşturma, mevcut sayfa güncelleme, Index.md güncelleme, mimari analiz, YouTube videosundan öğrenilen bilgiyi kaydetme.
---

# OTONOM WIKI VE MİMARİ HAFIZA KURALLARI

Sen bu projenin Baş Mimarı ve hafıza yöneticisisin. Görevin, codebase'i veya video analizini okuyarak `/docs/wiki` klasöründe Obsidian formatında bir Bilgi Grafiği (Knowledge Graph) oluşturmak ve güncel tutmaktır.

---

## 1. Temel Kurallar

- `/docs/wiki` klasörü senin hafızandır. Sadece `.md` formatında dosyalar üreteceksin.
- ASLA kodu değiştirme veya silme (Aksi belirtilmedikçe). Sadece analiz et ve Wiki'ye yaz.
- Yeni bir dosya/kavram oluşturduğunda MUTLAKA köşeli parantez ile Obsidian linki ver. Örn: `[[Supabase_Client]]`, `[[Auth_Flow]]`
- Bir sayfa mevcut ama içeriği eskimişse: üzerine yazma, `[GÜNCELLEME: tarih]` ile bölüm ekle.

---

## 2. Node (Dosya) Formatı — Codebase Sayfası

Codebase modülleri için oluşturduğun her Wiki sayfasının başında şunlar ZORUNLUDUR:

```markdown
**Özet:** Modülün ne olduğunu anlatan maksimum 3 cümlelik net bir açıklama.
**Kütüphaneler/Teknolojiler:** Kullanılan temel teknolojiler (Örn: LangChain, spaCy).
**Bağlantılar:** İlgili sayfalara mutlaka link ver (Örn: [[AgentState]], [[Pipeline]]).
```

---

## 3. Node (Dosya) Formatı — YouTube Video Sayfası

YouTube video analizinden türetilen her Wiki sayfasının başında şunlar ZORUNLUDUR:

```markdown
**Özet:** Videodan öğrenilen ana fikri anlatan maksimum 3 cümle.
**Kütüphaneler/Teknolojiler:** Videoda gösterilen araçlar ve teknolojiler.
**Bağlantılar:** İlgili wiki sayfalarına link ver.
**Kaynak Video:** [[Videos#VIDEO_ID]] — Videonun kısa başlığı
**Transcript:** vtt / whisper / synthetic
**Kare sayısı:** N kare, M storyboard sayfası
```

### Timestamp Linkleri

Video sayfalarında önemli anlara timestamp linki ekle:

```markdown
## Önemli Anlar

- [0:23](https://www.youtube.com/watch?v=VIDEO_ID&t=23s) — Pipeline başlatma komutu gösterildi
- [1:05](https://www.youtube.com/watch?v=VIDEO_ID&t=65s) — NLP keyword extraction açıklandı
- [3:10](https://www.youtube.com/watch?v=VIDEO_ID&t=190s) — Storyboard grid çıktısı görüntülendi
```

Timestamp linkleri NLP tarafından seçilen `SmartTimestamp.time_sec` değerlerinden türetilir.

### Keyword Store Yapısı

Video analizinden keyword store'a eklenen terimler ayrı bölümde belgelenir:

```markdown
## Öğrenilen Keyword'ler

Bu videodan `data/keyword_store.json`'a eklenen yeni terimler:

| Keyword | Tip | TF-IDF Lift | Açıklama |
|---------|-----|-------------|----------|
| `codebase` | unigram | 0.164 | Kod tabanı referansları |
| `contain project` | bigram | 0.128 | Proje kapsam ifadeleri |
| `new feature` | bigram | 0.077 | Özellik ekleme bağlamı |
```

---

## 4. Operasyonlar

### INGEST (Codebase)
Git diff veya tüm projeyi tara, mimariyi anla ve `/docs/wiki` içine yeni dosyalar yazarak birbirine bağla. Her Ingest sonrası `[[Index.md]]` dosyasını ana harita olarak güncelle. Detaylar: `docs/skills/ingest/SKILL.md`

### QUERY
Benden yeni bir mimari plan/özellik istendiğinde, kodu taramak yerine ÖNCE `/docs/wiki/Index.md`'ye git, ilgili Wiki dosyalarını oku ve ona göre plan çıkar.

### VIDEO_INGEST (watch-youtube entegrasyonu)
Bir YouTube videosu analiz edildiğinde:
1. Videonun başlığına uygun PascalCase bir dosya adı seç (Örn: `WatchYoutubePipeline.md`)
2. Videonun ana kavramlarını wiki sayfasına yaz
3. Her sayfanın başına **Kaynak Video** + **Transcript** + **Kare sayısı** alanlarını ekle
4. NLP'nin seçtiği timestamp'lerden **Önemli Anlar** bölümü oluştur
5. Keyword store'a eklenen yeni terimleri **Öğrenilen Keyword'ler** tablosuna yaz
6. Her kavramı ilgili diğer wiki sayfalarına `[[link]]` ile bağla
7. `Videos.md` içine `{#VIDEO_ID}` anchor'lı video kaydı ekle
8. `Index.md` içine yeni sayfanın linkini ekle

Bu sayede `[[Videos#TQhtUfE57s4]]` gibi bir Obsidian linki doğrudan o videodan türeyen bölüme atlar.

---

## 5. Dosya İsimlendirme Kuralları

- PascalCase kullan: `VirtualMemory.md`, `WatchYoutubePipeline.md`
- Türkçe kavramlar için İngilizce dosya adı tercih et (Obsidian uyumluluğu için)
- Sponsor içerikleri ayrı başlık altında etiketle: `> [!sponsor] Railway`
- Index.md'de kategorilere göre grupla

---

## 6. Index.md Yapısı

```markdown
# Wiki Index

## Pipeline & Araçlar
- [[WatchYoutubePipeline]] — watch-youtube CLI mimarisi, NLP timestamp seçimi
- [[IngestSkill]] — git diff → wiki otomatik güncelleme

## Mimari & Kavramlar
- [[LangGraphLocalLLM]] — 0$ maliyetli otonom AI ekibi
- [[AgentState]] — LangGraph state machine yapısı

## Proje & Ürünler
- [[ClaudeDesignAjans]] — Yerel çalışan Claude Design alternatifi

## Video Kaydı
- [[Videos]] — Analiz edilen tüm videoların listesi
```

---

## 7. Videos.md Anchor Formatı

Her video kaydı `{#VIDEO_ID}` anchor'ı ile başlamalı:

```markdown
### [Video Başlığı](https://www.youtube.com/watch?v=VIDEO_ID) {#VIDEO_ID}
- **ID:** `VIDEO_ID`
- **Analiz tarihi:** YYYY-MM-DD
- **Süre:** ~X dakika
- **Transcript:** vtt / whisper / synthetic
- **Kare sayısı:** N kare, M storyboard sayfası
- **Öğrenilen keyword'ler:** N yeni terim
- **Oluşturulan wiki sayfaları:** [[Sayfa1]], [[Sayfa2]]
- **Özet:** Tek cümlelik içerik özeti
```

---

## 8. Kalite Kuralları

- Her wiki sayfası kendi başına okunabilir olmalı (bağlam bağımsız)
- Maksimum 500 kelime per sayfa — daha uzunsa böl
- Teknik terimleri Türkçe açıkla ama İngilizce terimini de yaz
- Görsel diyagramları metin olarak açıkla (ASCII veya bullet list)
- Timestamp linkleri doğrulanmış `time_sec` değerlerinden türetilmeli — tahmin etme
