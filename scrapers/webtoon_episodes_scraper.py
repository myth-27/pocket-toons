from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

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
class EpisodeMetadata:
    webtoon_title: str
    series_url: str
    episode_number: Optional[int]
    episode_title: str
    episode_url: Optional[str]
    likes: Optional[int]
    publish_date: Optional[str]


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_webtoon_urls(csv_path: Path) -> List[dict]:
    """Read webtoon URLs from CSV file."""
    urls = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls.append({
                "webtoon_title": row.get("webtoon_title", ""),
                "series_url": row.get("series_url", ""),
            })
    return urls


def setup_chrome_driver(headless: bool = False) -> webdriver.Chrome:
    """Setup Chrome WebDriver with appropriate options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Try to use webdriver-manager if available, otherwise use system ChromeDriver
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("[INFO] Using webdriver-manager for ChromeDriver")
    except ImportError:
        # Fallback to system ChromeDriver
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("[INFO] Using system ChromeDriver")
        except WebDriverException as e:
            print(f"[ERROR] Failed to initialize ChromeDriver: {e}")
            print("[INFO] Options:")
            print("  1. Install webdriver-manager: pip install webdriver-manager")
            print("  2. Or download ChromeDriver from https://chromedriver.chromium.org/ and add to PATH")
            raise
    
    return driver


def scroll_to_load_episodes(driver: webdriver.Chrome, max_scrolls: int = 50) -> None:
    """
    Scroll down to load all episodes via infinite scroll.
    Uses random delays between scrolls to appear more natural.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    no_change_count = 0
    
    while scroll_count < max_scrolls:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Random sleep between 2-5 seconds
        sleep_time = random.uniform(2.0, 5.0)
        time.sleep(sleep_time)
        
        # Check if new content loaded
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 3:  # No change for 3 scrolls, likely done
                break
        else:
            no_change_count = 0
        
        last_height = new_height
        scroll_count += 1
        
        # Scroll back up a bit to trigger lazy loading
        if scroll_count % 5 == 0:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
            time.sleep(random.uniform(1.0, 2.0))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # Scroll to top to ensure all episodes are in DOM
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


def extract_episode_number(text: str) -> Optional[int]:
    """Extract episode number from text."""
    # Common patterns: "Episode 123", "Ep. 123", "#123", "123"
    patterns = [
        r'episode\s*#?\s*(\d+)',
        r'ep\.?\s*#?\s*(\d+)',
        r'#\s*(\d+)',
        r'^\s*(\d+)\s*$',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def parse_likes(likes_text: str) -> Optional[int]:
    """Parse likes count from text (handles K, M suffixes)."""
    if not likes_text:
        return None
    
    likes_text = likes_text.strip().lower().replace(',', '')
    
    # Handle K (thousands) and M (millions)
    if 'k' in likes_text:
        try:
            return int(float(likes_text.replace('k', '')) * 1000)
        except ValueError:
            return None
    elif 'm' in likes_text:
        try:
            return int(float(likes_text.replace('m', '')) * 1000000)
        except ValueError:
            return None
    else:
        try:
            return int(likes_text)
        except ValueError:
            return None


def extract_episodes_from_page(
    driver: webdriver.Chrome,
    webtoon_title: str,
    series_url: str,
) -> List[EpisodeMetadata]:
    """
    Extract episode metadata from the loaded page.
    Handles Webtoons.com structure and common variations.
    """
    episodes: List[EpisodeMetadata] = []
    
    try:
        # Wait for episode list to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li, .episode, [class*='episode']"))
        )
    except TimeoutException:
        print(f"[WARN] Timeout waiting for episodes on {series_url}")
        return episodes
    
    # Common selectors for episode items (Webtoons.com specific)
    episode_selectors = [
        "#_listUl li",  # Webtoons.com main selector
        ".episode_list li",
        "[class*='episode']",
        "li[data-episode-no]",
    ]
    
    episode_elements = []
    for selector in episode_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements and len(elements) > 0:
                episode_elements = elements
                break
        except Exception:
            continue
    
    if not episode_elements:
        print(f"[WARN] No episode elements found for {webtoon_title}")
        return episodes
    
    print(f"[INFO] Found {len(episode_elements)} episode elements")
    
    for elem in episode_elements:
        try:
            # Extract episode title
            title = ""
            title_selectors = [
                ".subj",  # Webtoons.com
                ".episode_title",
                "[class*='title']",
                "a",
            ]
            for sel in title_selectors:
                try:
                    title_elem = elem.find_element(By.CSS_SELECTOR, sel)
                    title = title_elem.text.strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue
            
            if not title:
                continue
            
            # Extract episode URL
            episode_url = None
            try:
                link_elem = elem.find_element(By.TAG_NAME, "a")
                episode_url = link_elem.get_attribute("href")
            except NoSuchElementException:
                pass
            
            # Extract episode number
            episode_number = extract_episode_number(title)
            if episode_number is None:
                # Try to get from data attribute or URL
                try:
                    ep_no = elem.get_attribute("data-episode-no")
                    if ep_no:
                        episode_number = int(ep_no)
                except (ValueError, TypeError):
                    pass
            
            # Extract likes
            likes = None
            likes_selectors = [
                ".like_area .like",
                "[class*='like']",
                ".like_count",
            ]
            for sel in likes_selectors:
                try:
                    likes_elem = elem.find_element(By.CSS_SELECTOR, sel)
                    likes_text = likes_elem.text.strip()
                    likes = parse_likes(likes_text)
                    if likes is not None:
                        break
                except NoSuchElementException:
                    continue
            
            # Extract publish date
            publish_date = None
            date_selectors = [
                ".date",
                "[class*='date']",
                ".publish_date",
            ]
            for sel in date_selectors:
                try:
                    date_elem = elem.find_element(By.CSS_SELECTOR, sel)
                    publish_date = date_elem.text.strip()
                    if publish_date:
                        break
                except NoSuchElementException:
                    continue
            
            episodes.append(EpisodeMetadata(
                webtoon_title=webtoon_title,
                series_url=series_url,
                episode_number=episode_number,
                episode_title=title,
                episode_url=episode_url,
                likes=likes,
                publish_date=publish_date,
            ))
            
        except Exception as e:
            print(f"[WARN] Error extracting episode: {e}")
            continue
    
    return episodes


