# Greenlight Intelligence

Greenlight Intelligence is a small experimental toolkit to help you explore \"greenlight\" potential for series ideas using data from:

- Webtoon pages (titles, episode info, etc.)
- YouTube video transcripts and comments
- Simple NLP analysis and scoring rules

You **do not need to be a pro coder** to use this. The project is organized into clear steps and scripts you can run from the command line.

---

## Project structure

```text
greenlight-intelligence/
├── data/
│   ├── raw/         # Raw scraped data (JSON/CSV)
│   ├── processed/   # Cleaned & feature-ready data
│   └── external/    # Any external reference data
│
├── scrapers/
│   ├── webtoon_scraper.py      # Scrape webtoon-like pages
│   └── youtube_transcripts.py  # Download YouTube transcripts
│
├── nlp/
│   ├── comment_emotions.py     # Analyze comment sentiment/emotions
│   └── transcript_analysis.py  # Analyze transcript text
│
├── scoring/
│   ├── feature_engineering.py  # Turn text into numeric features
│   └── score_titles.py         # Score titles/series ideas
│
├── config/
│   └── settings.yaml           # Paths and default parameters
│
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Create and activate a virtual environment (recommended)

From the project root (`c:\Users\Nitin\Documents\pocket_toons`):

```bash
python -m venv venv

# On Windows (PowerShell)
venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, you may need to adjust the execution policy, for example:

```bash
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

On Linux/macOS the activate command looks like:

```bash
source venv/bin/activate
```

### 2. Install dependencies

With the virtual environment active:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

Basic settings live in `config/settings.yaml` and include:

- **paths**: where raw/processed data is stored
- **scraping**: options for user-agent and base URLs
- **youtube**: transcript language and options
- **nlp**: language, sentiment model
- **scoring**: weights for different features

You can edit that file with any text editor; we will keep the defaults simple.

---

## First scripts to try

After installing requirements, you will be able to:

1. **Scrape a webtoon-like page** (structure is customizable later)
2. **Download a YouTube transcript by video ID**
3. **Run simple NLP analysis and scoring** on the collected text

We will wire these scripts up step by step so you can:

- Run one script at a time
- Inspect the output files in `data/`
- Adjust your ideas and scoring rules without touching heavy code

As we go, we can add concrete examples of commands tailored to your exact use cases (which sites, what kind of titles, what \"greenlight\" means for you).

