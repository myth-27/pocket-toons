import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional, List

# Add parent directory to sys.path if needed for internal imports
sys.path.append(os.getcwd())

from scrapers.webtoon_episode_scraper import scrape_episode, load_settings
from scrapers.webtoon_panel_downloader import PanelDownloader
from models.google_vision_ocr_handler import GoogleVisionOCR

def run_ocr_pipeline(episode_url: str, content_id: str, episode_num: int, credentials_json: Optional[str] = None):
    """
    Executes the full OCR pipeline for a given webtoon episode.
    """
    settings = load_settings()
    raw_dir = settings.get("paths", {}).get("raw_data_dir", "data/raw")
    
    # 1. Scrape Episode Metadata & Image URLs
    print(f"--- STEP 1: Scraping Episode Metadata [{episode_url}] ---")
    json_path = scrape_episode(episode_url)
    with open(json_path, 'r', encoding='utf-8') as f:
        episode_data = json.load(f)
    
    image_urls = episode_data.get("images", [])
    if not image_urls:
        print("[ERROR] No images found for this episode. Scraper might need adjustment.")
        return

    # 2. Download Panels
    print(f"--- STEP 2: Downloading {len(image_urls)} Panels ---")
    downloader = PanelDownloader(output_dir=os.path.join(raw_dir, "panels"))
    panel_paths = downloader.download_episode_panels(content_id, episode_num, image_urls)
    
    # 3. Perform OCR
    print(f"--- STEP 3: Performing Google Vision OCR ---")
    # Try to find credentials in settings or provided via CLI
    vision_cfg = settings.get("vision", {})
    creds = credentials_json or vision_cfg.get("credentials_path")
    api_key = vision_cfg.get("api_key") or settings.get("youtube", {}).get("api_key")
    
    ocr_engine = GoogleVisionOCR(credentials_path=creds, api_key=api_key)
    results = ocr_engine.batch_extract([str(p) for p in panel_paths])
    
    # 4. Consolidate and Save Script
    print(f"--- STEP 4: Consolidating and Saving Script ---")
    full_script = []
    for res in results:
        if res['text'] and not res['text'].startswith("OCR Error"):
            full_script.append(res['text'])
    
    consolidated_text = "\n\n".join(full_script)
    
    script_dir = Path("data/processed/ocr_scripts")
    script_dir.mkdir(parents=True, exist_ok=True)
    
    script_file = script_dir / f"{content_id}_ep{episode_num}_script.txt"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(consolidated_text)
    
    # Also save detailed JSON for further analysis
    detailed_json = script_dir / f"{content_id}_ep{episode_num}_detailed.json"
    with open(detailed_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ OCR PIPELINE COMPLETE.")
    print(f"📄 Script saved to: {script_file}")
    print(f"🛡️  Word Count: {len(consolidated_text.split())}")

def main():
    parser = argparse.ArgumentParser(description="Run Google Vision OCR Pipeline on a Webtoon Episode")
    parser.add_argument("url", help="Webtoon episode URL")
    parser.add_argument("--id", required=True, help="Content ID (e.g., 'tower_of_god')")
    parser.add_argument("--ep", type=int, required=True, help="Episode number")
    parser.add_argument("--creds", help="Path to Google Cloud Service Account JSON")
    
    args = parser.parse_args()
    
    run_ocr_pipeline(args.url, args.id, args.ep, args.creds)

if __name__ == "__main__":
    main()
