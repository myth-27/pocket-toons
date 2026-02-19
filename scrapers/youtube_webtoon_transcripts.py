from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript,
)

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        # Fallback for older Python versions
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


CONFIG_PATH = Path("config/settings.yaml")

TRANSCRIPT_BLOCKED = False
TRANSCRIPT_BLOCK_REASON = ""


@dataclass
class VideoInfo:
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: int
    description: str = ""  # Added for filtering


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_youtube_api_key(settings: dict) -> str:
    # Prefer environment variable for safety
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        return api_key

    api_key = settings.get("youtube", {}).get("api_key")
    if not api_key or "YOUR_YOUTUBE_API_KEY_HERE" in str(api_key):
        raise RuntimeError(
            "YouTube API key not configured. Set YOUTUBE_API_KEY env var or "
            "edit config/settings.yaml under youtube.api_key."
        )
    return str(api_key)


def youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def is_youtube_api_rate_limited(err: HttpError) -> bool:
    """
    Detect YouTube Data API rate limiting/quota errors.
    We keep it string-based to avoid depending on googleapiclient internals.
    """
    try:
        status = int(getattr(getattr(err, "resp", None), "status", 0) or 0)
    except Exception:
        status = 0

    msg = str(err).lower()
    if status in (403, 429) and any(
        token in msg
        for token in (
            "quota",
            "quotaexceeded",
            "ratelimitexceeded",
            "daily limit",
            "user-rate limit",
            "too many requests",
        )
    ):
        return True
    return False


def is_transcript_ip_blocked_error(err: Exception) -> bool:
    """
    Detect when youtube-transcript-api is being blocked by YouTube (IP ban / request blocked).
    When this happens, continuing to request transcripts usually makes it worse.
    """
    msg = str(err).lower()
    return any(
        token in msg
        for token in (
            "youtube is blocking requests from your ip",
            "requestblocked",
            "ipblocked",
            "http error 429",
            "too many requests",
            "temporarily blocked",
        )
    )


def search_top_videos_for_title(
    yt,
    title: str,
    max_results: int = 5,
) -> List[VideoInfo]:
    try:
        search_response = (
            yt.search()
            .list(
                part="id,snippet",
                type="video",
                q=title,
                maxResults=max_results,
                order="viewCount",
                safeSearch="none",
            )
            .execute()
        )
    except HttpError as e:
        if is_youtube_api_rate_limited(e):
            print(f"[ERROR] YouTube API rate-limited/quota hit while searching '{title}'.")
            print(f"        Details: {e}")
            raise
        print(f"[ERROR] YouTube search failed for '{title}': {e}")
        return []

    items = search_response.get("items", [])
    if not items:
        return []

    video_ids = [item["id"]["videoId"] for item in items if "videoId" in item.get("id", {})]
    if not video_ids:
        return []

    # Fetch statistics and descriptions (viewCount, description) in a single batch call
    stats: Dict[str, Dict] = {}
    try:
        videos_response = (
            yt.videos()
            .list(part="snippet,statistics", id=",".join(video_ids))
            .execute()
        )
        for v in videos_response.get("items", []):
            vid = v["id"]
            stats[vid] = v
    except HttpError as e:
        print(f"[WARN] Could not fetch video statistics batch: {e}")

    results: List[VideoInfo] = []
    for item in items:
        vid = item["id"].get("videoId")
        if not vid:
            continue

        snippet = stats.get(vid, {}).get("snippet", item.get("snippet", {}))
        statistics = stats.get(vid, {}).get("statistics", {})

        title_text = snippet.get("title", "")
        channel_title = snippet.get("channelTitle", "")
        published_at = snippet.get("publishedAt", "")
        view_count = int(statistics.get("viewCount", 0))
        description = snippet.get("description", "")

        results.append(
            VideoInfo(
                video_id=vid,
                title=title_text,
                channel_title=channel_title,
                published_at=published_at,
                view_count=view_count,
                description=description,
            )
        )

    return results


