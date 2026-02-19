import re
import math
from collections import Counter

# Task 2: Script Feature Extraction
# Extract explainable features:
# - emotional_intensity_score
# - cliffhanger_density
# - trope_density (rule-based)
# - character_focus_score
# - pacing_proxy (dialogue vs exposition)

# --- KEYWORD LISTS (Simplified for Rule-Based Logic) ---

KEYWORDS_EMOTION = {
    'wow', 'omg', 'insane', 'crazy', 'hyped', 'amazing', 'peak', 'goat', 'fire', 'love',
    'hate', 'angry', 'annoyed', 'stupid', 'worst', 'trash', 'cry', 'sad', 'tears', 'sob',
    'scared', 'terrified', 'horror', 'shock', 'shook', 'gasp', 'emotional', 'tension',
    'feeling', 'heart', 'pain', 'joy', 'fear', 'anxiety', 'excitement', 'dramatic', 'intense', 'stakes'
}

KEYWORDS_CLIFFHANGER = {
    'suddenly', 'twist', 'reveal', 'secret', 'unknown', 'shadow', 'silence', 'door', 'behind',
    'cliffhanger', 'to be continued', 'end', 'stop', 'wait', 'what', 'who', 'looming', 'threat',
    'realization', 'shocking', 'truth', 'final', 'last', 'moment', 'suspense'
}

KEYWORDS_TROPES = {
    'action': ['level up', 'system', 'dungeon', 'hunter', 'rank', 'gate', 'monster', 'skill', 'awakening', 'fight', 'battle', 'war', 'hero', 'villain', 'power'],
    'romance': ['blush', 'heartbeat', 'gaze', 'hand', 'kiss', 'crush', 'date', 'love', 'flower', 'relationship', 'feelings', 'confession', 'couple', 'eyes'],
    'fantasy': ['magic', 'mana', 'spell', 'dragon', 'sword', 'kingdom', 'empire', 'noble', 'knight', 'wizard', 'witch', 'curse', 'destiny', 'prophecy'],
    'drama': ['bully', 'school', 'gang', 'fight', 'money', 'rich', 'poor', 'revenge', 'plastic surgery', 'scandal', 'rumor', 'friendship', 'betrayal', 'secret']
}

def extract_script_features(script_text: str, genre: str = "unknown"):
    """
    Extracts rule-based features from a script.
    """
    if not isinstance(script_text, str) or not script_text.strip():
        return {
            'emotional_intensity_score': 0.0,
            'cliffhanger_density': 0.0,
            'trope_density': 0.0,
            'character_focus_score': 0.0,
            'pacing_proxy': 0.0,
            'word_count': 0
        }
        
    text_lower = script_text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    word_count = len(words)
    if word_count == 0:
        word_count = 1 # Avoid div by zero
        
    # 1. Emotional Intensity Score
    # Density of emotion keywords * multiplier (e.g. 1000 for readable scale)
    emotion_count = sum(1 for w in words if w in KEYWORDS_EMOTION)
    emotional_intensity = (emotion_count / word_count) * 1000
    
    # 2. Cliffhanger Density
    # Look for accumulation of cliffhanger words, especially at end of scenes/script?
    # Simple density for now as requested.
    cliffhanger_count = sum(1 for w in words if w in KEYWORDS_CLIFFHANGER)
    cliffhanger_density = (cliffhanger_count / word_count) * 1000
    
    # 3. Trope Density
    # Depends on genre. If unknown, check all? Or average?
    # Let's use the specified genre list if available, else all.
    target_tropes = KEYWORDS_TROPES.get(genre.lower(), [])
    if not target_tropes and genre == "unknown":
        # Aggregate all unique trope words
        all_tropes = set()
        for glist in KEYWORDS_TROPES.values():
            all_tropes.update(glist)
        target_tropes = list(all_tropes)
        
    trope_count = sum(text_lower.count(t) for t in target_tropes)
    trope_density = (trope_count / word_count) * 1000
    
    # 4. Character Focus Score
    # Heuristic: Count proper nouns (Capitalized words not at start of sentence)? 
    # Or define characters? Without NLP, counting named entities is hard.
    # Fallback: Count "I", "You", "He", "She", "They" (pronouns) -> Focus on people vs setting.
    # High pronoun usage often indicates character focus.
    pronouns = {'i', 'you', 'he', 'she', 'they', 'him', 'her', 'me', 'us', 'we'}
    pronoun_count = sum(1 for w in words if w in pronouns)
    character_focus = (pronoun_count / word_count) * 100
    
    # 5. Pacing Proxy (Dialogue vs Exposition)
    # Estimate dialogue by quotes.
    # Count characters inside quotes vs total characters.
    quotes = re.findall(r'"([^"]*)"', script_text) # Simple double quote check
    # Also check single quotes or localized quotes if needed, but standard is "
    dialogue_len = sum(len(q) for q in quotes)
    total_len = len(script_text)
    if total_len == 0: total_len = 1
    
    pacing_proxy = dialogue_len / total_len # 0.0 to 1.0. Higher = more dialogue = usually faster pacing.
    
    return {
        'emotional_intensity_score': round(emotional_intensity, 4),
        'cliffhanger_density': round(cliffhanger_density, 4),
        'trope_density': round(trope_density, 4),
        'character_focus_score': round(character_focus, 4),
        'pacing_proxy': round(pacing_proxy, 4),
        'word_count': word_count
    }

if __name__ == "__main__":
    # Tests
    sample_text = 'The hunter entered the dungeon. "Wait!" she screamed. Suddenly, the gate closed. "Oh no."'
    print(extract_script_features(sample_text, "action"))
