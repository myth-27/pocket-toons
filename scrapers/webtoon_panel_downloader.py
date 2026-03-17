import os
import requests
import time
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Optional

class PanelDownloader:
    """
    Downloads Webtoon panels for OCR processing.
    """
    def __init__(self, output_dir: str = "data/raw/panels", user_agent: str = "Mozilla/5.0"):
        self.output_dir = Path(output_dir)
        self.headers = {"User-Agent": user_agent, "Referer": "https://www.webtoons.com/"}

    def download_image(self, url: str, filename: str) -> Optional[Path]:
        """Downloads a single image."""
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=10)
            response.raise_for_status()
            
            filepath = self.output_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            return filepath
        except Exception as e:
            print(f"[ERROR] Failed to download {url}: {e}")
            return None

    def download_episode_panels(self, content_id: str, episode_num: int, image_urls: List[str]) -> List[Path]:
        """
        Downloads all panels for a specific episode into a dedicated folder.
        """
        episode_dir = self.output_dir / content_id / f"ep_{episode_num}"
        episode_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        for i, url in enumerate(image_urls):
            # Extract extension or default to .jpg
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1] or ".jpg"
            filename = f"{content_id}_ep{episode_num}_p{i:03d}{ext}"
            
            path = self.output_dir / content_id / f"ep_{episode_num}" / filename
            
            # Simple check to avoid redownloading
            if path.exists():
                saved_paths.append(path)
                continue
                
            res_path = self.download_image(url, str(path.relative_to(self.output_dir)))
            if res_path:
                saved_paths.append(res_path)
                # Small delay to avoid aggressive scraping signatures
                time.sleep(0.5)
                
        return saved_paths

def main():
    print("Panel Downloader module ready.")

if __name__ == "__main__":
    main()
