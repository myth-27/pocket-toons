from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

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
class EpisodeContent:
    episode_number: Optional[int]
    title: str
    url: str
    images: List[str]  # URLs to episode images
    text_content: str  # Any text content from the episode
    likes: Optional[int] = None
    views: Optional[int] = None
    published_date: Optional[str] = None


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


def parse_episode_content(episode_url: str, html: str) -> EpisodeContent:
    """
    Parse episode content from HTML.
    
    Extracts images, text, and metadata from a webtoon episode page.
    Customize selectors based on your target site structure.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract title
    title = ""
    title_selectors = ["h1", ".episode-title", "[class*='title']", ".title"]
    for selector in title_selectors:
        elem = soup.select_one(selector)
        if elem:
            title = elem.get_text(strip=True)
            break
    
    # Extract episode number from title or URL
    episode_number = None
    if title:
        import re
        match = re.search(r'episode\s*#?(\d+)', title, re.IGNORECASE)
        if match:
            episode_number = int(match.group(1))
    
    # Extract images (common patterns for webtoon images)
    images: List[str] = []
    img_selectors = [
        ".viewer img",
        "[class*='viewer'] img",
        "[class*='episode'] img",
        ".comic img",
        "img[data-url]",
    ]
    
    for selector in img_selectors:
        imgs = soup.select(selector)
        if imgs:
            for img in imgs:
                src = img.get("src") or img.get("data-src") or img.get("data-url")
                if src:
                    # Handle relative URLs
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        from urllib.parse import urljoin
                        src = urljoin(episode_url, src)
                    images.append(src)
            break
    
    # Extract text content (dialogue, narration, etc.)
    text_content = ""
    text_selectors = [
        ".viewer-text",
        "[class*='dialogue']",
        "[class*='text']",
        ".narration",
    ]
    for selector in text_selectors:
        elems = soup.select(selector)
        if elems:
            text_content = " ".join(elem.get_text(strip=True) for elem in elems)
            break
    
    # Extract likes/views if available
    likes = None
    views = None
    
    likes_elem = soup.select_one("[class*='like']") or soup.select_one("[class*='heart']")
    if likes_elem:
        likes_text = likes_elem.get_text(strip=True)
        import re
        match = re.search(r'(\d+)', likes_text.replace(',', ''))
        if match:
            likes = int(match.group(1))
    
    views_elem = soup.select_one("[class*='view']") or soup.select_one("[class*='read']")
    if views_elem:
        views_text = views_elem.get_text(strip=True)
        import re
        match = re.search(r'(\d+)', views_text.replace(',', ''))
        if match:
            views = int(match.group(1))
    
    return EpisodeContent(
        episode_number=episode_number,
        title=title or "Unknown",
        url=episode_url,
        images=images,
        text_content=text_content,
        likes=likes,
        views=views,
    )


def save_episode_content(episode_content: EpisodeContent, output_path: Path) -> None:
    """Save episode content to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(episode_content), f, ensure_ascii=False, indent=2)


def scrape_episode(episode_url: str, output_path: Path | None = None) -> Path:
    """Scrape content from a webtoon episode page."""
    settings = load_settings()
    scraping_cfg = settings.get("scraping", {})
    
    user_agent = scraping_cfg.get("user_agent", "GreenlightIntelligenceBot/0.1")
    timeout = int(scraping_cfg.get("request_timeout_seconds", 10))
    
    html = fetch_html(episode_url, user_agent=user_agent, timeout=timeout)
    episode_content = parse_episode_content(episode_url, html)
    
    if output_path is None:
        raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
        # Create filename from episode number or title
        if episode_content.episode_number:
            filename = f"episode_{episode_content.episode_number:04d}.json"
        else:
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in episode_content.title)
            safe_title = safe_title.replace(' ', '_')[:50]
            filename = f"episode_{safe_title}.json"
        output_path = Path(raw_dir) / filename
    
    save_episode_content(episode_content, output_path)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape webtoon episode content (images, text, metadata)"
    )
    parser.add_argument(
        "episode_url",
        help="URL of the webtoon episode page",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output JSON path (default: data/raw/episode_<number>.json)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    
    output = Path(args.output) if args.output is not None else None
    output_path = scrape_episode(args.episode_url, output)
    print(f"Saved episode content to {output_path}")
    print(f"Found {len(json.load(open(output_path))['images'])} images")


if __name__ == "__main__":
    main()
