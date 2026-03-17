"""
Gemini Script Evaluator — Uses Gemini 2.5 Flash to evaluate webtoon scripts
on 6 dimensions that correlate with adaptation success.

Scores each script on:
1. Hook Strength (0-10): How compelling is the opening?
2. Dialogue Quality (0-10): How natural, memorable, and character-driven?
3. Pacing (0-10): Flow, tension, revelation timing
4. Emotional Depth (0-10): Character emotion, reader connection
5. Visual Potential (0-10): How well would this translate to animation?
6. Adaptation Potential (0-10): Overall readiness for anime/film/drama

Usage:
    python script_evaluator.py                        # evaluate all cleaned scripts
    python script_evaluator.py --titles tower_of_god  # specific title
    python script_evaluator.py --file path/to/script  # single file (upload mode)
"""

import argparse
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
CLEANED_DIR = Path("data/processed/ocr_cleaned")
OUTPUT_PATH = Path("data/ml_dataset/script_evaluations.jsonl")
RATE_LIMIT_DELAY = 5

EVAL_PROMPT = """You are the AI engine inside Pocket Toons, a short-form mobile drama acquisition system (DramaBox/PocketToons format). Your job is to evaluate a NEW, UNPUBLISHED script with ZERO internet presence — no YouTube views, no Reddit posts, no MAL score. You must evaluate it purely on its intrinsic script quality.
CRITICAL RULE: Do NOT penalize this script for having no social metrics. It is a fresh script. Judge only what is written.

STEP 1 — INTRINSIC FEATURE EXTRACTION
Extract these values from the script (0.0 to 1.0):
- emotion_score: overall emotional intensity across the script
- cliffhanger_rate: ratio of episodes ending on unresolved tension
- addiction_score: pacing speed × cliffhanger frequency combined
- character_distinctness: how unique and differentiated each character feels
- world_building_density: richness of setting without over-explaining
- narrative_arc_completeness: does it follow a clear setup → escalation → hook structure?
- genre_signals: list the dominant genre tags (e.g. revenge, forbidden romance, superpowers)

STEP 2 — SHORT-FORM MOBILE SCORING (0–10 each)
Score for vertical mobile episodes (60–90 sec, phone screen, binge-tap):
1. hook_strength (25%): grabs attention in 3 seconds or the viewer scrolls away
2. cliffhanger_quality (20%): every episode ends forcing the next tap
3. binge_pull (15%): central obsession question that never resolves early
4. dialogue_quality (12%): punchy, distinct, zero exposition dumps
5. emotional_spike (13%): one gut-punch moment per episode minimum
6. visual_potential (10%): works as vertical close-up cinematography on phone
7. pacing (5%): something changes every 20 seconds

STEP 3 — SIMILARITY REASONING
Based on the script's genre signals, tone, and structure — name 3 comparable titles that performed well on mobile platforms and explain WHY this script is similar or different to each. Use this to justify your score.

STEP 4 — WEIGHTED FINAL SCORE
Calculate: script_overall = (hook×0.25) + (cliffhanger×0.20) + (binge×0.15) + (dialogue×0.12) + (emotion×0.13) + (visual×0.10) + (pacing×0.05)
Then: greenlight_score = script_overall × 10
Decision boundaries:
 GREENLIGHT = 78–100 — Commission immediately
 PILOT = 62–77 — Fix critical issue then pilot 5 episodes
 DEFER = 42–61 — Needs structural rework
 REWORK = 0–41 — Not mobile-ready

Output ONLY valid JSON representing the extracted fields exactly:
{
  "intrinsic_features": {
    "emotion_score": 0.82,
    "cliffhanger_rate": 0.90,
    "addiction_score": 0.85,
    "character_distinctness": 0.88,
    "world_building_density": 0.65,
    "narrative_arc_completeness": 0.85,
    "genre_signals": ["psychological thriller", "horror"]
  },
  "dimension_scores": {
    "hook_strength": {"score": 8.5, "reason": "Immediate establishment of visceral dread grabs attention fast."},
    "cliffhanger_quality": {"score": 9.0, "reason": "Incredible mandatory-tap cliffhanger for Ep 2."},
    "binge_pull": {"score": 8.5, "reason": "High central obsession: Will the son escape his complicity?"},
    "dialogue_quality": {"score": 7.5, "reason": "Father's dialogue is chilling, though son relies on internal monologue."},
    "emotional_spike": {"score": 8.0, "reason": "Terrifying realization when father connects news to the package."},
    "visual_potential": {"score": 9.0, "reason": "Extreme macro-shot potential for vertical video (syrup dripping)."},
    "pacing": {"score": 6.5, "reason": "A bit of a slow-burn for a 60s format."}
  },
  "similarity_matches": [
    {"title": "Strangers from Hell", "reason": "Similar tight, suffocating psychological horror..."}
  ],
  "final": {
    "script_overall": 8.27,
    "greenlight_score": 82.7,
    "decision": "GREENLIGHT",
    "top_strength": "Chilling, dual-layered dialogue creates instant hook.",
    "critical_fix": "Convert internal monologues into visual cues.",
    "mobile_fit": "Exceptionally primed for vertical platforms. Reliance on extreme close-ups translates perfectly."
  }
}
"""


def init_client():
    return genai.Client(api_key=API_KEY)


