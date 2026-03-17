"""
Real Reddit Scraper — Uses PRAW to access the official Reddit Developer API
to fetch actual posts about each webtoon/manhwa title from r/manhwa, r/webtoons, r/manga.

Requires Reddit API credentials in config/settings.yaml under the 'reddit' key.

Usage:
    python scrapers/reddit_real_scraper.py
    python scrapers/reddit_real_scraper.py --titles tower_of_god solo_leveling
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

import praw
import yaml

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
OUTPUT_PATH = Path("data/raw/reddit_posts_real.jsonl")

SUBREDDITS = ["manhwa", "webtoons", "manga", "anime"]
USER_AGENT = "PocketToonsBot/1.0 (Research Project)"
MAX_POSTS_PER_SUB = 25

def load_settings():
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def init_praw():
    settings = load_settings()
    reddit_config = settings.get("reddit", {})
    client_id = os.environ.get("REDDIT_CLIENT_ID") or reddit_config.get("client_id")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET") or reddit_config.get("client_secret")
    
    if not client_id or not client_secret:
        print("❌ ERROR: Reddit API credentials missing.")
        print("Please add 'client_id' and 'client_secret' under 'reddit' in config/settings.yaml")
        print("You can get these at: https://www.reddit.com/prefs/apps")
        return None
        
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=USER_AGENT
    )

def load_registry():
    titles = []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles.append(row)
    return titles

def scrape_title(reddit, content_id, title_name, aliases=""):
    """Scrape Reddit posts for a single title across all target subreddits using PRAW."""
    all_posts = []
    search_terms = [title_name]

    if aliases:
        search_terms.extend([a.strip() for a in aliases.split("|") if a.strip()])

    search_terms = list(set(search_terms))[:3]

    for subreddit_name in SUBREDDITS:
        try:
            sub = reddit.subreddit(subreddit_name)
            for term in search_terms:
                raw_query = f'"{term}"' # exact phrase search
                # PRAW search iterator
                for submission in sub.search(raw_query, sort="relevance", time_filter="all", limit=MAX_POSTS_PER_SUB):
                    all_posts.append({
                        "content_id": content_id,
                        "search_term": term,
                        "title": submission.title,
                        "selftext": submission.selftext[:500],
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "upvote_ratio": submission.upvote_ratio,
                        "created_utc": submission.created_utc,
                        "subreddit": subreddit_name,
                        "permalink": submission.permalink,
                    })
                time.sleep(1) # Be gentle with PRAW
        except Exception as e:
            print(f"    ⚠️ Error searching r/{subreddit_name} for '{term}': {e}")

    # Deduplicate by permalink
    seen = set()
    unique_posts = []
    for post in all_posts:
        if post["permalink"] not in seen:
            seen.add(post["permalink"])
            unique_posts.append(post)

    return unique_posts

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Real Reddit Scraper (PRAW)")
    parser.add_argument("--titles", nargs="+", help="Specific content_ids")
    args = parser.parse_args()

    reddit = init_praw()
    if not reddit:
        sys.exit(1)

    registry = load_registry()
    if args.titles:
        registry = [r for r in registry if r["content_id"] in args.titles]

    print(f"\n{'='*60}")
    print(f"  REAL REDDIT SCRAPER (Official API / PRAW)")
    print(f"  Titles: {len(registry)} | Subreddits: {', '.join(SUBREDDITS)}")
    print(f"{'='*60}\n")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    existing.add(json.loads(line)["content_id"])
                except Exception:
                    pass

    total_posts = 0

    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for i, item in enumerate(registry):
            cid = item["content_id"]
            title = item["canonical_title"]
            aliases = item.get("aliases", "")

            if cid in existing and not args.titles:
                print(f"  [{i+1}/{len(registry)}] ⏭️  {title} — already scraped")
                continue

            print(f"  [{i+1}/{len(registry)}] 🔄 {title}...")

            posts = scrape_title(reddit, cid, title, aliases)

            for post in posts:
                f.write(json.dumps(post, ensure_ascii=False) + "\n")
            f.flush()

            total_posts += len(posts)
            avg_score = sum(p["score"] for p in posts) / len(posts) if posts else 0
            print(f"           ✅ {len(posts)} posts (avg score: {avg_score:.0f})")

    print(f"\n{'='*60}")
    print(f"  COMPLETE — {total_posts} total posts saved to {OUTPUT_PATH}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

