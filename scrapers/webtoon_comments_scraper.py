from __future__ import annotations

import argparse
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
class Comment:
    webtoon_title: str
    episode_number: Optional[int]
    comment_text: str
    comment_timestamp: Optional[str]


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_episodes_jsonl(jsonl_path: Path) -> List[dict]:
    """Read episodes from JSONL file."""
    episodes = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                episodes.append(json.loads(line))
    return episodes


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


def is_emoji_only(text: str) -> bool:
    """Check if text contains only emojis and whitespace."""
    # Remove whitespace
    text_no_ws = text.strip()
    if not text_no_ws:
        return True
    
    # Check if all characters are emojis or emoji-related symbols
    # Emoji pattern: includes emojis, emoticons, and other symbols
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U00002700-\U000027BF"  # dingbats
        "]+",
        flags=re.UNICODE
    )
    
    # Remove all emojis and check if anything remains
    text_no_emoji = emoji_pattern.sub("", text_no_ws)
    return len(text_no_emoji.strip()) == 0


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    # Replace multiple spaces/tabs/newlines with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_valid_comment(text: str) -> bool:
    """Check if comment passes filtering rules."""
    # Skip emoji-only comments
    if is_emoji_only(text):
        return False
    
    # Skip comments with < 5 words
    if word_count(text) < 5:
        return False
    
    return True


def scroll_comment_section(
    driver: webdriver.Chrome,
    min_comments: int,
    max_comments: int,
) -> int:
    """
    Scroll comment section to load comments.
    Returns number of comments loaded.
    """
    comments_loaded = 0
    scroll_count = 0
    max_scrolls = 100
    no_change_count = 0
    
    while scroll_count < max_scrolls and comments_loaded < max_comments:
        # Find comment elements
        comment_selectors = [
            ".comment_item",
            "[class*='comment']",
            ".comment_list li",
            "[class*='CommentItem']",
        ]
        
        comments = []
        for selector in comment_selectors:
            try:
                comments = driver.find_elements(By.CSS_SELECTOR, selector)
                if comments:
                    break
            except Exception:
                continue
        
        current_count = len(comments)
        
        # If we have enough comments, check if we've reached min requirement
        if current_count >= min_comments and comments_loaded == current_count:
            no_change_count += 1
            if no_change_count >= 3:
                break
        else:
            no_change_count = 0
        
        comments_loaded = current_count
        
        # Scroll down in comment section
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Random delay between 3-6 seconds
        sleep_time = random.uniform(3.0, 6.0)
        time.sleep(sleep_time)
        
        scroll_count += 1
        
        # Occasionally scroll back up to trigger lazy loading
        if scroll_count % 5 == 0:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
            time.sleep(random.uniform(1.0, 2.0))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    return comments_loaded


def extract_comments_from_page(
    driver: webdriver.Chrome,
    webtoon_title: str,
    episode_number: Optional[int],
    max_comments: int,
) -> List[Comment]:
    """Extract comments from the episode page."""
    comments: List[Comment] = []
    
    # Wait for comment section to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".comment, [class*='comment']"))
        )
    except TimeoutException:
        print(f"[WARN] Comment section not found for episode {episode_number}")
        return comments
    
    # Scroll to load comments
    print(f"[INFO] Scrolling to load comments (target: {max_comments})...")
    comments_loaded = scroll_comment_section(driver, min_comments=10, max_comments=max_comments)
    print(f"[INFO] Loaded {comments_loaded} comment elements")
    
    # Extract comment text and timestamps
    comment_selectors = [
        ".comment_item",
        "[class*='comment']",
        ".comment_list li",
        "[class*='CommentItem']",
    ]
    
    comment_elements = []
    for selector in comment_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                comment_elements = elements[:max_comments]  # Limit to max_comments
                break
        except Exception:
            continue
    
    for elem in comment_elements:
        try:
            # Extract comment text
            text = ""
            text_selectors = [
                ".comment_text",
                "[class*='text']",
                ".text",
                "[class*='content']",
                ".comment",
            ]
            
            for sel in text_selectors:
                try:
                    text_elem = elem.find_element(By.CSS_SELECTOR, sel)
                    text = text_elem.text.strip()
                    if text:
                        break
                except NoSuchElementException:
                    continue
            
            # If no specific text element, get all text
            if not text:
                text = elem.text.strip()
            
            # Normalize whitespace
            text = normalize_whitespace(text)
            
            # Filter comments
            if not is_valid_comment(text):
                continue
            
            # Extract timestamp
            timestamp = None
            timestamp_selectors = [
                "time",
                "[class*='time']",
                "[class*='date']",
                "[class*='timestamp']",
            ]
            
            for sel in timestamp_selectors:
                try:
                    time_elem = elem.find_element(By.CSS_SELECTOR, sel)
                    timestamp = time_elem.get_attribute("datetime") or time_elem.text.strip()
                    if timestamp:
                        break
                except NoSuchElementException:
                    continue
            
            comments.append(Comment(
                webtoon_title=webtoon_title,
                episode_number=episode_number,
                comment_text=text,
                comment_timestamp=timestamp,
            ))
            
        except Exception as e:
            print(f"[WARN] Error extracting comment: {e}")
            continue
    
    return comments


