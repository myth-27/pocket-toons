"""
Batch OCR Pipeline — Scrapes first N episodes of each registered webtoon title
and produces structured ML-ready data with unique IDs.

Usage:
    python batch_ocr_pipeline.py                     # all titles, eps 1-10
    python batch_ocr_pipeline.py --titles tower_of_god solo_leveling
    python batch_ocr_pipeline.py --episodes 5        # first 5 eps only
    python batch_ocr_pipeline.py --dry-run            # show plan without running
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.append(os.getcwd())

from ocr_pipeline import run_ocr_pipeline

REGISTRY_PATH = Path("config/title_registry.json")
CORPUS_OUTPUT = Path("data/ml_dataset/ocr_corpus.jsonl")


def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["titles"]


def build_episode_url(title_entry, episode_num):
    """
    Construct the Webtoon episode viewer URL.
    Webtoon URL pattern: https://www.webtoons.com/en/{category}/{slug}/episode-{ep}/viewer?title_no={id}&episode_no={ep}
    """
    base = "https://www.webtoons.com/en"
    category = title_entry["category"]
    slug = title_entry["slug"]
    title_no = title_entry["title_no"]
    # episode_no on webtoons is usually 1-indexed and matches the episode number for early episodes
    return f"{base}/{category}/{slug}/episode-{episode_num}/viewer?title_no={title_no}&episode_no={episode_num}"


def build_corpus_entry(title_entry, episode_num):
    """Read the generated script file and build a corpus entry."""
    content_id = title_entry["content_id"]
    script_file = Path(f"data/processed/ocr_scripts/{content_id}_ep{episode_num}_script.txt")

    if not script_file.exists():
        return None

    text = script_file.read_text(encoding="utf-8").strip()
    if not text:
        return None

    return {
        "uid": title_entry["uid"],
        "content_id": content_id,
        "title": title_entry["title"],
        "genre": title_entry["genre"],
        "episode": episode_num,
        "word_count": len(text.split()),
        "script": text,
    }


def run_batch(titles=None, max_episodes=10, dry_run=False):
    registry = load_registry()

    # Filter titles if specified
    if titles:
        registry = [t for t in registry if t["content_id"] in titles]

    total_jobs = len(registry) * max_episodes
    print(f"\n{'='*60}")
    print(f"  BATCH OCR PIPELINE")
    print(f"  Titles: {len(registry)} | Episodes per title: {max_episodes}")
    print(f"  Total jobs: {total_jobs}")
    print(f"{'='*60}\n")

    if dry_run:
        for t in registry:
            print(f"  [{t['uid']}] {t['title']} ({t['genre']})")
            for ep in range(1, max_episodes + 1):
                url = build_episode_url(t, ep)
                print(f"    Ep {ep}: {url}")
        print(f"\n  DRY RUN complete. No data was downloaded.")
        return

    completed = 0
    failed = []
    skipped = []

    for t in registry:
        print(f"\n{'─'*60}")
        print(f"  [{t['uid']}] {t['title']} ({t['genre']})")
        print(f"{'─'*60}")

        for ep in range(1, max_episodes + 1):
            # Skip if already processed
            script_file = Path(f"data/processed/ocr_scripts/{t['content_id']}_ep{ep}_script.txt")
            if script_file.exists() and script_file.stat().st_size > 100:
                print(f"  ⏭️  Ep {ep}: Already processed ({script_file.stat().st_size} bytes), skipping.")
                skipped.append(f"{t['content_id']}_ep{ep}")
                completed += 1
                continue

            url = build_episode_url(t, ep)
            print(f"\n  🔄 Processing Ep {ep}/{max_episodes}...")

            try:
                run_ocr_pipeline(url, t["content_id"], ep)
                completed += 1
                print(f"  ✅ Ep {ep} done.")
            except Exception as e:
                error_msg = str(e)
                print(f"  ❌ Ep {ep} failed: {error_msg}")
                failed.append({"title": t["content_id"], "ep": ep, "error": error_msg})

            # Brief pause between episodes to be polite to servers
            time.sleep(1)

    # Build ML corpus
    print(f"\n{'='*60}")
    print(f"  BUILDING ML CORPUS")
    print(f"{'='*60}")

    CORPUS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    corpus_entries = 0

    with open(CORPUS_OUTPUT, "w", encoding="utf-8") as f:
        for t in load_registry():
            if titles and t["content_id"] not in titles:
                continue
            for ep in range(1, max_episodes + 1):
                entry = build_corpus_entry(t, ep)
                if entry:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    corpus_entries += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  ✅ Completed: {completed}/{total_jobs}")
    print(f"  ⏭️  Skipped (already done): {len(skipped)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"  📄 Corpus entries: {corpus_entries}")
    print(f"  📁 Corpus file: {CORPUS_OUTPUT}")
    print(f"{'='*60}")

    if failed:
        print(f"\n  Failed jobs:")
        for f_item in failed:
            print(f"    - {f_item['title']} ep{f_item['ep']}: {f_item['error']}")


def main():
    parser = argparse.ArgumentParser(description="Batch OCR Pipeline for Webtoon titles")
    parser.add_argument("--titles", nargs="+", help="Specific content_ids to process (default: all)")
    parser.add_argument("--episodes", type=int, default=10, help="Number of episodes per title (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without running")
    args = parser.parse_args()

    run_batch(titles=args.titles, max_episodes=args.episodes, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
