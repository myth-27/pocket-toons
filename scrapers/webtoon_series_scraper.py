from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import requests
import yaml
from bs4 import BeautifulSoup

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


CONFIG_PATH = Path("config/settings.yaml")


@dataclass
class SeriesInfo:
    title: str
    author: str
    description: str
    genre: str
    rating: Optional[float] = None
    subscribers: Optional[int] = None
    total_episodes: Optional[int] = None
    status: Optional[str] = None  # e.g., "ongoing", "completed"
    url: str = ""


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_html(url: str, user_agent: str, timeout: int) -> str:
    """Fetch HTML content from a URL."""
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_series_info(series_url: str, html: str) -> SeriesInfo:
    """
    Parse series information from HTML.
    
    This is a generic parser that attempts to extract common webtoon metadata.
    You may need to customize selectors based on the specific site structure.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Generic extraction - customize selectors for your target site
    # These are placeholder patterns that work for many sites
    
    # Try to find title (common patterns)
    title = ""
    title_selectors = [
        "h1.title", ".series-title", "[class*='title']", "h1", ".title"
    ]
    for selector in title_selectors:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break
    
    # Try to find author
    author = ""
    author_selectors = [
        ".author", "[class*='author']", ".creator", "[class*='creator']"
    ]
    for selector in author_selectors:
        elem = soup.select_one(selector)
        if elem:
            author = elem.get_text(strip=True)
            break
    
    # Try to find description
    description = ""
    desc_selectors = [
        ".description", "[class*='description']", ".summary", "[class*='summary']"
    ]
    for selector in desc_selectors:
        elem = soup.select_one(selector)
        if elem:
            description = elem.get_text(strip=True)
            break
    
    # Try to find genre
    genre = ""
    genre_selectors = [
        ".genre", "[class*='genre']", ".category", "[class*='category']"
    ]
    for selector in genre_selectors:
        elem = soup.select_one(selector)
        if elem:
            genre = elem.get_text(strip=True)
            break
    
    # Try to find rating (if available)
    rating = None
    rating_elem = soup.select_one("[class*='rating']") or soup.select_one("[class*='score']")
    if rating_elem:
        rating_text = rating_elem.get_text(strip=True)
        try:
            rating = float(rating_text.split()[0])
        except (ValueError, IndexError):
            pass
    
    return SeriesInfo(
        title=title or "Unknown",
        author=author or "Unknown",
        description=description or "",
        genre=genre or "",
        rating=rating,
        url=series_url,
    )


def save_series_info(series_info: SeriesInfo, output_path: Path) -> None:
    """Save series information to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(series_info), f, ensure_ascii=False, indent=2)


def scrape_series_info(series_url: str, output_path: Path | None = None) -> Path:
    """Scrape series information from a webtoon series page."""
    settings = load_settings()
    scraping_cfg = settings.get("scraping", {})
    
    user_agent = scraping_cfg.get("user_agent", "GreenlightIntelligenceBot/0.1")
    timeout = int(scraping_cfg.get("request_timeout_seconds", 10))
    
    html = fetch_html(series_url, user_agent=user_agent, timeout=timeout)
    series_info = parse_series_info(series_url, html)
    
    if output_path is None:
        raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
        # Create filename from series title (sanitized)
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in series_info.title)
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        output_path = Path(raw_dir) / f"series_info_{safe_title}.json"
    
    save_series_info(series_info, output_path)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape webtoon series information (title, author, description, genre, etc.)"
    )
    parser.add_argument(
        "series_url",
        help="URL of the webtoon series page",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output JSON path (default: data/raw/series_info_<title>.json)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    
    output = Path(args.output) if args.output is not None else None
    output_path = scrape_series_info(args.series_url, output)
    print(f"Saved series info to {output_path}")


if __name__ == "__main__":
    main()