def scrape_episode_comments(
    episode: dict,
    driver: webdriver.Chrome,
    max_comments_per_episode: int,
) -> List[Comment]:
    """Scrape comments from a single episode page."""
    episode_url = episode.get("episode_url")
    if not episode_url:
        print(f"[WARN] No episode URL for episode {episode.get('episode_number')}")
        return []
    
    webtoon_title = episode.get("webtoon_title", "Unknown")
    episode_number = episode.get("episode_number")
    
    print(f"\n=== Scraping comments: {webtoon_title} - Episode {episode_number} ===")
    print(f"URL: {episode_url}")
    
    try:
        # Navigate to episode page
        driver.get(episode_url)
        time.sleep(2)  # Initial page load
        
        # Extract comments
        comments = extract_comments_from_page(
            driver,
            webtoon_title,
            episode_number,
            max_comments=max_comments_per_episode,
        )
        
        print(f"[INFO] Extracted {len(comments)} valid comments")
        return comments
        
    except WebDriverException as e:
        print(f"[ERROR] Page may be blocked or inaccessible: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to scrape comments: {e}")
        return []


def save_comments_jsonl(comments: List[Comment], output_path: Path) -> None:
    """Save comments to JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for comment in comments:
            f.write(json.dumps(asdict(comment), ensure_ascii=False) + "\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape comments from webtoon episodes using Selenium"
    )
    parser.add_argument(
        "--episodes-file",
        type=str,
        default="data/raw/webtoon_episodes.jsonl",
        help="Path to episodes JSONL file (default: data/raw/webtoon_episodes.jsonl)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSONL file path (default: data/raw/webtoon_comments.jsonl)",
    )
    parser.add_argument(
        "--max-comments-per-episode",
        type=int,
        default=100,
        help="Maximum comments to extract per episode (default: 100)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--limit-episodes",
        type=int,
        default=None,
        help="Limit number of episodes to process (for testing)",
    )
    return parser


def main() -> None:
    settings = load_settings()
    parser = build_arg_parser()
    args = parser.parse_args()
    
    # Read episodes file
    episodes_path = Path(args.episodes_file)
    if not episodes_path.exists():
        print(f"[ERROR] Episodes file not found: {episodes_path}")
        return
    
    episodes = read_episodes_jsonl(episodes_path)
    if args.limit_episodes:
        episodes = episodes[:args.limit_episodes]
    
    print(f"[INFO] Processing {len(episodes)} episodes")
    
    # Setup output path
    raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
    output_path = Path(args.output) if args.output else Path(raw_dir) / "webtoon_comments.jsonl"
    
    # Setup Chrome driver
    print("[INFO] Initializing ChromeDriver...")
    driver = setup_chrome_driver(headless=args.headless)
    
    all_comments: List[Comment] = []
    
    try:
        for idx, episode in enumerate(episodes, 1):
            print(f"\n[{idx}/{len(episodes)}] Processing episode {episode.get('episode_number')}")
            
            comments = scrape_episode_comments(
                episode,
                driver,
                max_comments_per_episode=args.max_comments_per_episode,
            )
            
            all_comments.extend(comments)
            
            # Random delay between episodes (3-6 seconds)
            if idx < len(episodes):
                delay = random.uniform(3.0, 6.0)
                print(f"[INFO] Waiting {delay:.1f}s before next episode...")
                time.sleep(delay)
    
    finally:
        driver.quit()
        print("\n[INFO] Browser closed")
    
    # Save results
    if all_comments:
        save_comments_jsonl(all_comments, output_path)
        print(f"\n[SUCCESS] Saved {len(all_comments)} comments to {output_path}")
    else:
        print("\n[WARN] No comments were scraped")


if __name__ == "__main__":
    main()
