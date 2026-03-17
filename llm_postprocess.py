"""
Gemini LLM Post-Processor for OCR Scripts

Takes raw, noisy OCR text from webtoon panels and uses Gemini to produce
fully structured dialogue scripts with:
- Speaker labels (character names when identifiable)
- Separated dialogue, narration, and SFX
- Fixed OCR errors and garbage removal
- Proper punctuation and formatting

Usage:
    python llm_postprocess.py                           # process all raw scripts
    python llm_postprocess.py --titles tower_of_god     # specific title
    python llm_postprocess.py --file path/to/script.txt # single file
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from google import genai

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Configuration
API_KEY = "AIzaSyDjTbMfOBG4XyDvItY2OGGKzgZBoCWAzFI"
MODEL = "gemini-2.5-flash"
RAW_DIR = Path("data/processed/ocr_scripts")
CLEAN_DIR = Path("data/processed/ocr_cleaned")
CORPUS_FILE = Path("data/ml_dataset/ocr_corpus.jsonl")

# Rate limiting: Gemini free tier is 15 RPM for 2.5 Flash
RATE_LIMIT_DELAY = 5  # seconds between API calls

SYSTEM_PROMPT = """You are a professional script editor for webtoon (comic) dialogue extraction.

You will receive RAW OCR text extracted from webtoon comic panels. The text is noisy, with:
- OCR errors (e.g., "YOL" → "YOU", "BLT" → "BUT", "APMS" → "ARMS")
- Sound effects mixed with dialogue (e.g., "CRASH", "POW", "SWOOSH")
- Random garbage characters and fragments
- Missing punctuation and broken sentences
- Chapter headers and metadata mixed in

Your job is to produce a CLEAN, STRUCTURED script. Output ONLY valid JSON with this exact format:

{
  "title_header": "Episode title/chapter info if found, else empty string",
  "dialogue": [
    {
      "speaker": "Character Name or UNKNOWN or NARRATOR",
      "line": "The cleaned dialogue line",
      "type": "dialogue | narration | thought | sfx"
    }
  ],
  "sfx_list": ["CRASH", "POW", "SWOOSH"],
  "summary": "A 1-2 sentence summary of what happens in this episode based on the dialogue",
  "word_count": 123,
  "confidence": "high | medium | low"
}

Rules:
1. Fix all OCR errors — use context to determine correct words
2. Separate dialogue from sound effects (SFX)
3. If you can identify character names from the dialogue, use them as speaker labels
4. Mark internal thoughts differently from spoken dialogue
5. Narration (scene descriptions, internal monologue) should be labeled as NARRATOR
6. Remove garbage text, duplicates, and header/footer noise
7. Preserve the story order — don't rearrange lines
8. Set confidence to "low" if the text is too noisy to reliably clean
9. Output ONLY the JSON, no markdown formatting, no code fences"""


def init_client():
    """Initialize the Gemini client."""
    return genai.Client(api_key=API_KEY)


def process_script(client, raw_text, title="", episode=0, max_retries=2):
    """Send raw OCR text to Gemini for cleaning and structuring."""
    user_prompt = f"Webtoon: {title}, Episode: {episode}\n\nRAW OCR TEXT:\n{raw_text}"

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "temperature": 0.1,
                    "max_output_tokens": 65536,
                    "response_mime_type": "application/json",
                }
            )

            result_text = response.text.strip()

            # Strip markdown code fences if present
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                result_text = "\n".join(lines)

            parsed = json.loads(result_text)
            return parsed

        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(f"    ⚠️  JSON parse error (attempt {attempt+1}), retrying...")
                time.sleep(RATE_LIMIT_DELAY)
                continue
            print(f"    ⚠️  JSON parse error after {max_retries+1} attempts: {e}")
            return {
                "title_header": f"{title} Ep {episode}",
                "dialogue": [{"speaker": "RAW", "line": raw_text[:500], "type": "dialogue"}],
                "sfx_list": [],
                "summary": "Failed to parse LLM output",
                "word_count": len(raw_text.split()),
                "confidence": "low"
            }
        except Exception as e:
            print(f"    ❌ Gemini API error: {e}")
            if attempt < max_retries:
                time.sleep(RATE_LIMIT_DELAY)
                continue
            return None

    return None


def save_cleaned(parsed, output_path):
    """Save structured script as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)


