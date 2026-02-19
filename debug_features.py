from models.script_feature_extractor import extract_script_features
from pathlib import Path

file_path = Path("data/script_like_corpus/Action_High_13.txt")
text = file_path.read_text(encoding="utf-8")

print(f"File size: {len(text)}")
print(f"First 100 chars: {text[:100]}")

features = extract_script_features(text, "action")
print(f"Features: {features}")
