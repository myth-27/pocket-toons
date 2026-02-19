import pandas as pd
import logging
from pathlib import Path
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nlp_signals.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION: Keyword Lists ---

# A. Emotional Intensity Keywords
KEYWORDS_EXCITEMENT = {
    'wow', 'omg', 'insane', 'crazy', 'hyped', 'amazing', 'peak', 'goat', 'fire', 'love'
}
KEYWORDS_ANGER_FRUSTRATION = {
    'why', 'nooo', 'wtf', 'hate', 'angry', 'annoyed', 'stupid', 'worst', 'trash'
}
KEYWORDS_SHOCK_SURPRISE = {
    'what', 'twist', 'unexpected', 'expected', 'didn\'t expect', 'shock', 'shook'
}

# B. Addiction / Binge Language Keywords
KEYWORDS_ADDICTION = {
    'can\'t wait', 'cant wait', 'next episode', 'when update', 'binged', 'addicted', 'need more',
    'more please', 'hooked', 'withdrawal'
}

# C. Cliffhanger Frustration Keywords
KEYWORDS_CLIFFHANGER = {
    'that ending', 'why end here', 'cliffhanger', 'nooo end', 'short', 'too short', 'killing me'
}

def calculate_emotional_intensity(text):
    """
    Calculates emotional intensity score based on keyword presence.
    Score = count of matches from excitement, anger, shock lists.
    """
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    
    score = 0
    # Check simple presence or count occurrences? 
    # "Count-based" implies counting occurrences.
    
    # We can join all keywords and count total matches.
    all_emotional = KEYWORDS_EXCITEMENT | KEYWORDS_ANGER_FRUSTRATION | KEYWORDS_SHOCK_SURPRISE
    
    for kw in all_emotional:
        if kw in text_lower:
            # Simple containment check might double count if keywords overlap
            # but for simplicity and speed, and given the nature of these short comments, it's acceptable.
            # Ideally regex \bkw\b but some keywords are phrases.
            score += text_lower.count(kw)
            
    return score

def calculate_addiction_score(text):
    """
    Calculates addiction score based on keyword presence.
    """
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    score = 0
    for kw in KEYWORDS_ADDICTION:
        if kw in text_lower:
            score += 1 # Binary presence per keyword usually better for "addiction" concept but let's do count
    return score

def calculate_cliffhanger_score(text):
    """
    Calculates cliffhanger frustration score.
    """
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    score = 0
    for kw in KEYWORDS_CLIFFHANGER:
        if kw in text_lower:
            score += 1
    return score

def main():
    input_file = Path("data/processed/comments_clean.csv")
    episode_output_file = Path("data/processed/comment_signals_episode.csv")
    title_output_file = Path("data/processed/comment_signals_title.csv")
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return

    logger.info(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)
    logger.info(f"Loaded {len(df)} comments.")

    # 1. Calculate Signals per Comment
    logger.info("Calculating signals per comment...")
    
    # It's faster to apply a single function that returns a series, or apply individual functions.
    # Individual is clearer for maintenance.
    
    df['emotional_intensity_raw'] = df['comment_text'].apply(calculate_emotional_intensity)
    df['addiction_language_raw'] = df['comment_text'].apply(calculate_addiction_score)
    df['cliffhanger_raw'] = df['comment_text'].apply(calculate_cliffhanger_score)
    
    # 2. Aggregation Logic
    
    # A. Episode-level aggregation
    logger.info("Aggregating to episode level...")
    
    # Group by webtoon_title and episode_number
    # user wants: comment_count, emotional_intensity_score, addiction_language_score, cliffhanger_score
    # For scores at episode level, should it be Mean? Sum? 
    # "normalized per episode" usually implies Mean or Rate.
    # If I have 1000 comments, sum will be huge. 
    # Let's assume Mean for "Score" to normalize against comment volume, 
    # OR Sum if measuring total volume of signal. 
    # However, "normalized per episode" in the prompt usually means "relative to something" or just scaled.
    # Given the objective is "content greenlighting" and comparing episodes, 
    # a raw sum is biased by popularity. A mean (intensity per comment) is better for quality of reaction.
    # BUT, prompt says "Output: emotional_intensity_score (Count-based, normalized per episode)".
    # This is ambiguous. "Count-based" = Sum? "Normalized" = Mean?
    # Let's provide BOTH or likely Mean is the safe bet for "intensity".
    # Actually, standard practice for "Intensity Score" of an episode is often just average intensity.
    # Let's simple use Mean for now, but also keeping Total might be useful. 
    # Prompt asks for "Output columns: ... emotional_intensity_score ...". Singular.
    # I will calculate MEAN.
    
    episode_agg = df.groupby(['webtoon_title', 'episode_number']).agg(
        comment_count=('comment_text', 'count'),
        emotional_intensity_score=('emotional_intensity_raw', 'mean'), # Normalized by count
        addiction_language_score=('addiction_language_raw', 'mean'),
        cliffhanger_score=('cliffhanger_raw', 'mean')
    ).reset_index()
    
    # Round scores for readability
    episode_agg['emotional_intensity_score'] = episode_agg['emotional_intensity_score'].round(4)
    episode_agg['addiction_language_score'] = episode_agg['addiction_language_score'].round(4)
    episode_agg['cliffhanger_score'] = episode_agg['cliffhanger_score'].round(4)

    logger.info(f"Saving episode-level signals to {episode_output_file}...")
    episode_agg.to_csv(episode_output_file, index=False)

    # B. Title-level aggregation
    logger.info("Aggregating to title level...")
    
    # Create: avg_emotional_intensity, avg_addiction_language, avg_cliffhanger_score, total_comment_count
    # Should this be average of Episode Scores, or Average of All Comments?
    # "avg_emotional_intensity" -> Likely Average of Episode Scores gives equal weight to episodes.
    # Average of all comments gives weight to popular episodes.
    # Usually Title Level = Average of Episode Levels.
    
    title_agg = episode_agg.groupby('webtoon_title').agg(
        avg_emotional_intensity=('emotional_intensity_score', 'mean'),
        avg_addiction_language=('addiction_language_score', 'mean'),
        avg_cliffhanger_score=('cliffhanger_score', 'mean'),
        total_comment_count=('comment_count', 'sum')
    ).reset_index()
    
    title_agg['avg_emotional_intensity'] = title_agg['avg_emotional_intensity'].round(4)
    title_agg['avg_addiction_language'] = title_agg['avg_addiction_language'].round(4)
    title_agg['avg_cliffhanger_score'] = title_agg['avg_cliffhanger_score'].round(4)

    logger.info(f"Saving title-level signals to {title_output_file}...")
    title_agg.to_csv(title_output_file, index=False)

    # 3. Validation Output
    print("\n--- Validation: Top 5 Episodes by Addiction Language Score ---")
    top_addiction = episode_agg.sort_values(by='addiction_language_score', ascending=False).head(5)
    print(top_addiction[['webtoon_title', 'episode_number', 'addiction_language_score']].to_string(index=False))

    print("\n--- Validation: Top 5 Titles by Avg Emotional Intensity ---")
    top_emotional = title_agg.sort_values(by='avg_emotional_intensity', ascending=False).head(5)
    print(top_emotional[['webtoon_title', 'avg_emotional_intensity']].to_string(index=False))

    logger.info("Done.")

if __name__ == "__main__":
    main()
