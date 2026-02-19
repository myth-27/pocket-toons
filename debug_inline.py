import re
from pathlib import Path

# Mock Keywords
KEYWORDS_EMOTION = {
    'wow', 'omg', 'insane', 'crazy', 'hyped', 'amazing', 'peak', 'goat', 'fire', 'love',
    'hate', 'angry', 'annoyed', 'stupid', 'worst', 'trash', 'cry', 'sad', 'tears', 'sob',
    'scared', 'terrified', 'horror', 'shock', 'shook', 'gasp', 'emotional', 'tension',
    'feeling', 'heart', 'pain', 'joy', 'fear', 'anxiety', 'excitement', 'dramatic', 'intense', 'stakes'
}

def test():
    # Load file
    files = list(Path("data/script_like_corpus").glob("*.txt"))
    if not files:
        print("No files found")
        return
        
    fpath = files[0]
    print(f"Testing file: {fpath}")
    text = fpath.read_text(encoding="utf-8")
    
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    print(f"Word count: {len(words)}")
    print(f"First 20 words: {words[:20]}")
    
    emotion_matches = [w for w in words if w in KEYWORDS_EMOTION]
    print(f"Emotion matches: {emotion_matches}")
    
    score = (len(emotion_matches) / len(words)) * 1000 if words else 0
    print(f"Calculated Score: {score}")

if __name__ == "__main__":
    test()
