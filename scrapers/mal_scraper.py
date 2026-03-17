"""
MAL Ground Truth Scraper — Fetches MyAnimeList ratings for adapted titles
using the free Jikan API (no auth needed).

This provides the ground truth labels needed for ML training:
- MAL score (1-10 rating)
- Members count (popularity)
- Rank and popularity rank
- Adaptation status

Usage:
    python scrapers/mal_scraper.py
    python scrapers/mal_scraper.py --titles tower_of_god solo_leveling
"""

import csv
import json
import sys
import time
from pathlib import Path

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

REGISTRY_PATH = Path("data/registry/content_registry.csv")
OUTPUT_PATH = Path("data/raw/mal_ratings.jsonl")

JIKAN_BASE = "https://api.jikan.moe/v4"


def load_registry():
    titles = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles.append(row)
    return titles


def search_mal(title_name, media_type="anime"):
    """Search MyAnimeList via Jikan for a title."""
    url = f"{JIKAN_BASE}/{media_type}"
    params = {"q": title_name, "limit": 5, "order_by": "members", "sort": "desc"}

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 429:
            print(f"    ⏳ Rate limited, waiting 4s...")
            time.sleep(4)
            response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return []

        data = response.json()
        return data.get("data", [])

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return []


def find_best_match(results, title_name):
    """Find the best matching result from MAL search."""
    title_lower = title_name.lower()

    for result in results:
        # Check main title and alternative titles
        titles_to_check = [result.get("title", "").lower()]
        for alt in result.get("titles", []):
            titles_to_check.append(alt.get("title", "").lower())

        for t in titles_to_check:
            # Check for substring match
            if title_lower in t or t in title_lower:
                return result

    # If no exact match, return the first result if it has decent members
    if results and results[0].get("members", 0) > 1000:
        return results[0]

    return None


def scrape_mal_for_title(title_name):
    """Search MAL for anime and manga versions of a title."""
    results = {}

    # Search anime
    anime_results = search_mal(title_name, "anime")
    anime_match = find_best_match(anime_results, title_name)
    if anime_match:
        results["anime"] = {
            "mal_id": anime_match.get("mal_id"),
            "title": anime_match.get("title"),
            "score": anime_match.get("score"),
            "scored_by": anime_match.get("scored_by", 0),
            "members": anime_match.get("members", 0),
            "rank": anime_match.get("rank"),
            "popularity": anime_match.get("popularity"),
            "status": anime_match.get("status"),
            "episodes": anime_match.get("episodes"),
            "type": anime_match.get("type"),
            "url": anime_match.get("url"),
        }

    time.sleep(1)  # Jikan rate limit: 3 req/sec

    # Search manga
    manga_results = search_mal(title_name, "manga")
    manga_match = find_best_match(manga_results, title_name)
    if manga_match:
        results["manga"] = {
            "mal_id": manga_match.get("mal_id"),
            "title": manga_match.get("title"),
            "score": manga_match.get("score"),
            "scored_by": manga_match.get("scored_by", 0),
            "members": manga_match.get("members", 0),
            "rank": manga_match.get("rank"),
            "popularity": manga_match.get("popularity"),
            "status": manga_match.get("status"),
            "chapters": manga_match.get("chapters"),
            "type": manga_match.get("type"),
            "url": manga_match.get("url"),
        }

    time.sleep(1)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MAL Ground Truth Scraper")
    parser.add_argument("--titles", nargs="+", help="Specific content_ids")
    args = parser.parse_args()

    registry = load_registry()
    if args.titles:
        registry = [r for r in registry if r["content_id"] in args.titles]

    print(f"\n{'='*60}")
    print(f"  MAL GROUND TRUTH SCRAPER (Jikan API)")
    print(f"  Titles: {len(registry)}")
    print(f"{'='*60}\n")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing to support resume
    existing = set()
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    existing.add(json.loads(line)["content_id"])
                except Exception:
                    pass

    adapted_count = 0
    not_adapted = 0

    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for i, item in enumerate(registry):
            cid = item["content_id"]
            title = item["canonical_title"]

            if cid in existing and not args.titles:
                print(f"  [{i+1}/{len(registry)}] ⏭️  {title} — already scraped")
                continue

            print(f"  [{i+1}/{len(registry)}] 🔄 {title}...")

            try:
                results = scrape_mal_for_title(title)

                anime = results.get("anime", {})
                manga = results.get("manga", {})

                is_adapted = bool(anime)
                mal_score = anime.get("score") if anime else None
                manga_score = manga.get("score") if manga else None

                entry = {
                    "content_id": cid,
                    "title": title,
                    "is_adapted": is_adapted,
                    "anime_mal_score": mal_score,
                    "anime_members": anime.get("members", 0) if anime else 0,
                    "anime_rank": anime.get("rank") if anime else None,
                    "anime_status": anime.get("status") if anime else None,
                    "anime_episodes": anime.get("episodes") if anime else None,
                    "manga_mal_score": manga_score,
                    "manga_members": manga.get("members", 0) if manga else 0,
                    "manga_rank": manga.get("rank") if manga else None,
                    "is_adapted": is_adapted,
                }

                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                f.flush()

                if is_adapted:
                    adapted_count += 1
                    print(f"           ✅ ADAPTED — Anime: {mal_score}/10 ({anime.get('members', 0):,} members)")
                else:
                    not_adapted += 1
                    manga_info = f"Manga: {manga_score}/10" if manga_score else "No MAL data"
                    print(f"           📝 Not adapted — {manga_info}")

            except Exception as e:
                print(f"           ❌ Error: {e}")

            time.sleep(2)  # Be polite to Jikan

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"  Adapted (has anime): {adapted_count}")
    print(f"  Not adapted: {not_adapted}")
    print(f"  Saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