def evaluate_script(client, script_text, title="", genre="", episode=0):
    """Evaluate a single script using Gemini."""
    user_msg = f"Title: {title}\nGenre: {genre}\nEpisode: {episode}\n\nSCRIPT:\n{script_text}"

    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_msg,
                config={
                    "system_instruction": EVAL_PROMPT,
                    "temperature": 0.2,
                    "max_output_tokens": 4000,
                    "response_mime_type": "application/json",
                }
            )
            print(f"    DEBUG GEMINI RAW: {repr(response.text)}")
            result = json.loads(response.text.strip())
            return result
        except json.JSONDecodeError as e:
            print(f"    ❌ JSON Decode Error. Raw response: {response.text}")
            if attempt < 4:
                time.sleep(RATE_LIMIT_DELAY)
                continue
            return None
        except Exception as e:
            import traceback
            print(f"    ❌ Error: {e}")
            traceback.print_exc()
            if attempt < 4:
                sleep_time = 10 * (2 ** attempt)
                print(f"    ⏳ Rate limit or other error. Retrying in {sleep_time} seconds (Attempt {attempt+1}/5)...")
                time.sleep(sleep_time)
                continue
            return None
    return None


def evaluate_single_file(client, file_path):
    """Evaluate a single uploaded script file. Returns the evaluation dict."""
    text = Path(file_path).read_text(encoding="utf-8").strip()
    if len(text) < 20:
        return {"error": "Script too short", "overall_score": 0}
    result = evaluate_script(client, text, title="Uploaded Script")
    return result


def run_batch(titles=None, single_file=None):
    """Evaluate all cleaned scripts or specific ones."""
    client = init_client()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load title registry for metadata
    registry = {}
    reg_path = Path("config/title_registry.json")
    if reg_path.exists():
        with open(reg_path, "r") as f:
            for t in json.load(f)["titles"]:
                registry[t["content_id"]] = t

    if single_file:
        # Single file evaluation mode
        result = evaluate_single_file(client, single_file)
        if result:
            print(json.dumps(result, indent=2))
        return

    # Batch mode: process all cleaned scripts
    json_files = sorted(CLEANED_DIR.glob("*_clean.json"))
    if titles:
        json_files = [f for f in json_files if any(t in f.name for t in titles)]

    total = len(json_files)
    print(f"\n{'='*60}")
    print(f"  GEMINI SCRIPT EVALUATOR")
    print(f"  Model: {MODEL}")
    print(f"  Scripts to evaluate: {total}")
    print(f"{'='*60}\n")

    # Load existing evaluations for resume
    existing = set()
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    existing.add(f"{d['content_id']}_ep{d['episode']}")
                except Exception:
                    pass

    completed = 0
    failed = 0

    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for i, json_file in enumerate(json_files):
            fname = json_file.stem  # e.g., tower_of_god_ep1_clean
            parts = fname.replace("_clean", "").rsplit("_ep", 1)
            content_id = parts[0] if len(parts) == 2 else fname
            ep_str = parts[1] if len(parts) == 2 else "0"
            episode = int(ep_str) if ep_str.isdigit() else 0

            key = f"{content_id}_ep{episode}"
            if key in existing:
                print(f"  [{i+1}/{total}] ⏭️  {content_id} ep{episode} — already evaluated")
                completed += 1
                continue

            # Read the cleaned script
            try:
                with open(json_file, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                # Build script text from dialogue
                script_lines = []
                for entry in data.get("dialogue", []):
                    speaker = entry.get("speaker", "")
                    line = entry.get("line", "")
                    dtype = entry.get("type", "dialogue")
                    if dtype == "narration":
                        script_lines.append(f"({line})")
                    elif dtype == "thought":
                        script_lines.append(f"{speaker} (thinking): {line}")
                    else:
                        script_lines.append(f"{speaker}: {line}")
                script_text = "\n".join(script_lines)
            except Exception as e:
                print(f"  [{i+1}/{total}] ❌ Error reading {content_id} ep{episode}: {e}")
                failed += 1
                continue

            if len(script_text) < 20:
                print(f"  [{i+1}/{total}] ⏭️  {content_id} ep{episode} — script too short")
                continue

            meta = registry.get(content_id, {})
            genre = meta.get("genre", "unknown")

            print(f"  [{i+1}/{total}] 🔄 Evaluating {content_id} ep{episode}...")

            result = evaluate_script(client, script_text, 
                                     meta.get("title", content_id), genre, episode)

            if result:
                # Add metadata
                result["content_id"] = content_id
                result["episode"] = episode
                result["genre"] = genre
                result["title"] = meta.get("title", content_id)

                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()

                score = result.get("overall_score", 0)
                verdict = result.get("one_line_verdict", "N/A")[:60]
                print(f"           ✅ Score: {score}/10 — {verdict}")
                completed += 1
            else:
                failed += 1
                print(f"           ❌ Failed to evaluate")

            time.sleep(RATE_LIMIT_DELAY)

    print(f"\n{'='*60}")
    print(f"  EVALUATION COMPLETE")
    print(f"  ✅ Evaluated: {completed}/{total}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📁 Results: {OUTPUT_PATH}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Gemini Script Evaluator")
    parser.add_argument("--titles", nargs="+", help="Specific content_ids")
    parser.add_argument("--file", type=str, help="Single script file to evaluate")
    args = parser.parse_args()

    run_batch(titles=args.titles, single_file=args.file)


if __name__ == "__main__":
    main()
