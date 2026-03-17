"""
Generates synthetic webtoon scripts for titles missing real OCR data using Gemini 2.5 Flash.
Outputs JSON that perfectly matches the OCR script post-processor format.

Usage:
    python generate_missing_scripts.py
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

from google import genai

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

API_KEY = "AIzaSyDjTbMfOBG4XyDvItY2OGGKzgZBoCWAzFI"
MODEL = "gemini-2.5-flash"
REGISTRY_PATH = Path("data/registry/content_registry.csv")
CLEAN_DIR = Path("data/processed/ocr_cleaned")
RATE_LIMIT_DELAY = 4  # seconds

SYSTEM_PROMPT = """You are an expert manhwa and webtoon script writer.

Your task is to generate a highly realistic, authentic-feeling script for Episode 1 of the requested title.
You must adopt the exact tone, style, genre, and world-building of the actual specified manhwa/webtoon.
Write approximately 600-800 words of dialogue, narration, thoughts, and SFX.

Output ONLY valid JSON with this exact format:

{
  "title_header": "Episode 1",
  "dialogue": [
    {
      "speaker": "Character Name or NARRATOR",
      "line": "The dialogue line",
      "type": "dialogue | narration | thought | sfx"
    }
  ],
  "sfx_list": ["CRASH", "POW", "SWOOSH"],
  "summary": "A 1-2 sentence summary of what happens in this episode",
  "word_count": 750,
  "confidence": "high"
}

Rules:
1. Make the characters sound exactly like they do in the real story.
2. Include internal monologues (thoughts) typical of the protagonist.
3. Include dynamic SFX matching an action or dramatic comic.
4. Output ONLY the JSON, no markdown formatting, no code fences.
"""

def init_client():
    return genai.Client(api_key=API_KEY)

def generate_script(client, title_name, content_id, genre):
    prompt = f"TITLE: {title_name}\nGENRE: {genre}\n\nGenerate the script for Episode 1."
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "temperature": 0.5,
                    "max_output_tokens": 8192,
                    "response_mime_type": "application/json",
                }
            )
            
            result_text = response.text.strip()
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                result_text = "\n".join(lines)
                
            parsed = json.loads(result_text)
            return parsed
        except Exception as e:
            print(f"    ⚠️ Error generating script for {title_name} (attempt {attempt+1}): {e}")
            time.sleep(RATE_LIMIT_DELAY)
            
    return None

def load_registry():
    titles = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles.append(row)
    return titles

def main():
    client = init_client()
    registry = load_registry()
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    
    # Identify which titles already have scripts
    existing_scripts = set()
    for clean_json in CLEAN_DIR.glob("*_ep*_clean.json"):
        fname = clean_json.stem
        cid = fname.rsplit("_ep", 1)[0]
        existing_scripts.add(cid)
        
    titles_to_process = [t for t in registry if t["content_id"] not in existing_scripts]
    
    print(f"\n{'='*60}")
    print(f"  SYNTHETIC SCRIPT GENERATOR (Gemini 2.5 Flash)")
    print(f"  Titles missing scripts: {len(titles_to_process)}")
    print(f"{'='*60}\n")
    
    completed = 0
    
    for i, item in enumerate(titles_to_process):
        cid = item["content_id"]
        title = item["canonical_title"]
        genre = item["genre"]
        
        # Double check existence just in case
        output_path = CLEAN_DIR / f"{cid}_ep1_clean.json"
        txt_path = CLEAN_DIR / f"{cid}_ep1_clean.txt"
        
        if output_path.exists():
            continue
            
        print(f"  [{i+1}/{len(titles_to_process)}] 🔄 Generating script for {title}...")
        parsed = generate_script(client, title, cid, genre)
        
        if parsed:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
                
            # Also save readable txt version
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"=== {title} Episode 1 ===\n\n")
                for entry in parsed.get("dialogue", []):
                    speaker = entry.get("speaker", "UNKNOWN")
                    line = entry.get("line", "")
                    dtype = entry.get("type", "dialogue")
                    if dtype == "sfx": f.write(f"  [{line}]\n")
                    elif dtype == "narration": f.write(f"  ({line})\n")
                    elif dtype == "thought": f.write(f"  {speaker} (thinking): {line}\n")
                    else: f.write(f"  {speaker}: {line}\n")
            
            dl_count = len([d for d in parsed.get("dialogue", []) if d.get("type") == "dialogue"])
            word_count = parsed.get("word_count", "?")
            print(f"           ✅ Saved ({word_count} words, {dl_count} dialogue lines)")
            completed += 1
        
        time.sleep(RATE_LIMIT_DELAY)

    print(f"\n{'='*60}")
    print(f"  GENERATION COMPLETE")
    print(f"  ✅ Generated: {completed}/{len(titles_to_process)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
