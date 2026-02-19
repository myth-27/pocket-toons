import pandas as pd
import numpy as np
from pathlib import Path

# Goal: Create data/processed/episode_signals.csv and data/processed/transcript_signals.csv
# using existing clean files and some derivation/mock logic where real signal extraction logic is missing.

def generate_episode_signals():
    # Input: data/processed/episodes_clean.csv
    # Output: data/processed/episode_signals.csv
    # Columns: webtoon_title, episode_number, log_likes, hook_score, retention_slope, dropoff_risk
    
    input_file = Path("data/processed/episodes_clean.csv")
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    
    # 1. log_likes
    # If like count is 0 or null, handle gracefull
    df['likes'] = df['likes'].fillna(0)
    df['log_likes'] = np.log1p(df['likes'])
    
    # 2. hook_score (0-1)
    # Mock logic: Use random for now as we don't have the granular retention data to calculate it.
    # In production, this would come from retention curves.
    # To keep it deterministic, seed with episode number
    np.random.seed(42)
    df['hook_score'] = np.random.uniform(0.5, 1.0, size=len(df))
    
    # 3. retention_slope (-1 to 1?) -> Normalize to something useful? 
    # Usually slope is negative. Steeper slope = bad. Flatter = good.
    # Let's say range is -0.5 to 0.0.
    # User says "Reward retention_slope". So higher is better (flatter).
    # Let's generate -0.1 to -0.01 (good) and -0.5 (bad).
    df['retention_slope'] = np.random.uniform(-0.3, -0.01, size=len(df))
    
    # 4. dropoff_risk (0 or 1)
    # Random 20% risk
    df['dropoff_risk'] = np.random.choice([0, 1], size=len(df), p=[0.8, 0.2])
    
    output_cols = ['webtoon_title', 'episode_number', 'log_likes', 'hook_score', 'retention_slope', 'dropoff_risk']
    df[output_cols].to_csv("data/processed/episode_signals.csv", index=False)
    print(f"Generated data/processed/episode_signals.csv with {len(df)} rows.")

def generate_transcript_signals():
    # Input: data/processed/transcripts_clean.csv
    # Output: data/processed/transcript_signals.csv
    # Columns: webtoon_title, external_buzz_volume, external_emotion_score, log_view_strength
    
    input_file = Path("data/processed/transcripts_clean.csv")
    # If transcript file doesn't exist or is empty, we must handle it (some titles might not have transcripts)
    if not input_file.exists():
        print(f"Warning: {input_file} not found. Skipping transcript signals generation.")
        return

    try:
        df = pd.read_csv(input_file)
    except pd.errors.EmptyDataError:
        print("Transcript file empty.")
        return

    if df.empty:
        print("Transcript df empty.")
        return

    # Aggregate by title
    # external_buzz_volume = sum of view_count? or count of videos?
    # "volume" usually means quantity. Let's say Sum of Views.
    # log_view_strength = log of average views? 
    # external_emotion_score = average sentiment? (mock 0-1)
    
    title_group = df.groupby('webtoon_title').agg(
        external_buzz_volume=('view_count', 'sum'),
        avg_views=('view_count', 'mean')
    ).reset_index()
    
    title_group['log_view_strength'] = np.log1p(title_group['avg_views'])
    
    # Mock external_emotion_score
    np.random.seed(42)
    title_group['external_emotion_score'] = np.random.uniform(0.5, 1.0, size=len(title_group))
    
    output_cols = ['webtoon_title', 'external_buzz_volume', 'external_emotion_score', 'log_view_strength']
    title_group[output_cols].to_csv("data/processed/transcript_signals.csv", index=False)
    print(f"Generated data/processed/transcript_signals.csv with {len(title_group)} rows.")

if __name__ == "__main__":
    generate_episode_signals()
    generate_transcript_signals()
