from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import List, Set

import pandas as pd
from langdetect import detect, LangDetectException

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


def read_comments_jsonl(jsonl_path: Path) -> List[dict]:
    """Read comments from JSONL file."""
    comments = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                comments.append(json.loads(line))
    return comments


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_spam(text: str) -> bool:
    """
    Detect spam comments using simple heuristics.
    - Excessive repetition
    - Too many special characters
    - Suspicious patterns
    """
    text_lower = text.lower()
    
    # Check for excessive repetition (same word repeated many times)
    words = text_lower.split()
    if len(words) > 0:
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        max_repetition = max(word_counts.values()) if word_counts else 0
        if max_repetition > len(words) * 0.5:  # More than 50% repetition
            return True
    
    # Check for excessive special characters
    special_char_ratio = len(re.findall(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]', text)) / max(len(text), 1)
    if special_char_ratio > 0.3:  # More than 30% special characters
        return True
    
    # Check for suspicious patterns (all caps, excessive punctuation)
    if text.isupper() and len(text) > 20:
        return True
    
    # Check for common spam patterns
    spam_patterns = [
        r'click here',
        r'buy now',
        r'free money',
        r'http[s]?://',  # URLs
        r'www\.',
    ]
    for pattern in spam_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False


def detect_language(text: str) -> str:
    """Detect language of text. Returns 'en' for English, 'unknown' otherwise."""
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return "unknown"


def drop_duplicates(comments: List[dict]) -> List[dict]:
    """Drop duplicate comments based on text content."""
    seen: Set[str] = set()
    unique_comments = []
    
    for comment in comments:
        text = normalize_whitespace(comment.get("comment_text", "").lower())
        if text and text not in seen:
            seen.add(text)
            unique_comments.append(comment)
    
    return unique_comments


def clean_comments(comments: List[dict]) -> List[dict]:
    """
    Clean and normalize comments:
    - Drop duplicates
    - Language detection (keep English only)
    - Remove spam
    - Normalize whitespace
    """
    print(f"[INFO] Starting with {len(comments)} comments")
    
    # Drop duplicates
    comments = drop_duplicates(comments)
    print(f"[INFO] After dropping duplicates: {len(comments)} comments")
    
    cleaned = []
    spam_count = 0
    non_english_count = 0
    
    for comment in comments:
        text = comment.get("comment_text", "")
        
        # Normalize whitespace
        text = normalize_whitespace(text)
        if not text:
            continue
        
        # Update comment text
        comment["comment_text"] = text
        
        # Check for spam
        if is_spam(text):
            spam_count += 1
            continue
        
        # Language detection (keep English only)
        lang = detect_language(text)
        if lang != "en":
            non_english_count += 1
            continue
        
        cleaned.append(comment)
    
    print(f"[INFO] Removed {spam_count} spam comments")
    print(f"[INFO] Removed {non_english_count} non-English comments")
    print(f"[INFO] Final cleaned count: {len(cleaned)} comments")
    
    return cleaned


def save_clean_comments_csv(comments: List[dict], output_path: Path) -> None:
    """Save cleaned comments to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for comment in comments:
        text = comment.get("comment_text", "")
        rows.append({
            "webtoon_title": comment.get("webtoon_title", ""),
            "episode_number": comment.get("episode_number"),
            "comment_text": text,
            "word_count": word_count(text),
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"[INFO] Saved to {output_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean and normalize webtoon comments"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/raw/webtoon_comments.jsonl",
        help="Input JSONL file path (default: data/raw/webtoon_comments.jsonl)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV file path (default: data/processed/webtoon_comments_clean.csv)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    
    # Read input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return
    
    print(f"[INFO] Reading comments from {input_path}")
    comments = read_comments_jsonl(input_path)
    
    if not comments:
        print("[WARN] No comments found in input file")
        return
    
    # Clean comments
    cleaned_comments = clean_comments(comments)
    
    if not cleaned_comments:
        print("[WARN] No comments remained after cleaning")
        return
    
    # Setup output path
    output_path = Path(args.output) if args.output else Path("data/processed/webtoon_comments_clean.csv")
    
    # Save cleaned comments
    save_clean_comments_csv(cleaned_comments, output_path)
    print(f"\n[SUCCESS] Cleaned comments saved to {output_path}")


if __name__ == "__main__":
    main()
