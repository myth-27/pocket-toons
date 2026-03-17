import os
try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("❌ Dependency Error: PIL or pytesseract not found. Run: pip install Pillow pytesseract")

class OCRProcessor:
    """
    Experimental OCR processor for extracting text scripts from Webtoon panels.
    Requires Tesseract OCR engine to be installed on the system.
    """
    def __init__(self, tesseract_cmd=None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
    def extract_text(self, image_path):
        """
        Extracts text from a single panel image.
        """
        if not os.path.exists(image_path):
            return f"Error: File {image_path} not found."
            
        try:
            img = Image.open(image_path)
            # Preprocessing could be added here (grayscale, thresholding, etc.)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            return f"OCR Error: {str(e)}"

    def batch_process(self, folder_path):
        """
        Processes all images in a folder and returns a combined script.
        """
        results = {}
        for filename in sorted(os.listdir(folder_path)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                path = os.path.join(folder_path, filename)
                text = self.extract_text(path)
                results[filename] = text
        return results

def main():
    # Example usage
    processor = OCRProcessor()
    # Replace with actual image path for testing
    # text = processor.extract_text("data/raw/sample_panel.jpg")
    # print(text)
    print("OCR Processor ready. Ensure Tesseract is installed: https://github.com/tesseract-ocr/tesseract")

if __name__ == "__main__":
    main()
