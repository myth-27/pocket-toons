"""
YouTube Demand Scorer — Searches for manhwa storytelling/recap videos
for each title and collects demand signals (views, likes, comments).

Usage:
    python scrapers/youtube_demand_scraper.py
    python scrapers/youtube_demand_scraper.py --titles tower_of_god solo_leveling
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

CONFIG_PATH = Path("config/settings.yaml")
REGISTRY_PATH = Path("data/registry/content_registry.csv")
OUTPUT_PATH = Path("data/raw/youtube_demand.jsonl")

# Search queries to find manhwa storytelling/recap videos
SEARCH_TEMPLATES = [
    '"{title}" manhwa recap',
    '"{title}" webtoon explained',
    '"{title}" manhwa story',
]

MAX_RESULTS_PER_QUERY = 10


def load_settings():
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_registry():
    titles = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles.append(row)
    return titles


def search_videos(youtube, query, max_results=10):
    """Search YouTube for videos matching the query."""
    try:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results,
            order="viewCount",
        )
        response = request.execute()
        return response.get("items", [])
    except HttpError as e:
        print(f"    ⚠️  Search error: {e}")
        return []


def get_video_stats(youtube, video_ids):
    """Get detailed statistics for a list of video IDs."""
    if not video_ids:
        return {}
    try:
        request = youtube.videos().list(
            id=",".join(video_ids),
            part="statistics,contentDetails",
        )
        response = request.execute()
        stats = {}
        for item in response.get("items", []):
            s = item.get("statistics", {})
            stats[item["id"]] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            }
        return stats
    except HttpError as e:
        print(f"    ⚠️  Stats error: {e}")
        return {}


def scrape_demand_for_title(youtube, title_name, content_id):
    """Search for storytelling/recap videos for a single title."""
    all_videos = []
    seen_ids = set()

    for template in SEARCH_TEMPLATES:
        query = template.format(title=title_name)
        results = search_videos(youtube, query, MAX_RESULTS_PER_QUERY)

        for item in results:
            vid_id = item["id"]["videoId"]
            if vid_id not in seen_ids:
                seen_ids.add(vid_id)
                all_videos.append({
                    "video_id": vid_id,
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "published": item["snippet"]["publishedAt"],
                })
        time.sleep(0.5)  # Rate limiting

    # Get stats for all found videos
    if all_videos:
        video_ids = [v["video_id"] for v in all_videos]
        # YouTube API allows max 50 IDs per request
        stats = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            stats.update(get_video_stats(youtube, batch))

        for v in all_videos:
            s = stats.get(v["video_id"], {})
            v["views"] = s.get("views", 0)
            v["likes"] = s.get("likes", 0)
            v["comments"] = s.get("comments", 0)

    # Aggregate demand signals
    total_views = sum(v.get("views", 0) for v in all_videos)
    total_likes = sum(v.get("likes", 0) for v in all_videos)
    total_comments = sum(v.get("comments", 0) for v in all_videos)
    avg_views = total_views / len(all_videos) if all_videos else 0
    top_video = max(all_videos, key=lambda v: v.get("views", 0)) if all_videos else None

    return {
        "content_id": content_id,
        "title": title_name,
        "video_count": len(all_videos),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_views": round(avg_views),
        "top_video_title": top_video["title"] if top_video else "",
        "top_video_views": top_video.get("views", 0) if top_video else 0,
        "top_channel": top_video["channel"] if top_video else "",
        "videos": all_videos,  # Full list for reference
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Demand Scorer")
    parser.add_argument("--titles", nargs="+", help="Specific content_ids")
    args = parser.parse_args()

    settings = load_settings()
    api_key = os.environ.get("YOUTUBE_API_KEY") or settings.get("youtube", {}).get("api_key")
    if not api_key:
        print("ERROR: No YouTube API key found")
        return

    youtube = build("youtube", "v3", developerKey=api_key)
    registry = load_registry()

    if args.titles:
        registry = [r for r in registry if r["content_id"] in args.titles]

    print(f"\n{'='*60}")
    print(f"  YOUTUBE DEMAND SCORER")
    print(f"  Titles: {len(registry)}")
    print(f"{'='*60}\n")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing results to support resume
    existing = set()
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    existing.add(json.loads(line)["content_id"])
                except Exception:
                    pass

    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for i, item in enumerate(registry):
            cid = item["content_id"]
            title = item["canonical_title"]

            if cid in existing and not args.titles:
                print(f"  [{i+1}/{len(registry)}] ⏭️  {title} — already scraped")
                continue

            print(f"  [{i+1}/{len(registry)}] 🔄 {title}...")

            try:
                result = scrape_demand_for_title(youtube, title, cid)
                # Save without the full video list for compact JSONL
                output_entry = {k: v for k, v in result.items() if k != "videos"}
                f.write(json.dumps(output_entry, ensure_ascii=False) + "\n")
                f.flush()

                print(f"           ✅ {result['video_count']} videos, {result['total_views']:,} total views")
            except Exception as e:
                print(f"           ❌ Error: {e}")

            time.sleep(1)  # Rate limit between titles

    print(f"\n{'='*60}")
    print(f"  COMPLETE — saved to {OUTPUT_PATH}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
