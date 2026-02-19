from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup


CONFIG_PATH = Path("config/settings.yaml")


@dataclass
class Episode:
    title: str
    url: str


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_html(url: str, user_agent: str, timeout: int) -> str:
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_episode_links(series_url: str, html: str) -> List[Episode]:
    """
    Best-effort generic parser.

    For a real project you will likely want to customize the CSS selectors
    below to match the exact webtoon site structure you are targeting.
    """
    soup = BeautifulSoup(html, "html.parser")
    episodes: List[Episode] = []

    # Placeholder heuristic: collect visible links that look like episode titles.
    for link in soup.find_all("a"):
        href = link.get("href")
        title = link.get_text(strip=True)
        if not href or not title:
            continue

        # Skip very short or obviously non-content links
        if len(title) < 3:
            continue

        full_url = urljoin(series_url, href)
        episodes.append(Episode(title=title, url=full_url))

    return episodes


def save_episodes(episodes: List[Episode], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(ep) for ep in episodes]
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scrape_series(series_url: str, output_path: Path | None = None) -> Path:
    settings = load_settings()
    scraping_cfg = settings.get("scraping", {})

    user_agent = scraping_cfg.get("user_agent", "GreenlightIntelligenceBot/0.1")
    timeout = int(scraping_cfg.get("request_timeout_seconds", 10))

    html = fetch_html(series_url, user_agent=user_agent, timeout=timeout)
    episodes = parse_episode_links(series_url, html)

    if output_path is None:
        raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
        output_path = Path(raw_dir) / "webtoon_episodes.json"

    save_episodes(episodes, output_path)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape a webtoon-like series page and save a simple list "
            "of episode titles + URLs as JSON."
        )
    )
    parser.add_argument(
        "series_url",
        help="URL of the series page to scrape",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output JSON path (default: data/raw/webtoon_episodes.json)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    output = Path(args.output) if args.output is not None else None
    output_path = scrape_series(args.series_url, output)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()