def scrape_webtoon_episodes(
    webtoon_title: str,
    series_url: str,
    driver: webdriver.Chrome,
) -> List[EpisodeMetadata]:
    """Scrape episodes from a single webtoon series."""
    print(f"\n=== Scraping {webtoon_title} ===")
    print(f"URL: {series_url}")
    
    try:
        # Navigate to series page
        driver.get(series_url)
        time.sleep(2)  # Initial page load
        
        # Scroll to load all episodes
        print("[INFO] Scrolling to load episodes...")
        scroll_to_load_episodes(driver, max_scrolls=50)
        
        # Extract episodes
        print("[INFO] Extracting episode metadata...")
        episodes = extract_episodes_from_page(driver, webtoon_title, series_url)
        
        print(f"[INFO] Extracted {len(episodes)} episodes")
        return episodes
        
    except Exception as e:
        print(f"[ERROR] Failed to scrape {webtoon_title}: {e}")
        return []


def save_episodes_jsonl(episodes: List[EpisodeMetadata], output_path: Path) -> None:
    """Save episodes to JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for episode in episodes:
            f.write(json.dumps(asdict(episode), ensure_ascii=False) + "\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape webtoon episode metadata using Selenium"
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        default="data/external/webtoon_urls.csv",
        help="Path to CSV file with webtoon URLs (default: data/external/webtoon_urls.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSONL file path (default: data/raw/webtoon_episodes.jsonl)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of webtoons to process (for testing)",
    )
    return parser


def main() -> None:
    settings = load_settings()
    parser = build_arg_parser()
    args = parser.parse_args()
    
    # Read CSV file
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        return
    
    webtoon_urls = read_webtoon_urls(csv_path)
    if args.limit:
        webtoon_urls = webtoon_urls[:args.limit]
    
    print(f"[INFO] Processing {len(webtoon_urls)} webtoon series")
    
    # Setup output path
    raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
    output_path = Path(args.output) if args.output else Path(raw_dir) / "webtoon_episodes.jsonl"
    
    # Setup Chrome driver
    print("[INFO] Initializing ChromeDriver...")
    driver = setup_chrome_driver(headless=args.headless)
    
    all_episodes: List[EpisodeMetadata] = []
    
    try:
        for idx, webtoon in enumerate(webtoon_urls, 1):
            print(f"\n[{idx}/{len(webtoon_urls)}] Processing: {webtoon['webtoon_title']}")
            
            episodes = scrape_webtoon_episodes(
                webtoon["webtoon_title"],
                webtoon["series_url"],
                driver,
            )
            
            all_episodes.extend(episodes)
            
            # Random delay between series
            if idx < len(webtoon_urls):
                delay = random.uniform(3.0, 6.0)
                print(f"[INFO] Waiting {delay:.1f}s before next series...")
                time.sleep(delay)
    
    finally:
        driver.quit()
        print("\n[INFO] Browser closed")
    
    # Save results
    if all_episodes:
        save_episodes_jsonl(all_episodes, output_path)
        print(f"\n[SUCCESS] Saved {len(all_episodes)} episodes to {output_path}")
    else:
        print("\n[WARN] No episodes were scraped")


if __name__ == "__main__":
    main()