def fetch_transcript_segments(
    video_id: str,
    language: str,
    include_auto_generated: bool,
) -> List[dict]:
    # youtube-transcript-api expects a list of language codes
    languages = [language]
    if include_auto_generated:
        languages.append(f"{language}-orig")

    try:
        global TRANSCRIPT_BLOCKED, TRANSCRIPT_BLOCK_REASON
        if TRANSCRIPT_BLOCKED:
            return []

        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        # Convert FetchedTranscript to list of dicts with text, start, duration
        segments = [
            {
                "text": entry.text,
                "start": entry.start,
                "duration": entry.duration,
            }
            for entry in transcript
        ]
        return segments
    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript) as e:
        # Some of these exceptions include IP blocking messages inside their text.
        if is_transcript_ip_blocked_error(e):
            TRANSCRIPT_BLOCKED = True
            TRANSCRIPT_BLOCK_REASON = str(e)
            print("[ERROR] Transcript requests appear IP-blocked / rate-limited. Stopping transcript fetches.")
            return []
        print(f"[WARN] No transcript for video {video_id}: {e}")
        return []
    except Exception as e:  # Defensive: any unexpected error
        if is_transcript_ip_blocked_error(e):
            TRANSCRIPT_BLOCKED = True
            TRANSCRIPT_BLOCK_REASON = str(e)
            print("[ERROR] Transcript requests appear IP-blocked / rate-limited. Stopping transcript fetches.")
            return []
        print(f"[ERROR] Failed to fetch transcript for video {video_id}: {e}")
        return []


def read_titles_from_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Titles file not found: {path}")
    titles: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            title = line.strip()
            if title:
                titles.append(title)
    return titles


