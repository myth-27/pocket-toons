import os
import random
from pathlib import Path

def generate_corpus():
    output_dir = Path("data/script_like_corpus")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    genres = ["Action", "Fantasy", "Romance", "Drama", "Thriller"]
    qualities = ["High", "Medium", "Low"]
    
    # Keyword Banks for Signal Injection
    keywords = {
        "Action": ["fight", "battle", "war", "attack", "defend", "sword", "weapon", "blood", "kill", "enemy", "system", "level", "rank", "skill", "dungeon", "gate", "monster", "hunter", "awakening", "power", "strength", "speed", "agility", "vitality", "mana", "magic", "spell", "fire", "ice", "lightning"],
        "Romance": ["love", "heart", "kiss", "blush", "date", "relationship", "feeling", "emotion", "cry", "tear", "hug", "hold", "hand", "eye", "gaze", "beautiful", "handsome", "cute", "sweet", "warm", "cold", "pain", "break", "hurt", "miss", "want", "need"],
        "Fantasy": ["magic", "mana", "dragon", "elf", "dwarf", "orc", "goblin", "kingdom", "empire", "noble", "knight", "wizard", "witch", "curse", "blessing", "god", "demon", "angel", "spirit", "soul", "destiny", "fate", "legend", "myth", "history", "ancient"],
        "Drama": ["school", "bully", "gang", "fight", "money", "rich", "poor", "revenge", "betrayal", "secret", "lie", "truth", "family", "friend", "enemy", "rival", "love", "hate", "jealousy", "envy", "pride", "shame", "guilt", "fear", "anger", "sadness"],
        "Thriller": ["kill", "murder", "crime", "police", "detective", "mystery", "clue", "proof", "witness", "suspect", "victim", "blood", "knife", "gun", "shoot", "hide", "run", "chase", "escape", "trap", "dark", "shadow", "night", "fear", "terror", "horror"]
    }
    
    emotion_words = ["wow", "omg", "insane", "crazy", "hyped", "amazing", "peak", "goat", "fire", "love", "hate", "angry", "annoyed", "stupid", "worst", "trash", "cry", "sad", "tears", "sob", "scared", "terrified", 'emotional', 'tension', 'stakes']
    cliffhanger_words = ["suddenly", "twist", "reveal", "secret", "unknown", "shadow", "silence", "door", "behind", "cliffhanger", "continued", "shocking", "truth"]

    print(f"Generating corpus in {output_dir}...")
    
    for i in range(20):
        genre = random.choice(genres)
        quality = random.choice(qualities)
        
        # Base Text
        if quality == "High":
            base_text = f"The {genre} story begins with high stakes. "
            base_text += " ".join(random.choices(keywords.get(genre, []), k=10))
            base_text += " ".join(random.choices(emotion_words, k=5))
            base_text += " ".join(random.choices(cliffhanger_words, k=3))
            filler_count = 50
        elif quality == "Medium":
            base_text = f"A standard {genre} story. "
            base_text += " ".join(random.choices(keywords.get(genre, []), k=5))
            base_text += " ".join(random.choices(emotion_words, k=2))
            filler_count = 100
        else:
            base_text = f"A boring {genre} story. "
            base_text += " ".join(random.choices(keywords.get(genre, []), k=1))
            filler_count = 150
            
        # Filler with occasional injection
        filler = []
        for _ in range(filler_count):
            if quality == "High" and random.random() < 0.1:
                filler.append(random.choice(keywords.get(genre, []) + emotion_words))
            else:
                filler.append("text")
                
        content = f"Title: Synthetic {genre} {quality} {i}\nGenre: {genre}\n\n{base_text}\n\n{' '.join(filler)}"
        
        filename = f"{genre}_{quality}_{i}.txt"
        with open(output_dir / filename, "w", encoding="utf-8") as f:
            f.write(content)
            
    print(f"✅ Created 20 synthetic script files with rich signals.")

if __name__ == "__main__":
    generate_corpus()
