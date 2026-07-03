# Bible Versions

A web scraper that downloads the entire Bible across **38+ English translations** from [BibleHub.com](https://biblehub.com), and exports them into individual JSON files formatted as flat lists of verses.

## Project Structure

```
bible-versions/
├── scraper.py              ← Main BibleHub scraper for the full English translation set
├── verify.py               ← Verify scraped Bible data for completeness
├── export.py               ← Export the main dataset into per-translation JSON files
├── twi/                    ← Isolated Ghana/TWI-only workflow
│   ├── scraper.py          ← TWI scraper entry point
│   └── export.py           ← TWI export entry point
│
├── README.md               ← You are here
├── requirements.txt        ← Python dependencies
├── pyproject.toml          ← Package config and console script entry points
│
├── bible_data.json         ← Raw scraped data from the main scraper
├── scraper_progress.json   ← Resume checkpoint — do NOT delete!
├── bible_scraper.log       ← Scraper activity log
│
├── versions/               ← Per-translation output (created by export.py or twi_export.py)
│   ├── NIV/
│   │   └── NIV_bible.json
│   ├── ESV/
│   │   └── ESV_bible.json
│   └── TWI/
│       └── TWI_bible.json
│
├── html_cache/             ← Cached HTML pages (speeds up re-scraping)
│
└── scrapers/               ← Additional scrapers (for reference / re-use)
    ├── apocrypha_scraper.py     ← Apocrypha / Deuterocanonical books
    ├── multilang_scraper.py     ← Multi-language scraper
    └── helpers/                 ← Helper scripts for multi-language workflow
        ├── apply_book_name_mapping.py
        ├── build_book_name_mapping.py
        ├── build_locale_version_map.py
        └── organize_versions_by_locale.py
```

---

## Quick Start

### Prerequisites

Make sure you have Python 3.11+ installed, then install dependencies:

```powershell
pip install -r requirements.txt
```

If you want the optional console commands after installation, you can also install the package in editable mode:

```powershell
pip install -e .
```

---

## Main Workflow: BibleHub English Translations

This is the default full workflow for the main multi-translation BibleHub collection.

### Step 1 — Scrape the Bible

This downloads all translations from BibleHub, verse by verse. It scrapes ~31,000 verses and captures **38+ translations simultaneously** from each verse page.

```powershell
python scraper.py -o bible_data.json
```

> **This will take several hours.** The scraper adds a small delay between requests to be respectful to BibleHub.

### 🛡️ Accidental Overwrite Protection

If you run `python scraper.py` without `--resume` but have existing data or progress files, the scraper will detect it and print a warning:

- **Interactive terminal:** You will be prompted to either **[r] Resume** (highly recommended), **[o] Overwrite** (start fresh), or **[a] Abort**.
- **Non-interactive terminal (scripts):** The scraper will fail safely and abort to protect your data, prompting you to explicitly pass `--resume` or `--overwrite`.

### 📊 Terminal Progress Bar

The scraper displays a beautiful, live-updating progress bar directly in your terminal:

```
[██████████░░░░░░░░░░░░░░]  41.5% | Genesis 24:12 | 12,900/31,102 | 4.8 v/s | ETA: 01:03:15 | Translations: 38
```

It displays the percentage completed, active book and verse, overall verse count, speed (verses/second), estimated time remaining (ETA), and number of captured translations.

### 📝 Monitor Log File

To keep your terminal interface clean and responsive, all detailed logs (like cache hits, downloads, and success notifications) are written directly to the log file `bible_scraper.log`.

To watch the live activity trail in the background, open a separate terminal and run:

```powershell
Get-Content bible_scraper.log -Wait  # PowerShell live tail
```

---

### Step 2 — Verify the Data

Once scraping is complete (or even while it's running), verify that all books, chapters, and verses were captured correctly:

```powershell
python verify.py
```

This checks all 66 canonical books and 31,103 verses per translation and prints a completion report. `Missing` means the verse is still absent from your JSON/cache, `SrcBlank` means BibleHub shows that translation label but leaves the verse text blank, and `SrcNA` means the cached BibleHub page does not include that translation label for that verse.

```
  Translation          Present Expected  Missing SrcBlank    SrcNA  Complete
  -------------------- -------- -------- -------- -------- -------- ---------
  BSB                   31,086   31,086        0        0        0   100.0%  OK
  ESV                   31,085   31,085        0        1        0   100.0%  SOURCE_LIMITS
  KJV                   31,102   31,102        0        0        0   100.0%  OK
  CEV                   27,863   27,863        0        0    3,223   100.0%  SOURCE_LIMITS
  ...
```

### Useful options

```powershell
# Check only one translation
python verify.py --version NIV

# Check the Ghana/TWI-only export directly
python verify.py --input versions/TWI/TWI_bible.json --version TWI

# Print the summary table only (no per-verse detail)
python verify.py --summary
```

If a translation shows `SOURCE_LIMITS`, the local data is complete for the text BibleHub exposes on its verse pages. If any translation shows `INCOMPLETE`, run a targeted retry instead of re-running the entire scrape:

```powershell
# Retry only verse pages that verify.py reports as truly missing
python scraper.py --retry-missing

# Re-download those pages instead of using cached HTML first
python scraper.py --retry-missing --force-refresh
```

If the package is installed, the same targeted retry is also available as:

```powershell
bible-scraper-retry-missing
bible-scraper-retry-missing --force-refresh
```

---

### Step 3 — Export the Translations

After verifying the data, split `bible_data.json` into individual per-translation files formatted as flat verse arrays:

```powershell
python export.py
```

Each translation is saved as a flat JSON array of verse objects:

```json
[
  { "book": "Genesis", "chapter": 1, "verse": 1, "text": "In the beginning..." },
  { "book": "Genesis", "chapter": 1, "verse": 2, "text": "Now the earth was..." },
  ...
]
```

Files are created in `versions/<CODE>/<CODE>_bible.json`.
The exporter uses short translation codes for folder and file names, for example:

```text
versions/AMP/AMP_bible.json
versions/NKJV/NKJV_bible.json
versions/NIV/NIV_bible.json
```

### Useful options

```powershell
# Export to a custom output folder
python export.py --output my_output_folder

# Export only one translation
python export.py --version ESV
python export.py --version AMP

# Export without the completeness report
python export.py --no-report
```

---

### Step 4 — Use the Exported Files

After exporting, copy the translation folders you need into your target application's resources directory:

```powershell
Copy-Item -Recurse "versions\NIV" "..\your-bible-app\resources\bibles\"
Copy-Item -Recurse "versions\ESV" "..\your-bible-app\resources\bibles\"
```

---

## Available Translations

The scraper captures all translations available on BibleHub's verse pages, including:

| Code            | Name                        |
| --------------- | --------------------------- |
| NIV             | New International Version   |
| ESV             | English Standard Version    |
| NLT             | New Living Translation      |
| CSB             | Christian Standard Bible    |
| BSB             | Berean Standard Bible       |
| NASB            | New American Standard Bible |
| KJV             | King James Version          |
| NKJV            | New King James Version      |
| AMP             | Amplified Bible             |
| MSG             | The Message                 |
| ...and 28+ more |                             |

---

## Optional Ghana/TWI-Only Workflow

If you want a single Ghana-focused Akan/Twi Bible, use the dedicated TWI workflow instead of the main BibleHub multi-translation scrape.

### Scrape TWI only

```powershell
python twi/scraper.py -o versions/TWI/TWI_bible.json
```

This writes a raw TWI dataset to the output path and keeps the TWI Bible separate from the broader English BibleHub collection.

### Export TWI only

```powershell
python twi/export.py -i versions/TWI/TWI_bible_raw.json -o versions/TWI/TWI_bible.json
```

### Verify TWI only

You can verify the TWI output directly with the same verifier, including flat JSON exports:

```powershell
python verify.py --input versions/TWI/TWI_bible.json --version TWI
```

If you installed the package in editable mode, the same commands are also available as:

```powershell
bible-scraper-twi --output versions/TWI/TWI_bible.json
```

### Notes about the TWI scraper

- The TWI scraper is intentionally separate because it targets a Ghana-specific Akan/Twi translation from Were Kronkron rather than the main BibleHub translation bundle.
- It is useful for local or country-specific projects where you want one TWI Bible without the larger English dataset.
- The TWI workflow lives entirely under the dedicated [twi](twi) folder so it stays separate from the main BibleHub-based workflow.

---

## Multi-Language and Apocrypha Scrapers

The `scrapers/` folder also contains additional scrapers for other use cases:

- **`apocrypha_scraper.py`** — Scrapes the Apocrypha/Deuterocanonical books (Maccabees, Tobit, Judith, Wisdom of Solomon, etc.) included in Catholic and Orthodox Bibles but not in most Protestant Bibles.
- **`multilang_scraper.py`** — Scrapes Bible translations in other languages (Spanish, French, German, etc.) from BibleHub's international pages. The `helpers/` subfolder contains supporting scripts for building language maps and organizing the output.

---

## Important Notes

- **Rate limiting**: The scraper is intentionally slow to avoid overwhelming BibleHub's servers.
- **HTML cache**: All fetched pages are cached locally in `html_cache/`. If re-scraping, the cache speeds things up significantly.
- **Copyright**: Bible translations have different copyright terms. This data is intended for personal/educational use. For public or commercial use, verify licensing for each translation.

---

## Acknowledgments

Data sourced from [BibleHub.com](https://biblehub.com). Special thanks to the open Bible developer community for making Scripture accessible in digital form.