def save_readable(parsed, output_path):
    """Save a human-readable .txt version of the cleaned script."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        if parsed.get("title_header"):
            f.write(f"=== {parsed['title_header']} ===\n\n")

        if parsed.get("summary"):
            f.write(f"SUMMARY: {parsed['summary']}\n\n")
            f.write("─" * 50 + "\n\n")

        for entry in parsed.get("dialogue", []):
            speaker = entry.get("speaker", "UNKNOWN")
            line = entry.get("line", "")
            dtype = entry.get("type", "dialogue")

            if dtype == "sfx":
                f.write(f"  [{line}]\n")
            elif dtype == "narration":
                f.write(f"  ({line})\n")
            elif dtype == "thought":
                f.write(f"  {speaker} (thinking): {line}\n")
            else:
                f.write(f"  {speaker}: {line}\n")

        if parsed.get("sfx_list"):
            f.write(f"\n─── SFX: {', '.join(parsed['sfx_list'])} ───\n")

        f.write(f"\n[Words: {parsed.get('word_count', '?')} | Confidence: {parsed.get('confidence', '?')}]\n")


def build_corpus_entry(parsed, uid, content_id, title, genre, episode):
    """Build an ML-ready corpus entry from the cleaned script."""
    # Extract just the dialogue text
    dialogue_text = "\n".join(
        f"{e['speaker']}: {e['line']}" for e in parsed.get("dialogue", [])
        if e.get("type") in ("dialogue", "narration", "thought")
    )
    return {
        "uid": uid,
        "content_id": content_id,
        "title": title,
        "genre": genre,
        "episode": episode,
        "word_count": parsed.get("word_count", len(dialogue_text.split())),
        "confidence": parsed.get("confidence", "unknown"),
        "summary": parsed.get("summary", ""),
        "script": dialogue_text,
        "sfx": parsed.get("sfx_list", []),
    }


def run_batch(titles=None, single_file=None):
    """Process all or selected raw OCR scripts through Gemini."""
    client = init_client()
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # Load title registry for metadata
    registry_path = Path("config/title_registry.json")
    registry = {}
    if registry_path.exists():
        with open(registry_path, "r") as f:
            for t in json.load(f)["titles"]:
                registry[t["content_id"]] = t

    if single_file:
        files = [Path(single_file)]
    else:
        files = sorted(RAW_DIR.glob("*_script.txt"))
        if titles:
            files = [f for f in files if any(t in f.name for t in titles)]

    total = len(files)
    print(f"\n{'='*60}")
    print(f"  GEMINI LLM POST-PROCESSOR")
    print(f"  Model: {MODEL}")
    print(f"  Files to process: {total}")
    print(f"{'='*60}\n")

    completed = 0
    failed = 0
    corpus_entries = []

    for i, script_file in enumerate(files):
        # Parse content_id and episode from filename
        fname = script_file.stem  # e.g., "tower_of_god_ep1_script"
        parts = fname.rsplit("_ep", 1)
        content_id = parts[0] if len(parts) == 2 else fname
        ep_str = parts[1].replace("_script", "") if len(parts) == 2 else "0"
        episode = int(ep_str) if ep_str.isdigit() else 0

        # Check if already cleaned
        clean_json = CLEAN_DIR / f"{content_id}_ep{episode}_clean.json"
        if clean_json.exists() and clean_json.stat().st_size > 100:
            print(f"  [{i+1}/{total}] ⏭️  {content_id} ep{episode} — already cleaned, skipping")
            # Still load for corpus
            with open(clean_json, "r", encoding="utf-8") as f:
                parsed = json.load(f)
            meta = registry.get(content_id, {})
            corpus_entries.append(build_corpus_entry(
                parsed, meta.get("uid", ""), content_id,
                meta.get("title", content_id), meta.get("genre", ""), episode
            ))
            completed += 1
            continue

        # Read raw text
        raw_text = script_file.read_text(encoding="utf-8").strip()
        if len(raw_text) < 20:
            print(f"  [{i+1}/{total}] ⏭️  {content_id} ep{episode} — too short, skipping")
            continue

        print(f"  [{i+1}/{total}] 🔄 Processing {content_id} ep{episode} ({len(raw_text.split())} words)...")

        meta = registry.get(content_id, {})
        parsed = process_script(client, raw_text, meta.get("title", content_id), episode)

        if parsed:
            # Save structured JSON
            save_cleaned(parsed, clean_json)
            # Save readable text
            save_readable(parsed, CLEAN_DIR / f"{content_id}_ep{episode}_clean.txt")
            # Build corpus entry
            corpus_entries.append(build_corpus_entry(
                parsed, meta.get("uid", ""), content_id,
                meta.get("title", content_id), meta.get("genre", ""), episode
            ))
            completed += 1
            dl_count = len([d for d in parsed.get("dialogue", []) if d.get("type", "dialogue") == "dialogue"])
            print(f"           ✅ Done — {dl_count} dialogue lines, confidence: {parsed.get('confidence', '?')}")
        else:
            failed += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    # Save ML corpus
    if corpus_entries:
        CORPUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CORPUS_FILE, "w", encoding="utf-8") as f:
            for entry in corpus_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Summary
    print(f"\n{'='*60}")
    print(f"  POST-PROCESSING COMPLETE")
    print(f"  ✅ Cleaned: {completed}/{total}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📄 Corpus entries: {len(corpus_entries)}")
    print(f"  📁 Clean scripts: {CLEAN_DIR}")
    print(f"  📁 ML corpus: {CORPUS_FILE}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Gemini LLM Post-Processor for OCR scripts")
    parser.add_argument("--titles", nargs="+", help="Specific content_ids to process")
    parser.add_argument("--file", type=str, help="Process a single script file")
    args = parser.parse_args()

    run_batch(titles=args.titles, single_file=args.file)


if __name__ == "__main__":
    main()
