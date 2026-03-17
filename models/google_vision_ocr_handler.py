import os
import io
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from google.cloud import vision
except ImportError:
    vision = None

try:
    import easyocr
except ImportError:
    easyocr = None

import requests

class GoogleVisionOCR:
    """
    Multi-strategy OCR handler:
      A) Google Cloud Vision (service account)
      B) Google Cloud Vision (REST API key)
      C) EasyOCR (local, no API needed)
    """
    def __init__(self, credentials_path: Optional[str] = None, api_key: Optional[str] = None):
        self.client = None
        self.api_key = api_key
        self.easyocr_reader = None
        
        # Try Google Vision client first
        if vision:
            try:
                if credentials_path and os.path.exists(credentials_path):
                    self.client = vision.ImageAnnotatorClient.from_service_account_json(credentials_path)
                    print(f"[INFO] Initialized Google Vision client with service account: {credentials_path}")
                elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                    self.client = vision.ImageAnnotatorClient()
                    print("[INFO] Initialized Google Vision client from environment credentials.")
                else:
                    print("[WARN] No service account credentials found.")
            except Exception as e:
                print(f"[ERROR] Failed to initialize Google Vision client: {e}")
        
        # Initialize EasyOCR as fallback
        if not self.client and not self.api_key:
            self._init_easyocr()
        elif not self.client:
            # We have an API key, but init EasyOCR lazily in case REST fails
            pass

    def _init_easyocr(self):
        if easyocr and not self.easyocr_reader:
            try:
                print("[INFO] Initializing EasyOCR (local mode)...")
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                print("[INFO] EasyOCR ready.")
            except Exception as e:
                print(f"[ERROR] Failed to initialize EasyOCR: {e}")

    def extract_text(self, image_path: str) -> str:
        """
        Extracts text from a single image using multiple strategies.
        """
        if not os.path.exists(image_path):
            return f"Error: File {image_path} not found."

        # Strategy A: Official Google Vision client
        if self.client:
            try:
                with io.open(image_path, 'rb') as image_file:
                    content = image_file.read()
                image = vision.Image(content=content)
                response = self.client.document_text_detection(image=image)
                if response.error.message:
                    print(f"[ERROR] Vision API error: {response.error.message}")
                else:
                    return response.full_text_annotation.text.strip()
            except Exception as e:
                print(f"[ERROR] Service account OCR failed: {e}")

        # Strategy B: REST API with API Key
        if self.api_key:
            try:
                with open(image_path, "rb") as image_file:
                    content = base64.b64encode(image_file.read()).decode('utf-8')

                url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"
                payload = {
                    "requests": [{
                        "image": {"content": content},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
                    }]
                }
                
                response = requests.post(url, json=payload, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    responses = data.get("responses", [])
                    if responses and "fullTextAnnotation" in responses[0]:
                        return responses[0]["fullTextAnnotation"]["text"].strip()
                    elif responses and "error" in responses[0]:
                        print(f"[WARN] REST API error: {responses[0]['error']['message']}, falling back to EasyOCR")
                    else:
                        return ""  # No text found in this image
                else:
                    print(f"[WARN] REST API returned {response.status_code}, falling back to EasyOCR")
            except Exception as e:
                print(f"[WARN] REST Exception: {e}, falling back to EasyOCR")

        # Strategy C: EasyOCR (local, no API needed)
        if not self.easyocr_reader:
            self._init_easyocr()
        
        if self.easyocr_reader:
            try:
                results = self.easyocr_reader.readtext(image_path, detail=0, paragraph=True)
                return "\n".join(results).strip()
            except Exception as e:
                return f"OCR Error (EasyOCR): {str(e)}"

        return "Error: No OCR engine available."

    def batch_extract(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Extracts text from multiple images sequentially.
        """
        results = []
        total = len(image_paths)
        for i, path in enumerate(image_paths):
            print(f"  [{i+1}/{total}] Processing {os.path.basename(path)}...", end=" ")
            text = self.extract_text(path)
            word_count = len(text.split()) if text and not text.startswith("Error") else 0
            print(f"({word_count} words)")
            results.append({
                "path": path,
                "text": text
            })
        return results

def test():
    print("OCR Handler loaded.")
    print(f"  Google Vision: {'available' if vision else 'not installed'}")
    print(f"  EasyOCR: {'available' if easyocr else 'not installed'}")

if __name__ == "__main__":
    test()