def iter_titles(
    cli_titles: Iterable[str],
    titles_file: Optional[Path],
) -> List[str]:
    titles: List[str] = []
    if titles_file is not None:
        titles.extend(read_titles_from_file(titles_file))
    titles.extend(t.strip() for t in cli_titles if t.strip())

    # Remove duplicates while preserving order
    seen = set()
    uniq: List[str] = []
    for t in titles:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def save_jsonl(
    records: Iterable[dict],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ============================================================================
# FILTERING AND CLASSIFICATION FUNCTIONS
# ============================================================================

def should_exclude_by_title(video_title: str) -> bool:
    """
    Hard exclusion filter: Exclude videos with certain keywords in title.
    These typically indicate music videos, OSTs, shorts, etc.
    
    To tune: Modify the exclude_keywords list below.
    """
    exclude_keywords = ["music", "ost", "mv", "official", "visualizer", "shorts"]
    title_lower = video_title.lower()
    return any(keyword in title_lower for keyword in exclude_keywords)


def should_include_by_content(video_title: str, video_description: str) -> bool:
    """
    Positive inclusion filter: Only keep videos that match content keywords.
    Must have relevant keywords in title OR description.
    
    To tune: Modify the title_keywords and desc_keywords lists below.
    """
    title_keywords = ["review", "summary", "explained", "episode", "analysis", "recap", "story"]
    desc_keywords = ["webtoon", "anime", "episode", "plot", "story"]
    
    title_lower = video_title.lower()
    desc_lower = video_description.lower()
    
    # Check title keywords
    if any(keyword in title_lower for keyword in title_keywords):
        return True
    
    # Check description keywords
    if any(keyword in desc_lower for keyword in desc_keywords):
        return True
    
    return False


def passes_transcript_quality(transcript_segments: List[dict]) -> bool:
    """
    Transcript quality filter: Ensure transcripts meet minimum quality thresholds.
    - Must have segments
    - Must have at least 300 words total
    - Must have at least 20 segments
    
    To tune: Modify MIN_WORD_COUNT and MIN_SEGMENTS below.
    """
    MIN_WORD_COUNT = 300
    MIN_SEGMENTS = 20
    
    if not transcript_segments:
        return False
    
    if len(transcript_segments) < MIN_SEGMENTS:
        return False
    
    # Count total words across all segments
    total_words = sum(len(seg.get("text", "").split()) for seg in transcript_segments)
    if total_words < MIN_WORD_COUNT:
        return False
    
    return True


def classify_content_type(video_title: str, transcript_segments: List[dict]) -> str:
    """
    Rule-based content type classification.
    Assigns content_type based on title keywords and transcript characteristics.
    """
    title_lower = video_title.lower()
    
    # Review/Analysis content
    if any(kw in title_lower for kw in ["review", "analysis", "explained"]):
        return "review"
    
    # Summary/Recap content
    if any(kw in title_lower for kw in ["summary", "recap"]):
        return "summary"
    
    # Episode read/walkthrough content
    if "episode" in title_lower and any(kw in title_lower for kw in ["read", "walkthrough"]):
        return "episode_read"
    
    # Music content (should be filtered out, but classify for completeness)
    if any(kw in title_lower for kw in ["music", "ost", "mv"]):
        return "music"
    
    # Short clips (check duration)
    if transcript_segments:
        total_duration = sum(seg.get("duration", 0) for seg in transcript_segments)
        if total_duration < 300:  # Less than 5 minutes
            return "clip"
    
    return "unknown"


def clean_transcript_text(transcript_segments: List[dict]) -> str:
    """
    Clean and normalize transcript text.
    - Join all segments
    - Lowercase
    - Remove common filler words
    - Normalize whitespace
    """
    # Common filler words to remove
    filler_words = {
        "um", "uh", "er", "ah", "oh", "hmm", "like", "you know",
        "i mean", "well", "so", "actually", "basically", "literally"
    }
    
    # Join all segment texts
    full_text = " ".join(seg.get("text", "") for seg in transcript_segments)
    
    # Lowercase
    full_text = full_text.lower()
    
    # Remove filler words (simple word boundary matching)
    words = full_text.split()
    cleaned_words = [w for w in words if w not in filler_words]
    
    # Normalize whitespace
    cleaned_text = " ".join(cleaned_words)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def save_processed_csv(
    records: List[dict],
    output_path: Path,
) -> None:
    """
    Save processed records to CSV with normalized fields.
    Columns: webtoon_title, video_id, content_type, view_count, language, word_count, clean_text
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow([
            "webtoon_title",
            "video_id",
            "content_type",
            "view_count",
            "language",
            "word_count",
            "clean_text"
        ])
        
        # Write data rows
        for record in records:
            video = record.get("video", {})
            transcript_segments = record.get("transcript_segments", [])
            clean_text = clean_transcript_text(transcript_segments)
            word_count = count_words(clean_text)
            
            writer.writerow([
                record.get("webtoon_title", ""),
                video.get("video_id", ""),
                record.get("content_type", "unknown"),
                video.get("view_count", 0),
                record.get("language", "en"),
                word_count,
                clean_text
            ])


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "For each Webtoon title, search YouTube, take the top N videos by "
            "view count, fetch transcripts, and write JSONL."
        )
    )
    parser.add_argument(
        "--title",
        action="append",
        default=[],
        help="Webtoon title (can be repeated).",
    )
    parser.add_argument(
        "--titles-file",
        type=str,
        default=None,
        help="Path to a text file with one Webtoon title per line.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Max number of YouTube videos per title (default: 5).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSONL file path (default: data/raw/webtoon_youtube_transcripts.jsonl).",
    )
    parser.add_argument(
        "--csv-output",
        type=str,
        default=None,
        help="Output CSV file path (default: data/processed/webtoon_youtube_transcripts.csv).",
    )
    parser.add_argument(
        "--limit-titles",
        type=int,
        default=None,
        help="Limit processing to first N titles (for testing).",
    )
    return parser


def main() -> None:
    settings = load_settings()
    parser = build_arg_parser()
    args = parser.parse_args()

    titles_file = Path(args.titles_file) if args.titles_file else None
    titles = iter_titles(args.title, titles_file)
    if not titles:
        print("No titles provided. Use --title or --titles-file.")
        return

    # Limit to 5 titles for now (or custom limit if specified)
    if args.limit_titles:
        titles = titles[:args.limit_titles]
    else:
        titles = titles[:5]  # Default limit to 5 titles
    
    print(f"[INFO] Processing {len(titles)} titles (limited for testing)")

    raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
    processed_dir = settings.get("paths", {}).get("processed_data_dir", "data/processed")
    
    output_path = Path(args.output) if args.output else Path(raw_dir) / "webtoon_youtube_transcripts.jsonl"
    csv_output_path = Path(args.csv_output) if args.csv_output else Path(processed_dir) / "webtoon_youtube_transcripts.csv"

    yt_cfg = settings.get("youtube", {})
    language = yt_cfg.get("language", "en")
    include_auto = bool(yt_cfg.get("include_auto_generated", True))

    api_key = get_youtube_api_key(settings)
    yt = youtube_client(api_key)

    all_records: List[dict] = []
    filtered_count = 0
    transcript_blocked_hits = 0

    for title in titles:
        print(f"\n=== Processing title: {title} ===")
        try:
            videos = search_top_videos_for_title(yt, title, max_results=args.max_results)
        except HttpError:
            # Rate limit / quota – stop early to avoid burning quota.
            print("[ERROR] Stopping run due to YouTube Data API rate limit/quota.")
            break
        if not videos:
            print(f"[INFO] No videos found for '{title}'")
            continue

        for v in videos:
            print(f"  - Checking: {v.video_id} ({v.view_count} views): {v.title}")
            
            # 1. Hard exclusion filter (title-based)
            if should_exclude_by_title(v.title):
                print(f"    [FILTERED] Excluded by title keywords")
                filtered_count += 1
                continue
            
            # 2. Positive inclusion filter (title OR description)
            if not should_include_by_content(v.title, v.description):
                print(f"    [FILTERED] Does not match inclusion keywords")
                filtered_count += 1
                continue
            
            # Fetch transcript
            segments = fetch_transcript_segments(
                video_id=v.video_id,
                language=language,
                include_auto_generated=include_auto,
            )

            if TRANSCRIPT_BLOCKED:
                transcript_blocked_hits += 1
                print("[ERROR] Transcript fetching is currently blocked. Ending early to avoid worsening the block.")
                break
            
            # 3. Transcript quality filter
            if not passes_transcript_quality(segments):
                print(f"    [FILTERED] Transcript quality too low (empty, <300 words, or <20 segments)")
                filtered_count += 1
                continue
            
            # 4. Classify content type
            content_type = classify_content_type(v.title, segments)
            
            print(f"    [KEPT] Content type: {content_type}, Segments: {len(segments)}")

            record = {
                "webtoon_title": title,
                "search_query": title,
                "video": asdict(v),
                "transcript_segments": segments,
                "content_type": content_type,
                "language": language,
            }
            all_records.append(record)

        if TRANSCRIPT_BLOCKED:
            break

    print(f"\n=== Summary ===")
    print(f"Total records kept: {len(all_records)}")
    print(f"Total records filtered: {filtered_count}")
    if TRANSCRIPT_BLOCKED:
        print("[ERROR] Transcript rate-limit / IP block detected during run.")
        if TRANSCRIPT_BLOCK_REASON:
            reason = TRANSCRIPT_BLOCK_REASON.replace("\n", " ").strip()
            if len(reason) > 300:
                reason = reason[:300] + "..."
            print(f"        Reason: {reason}")

    if not all_records:
        print("No results to write (all videos were filtered out).")
        return

    # Save raw JSONL (all records, including filtered metadata)
    save_jsonl(all_records, output_path)
    print(f"Wrote {len(all_records)} records to {output_path}")
    
    # Save processed CSV (normalized, clean output)
    save_processed_csv(all_records, csv_output_path)
    print(f"Wrote processed CSV to {csv_output_path}")


if __name__ == "__main__":
    main()

