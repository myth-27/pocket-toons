import pandas as pd
import numpy as np
from pathlib import Path

# Goal: Create data/processed/genre_profiles.csv
# Inputs: 
# - data/processed/greenlight_ranking.csv (for genre mapping)
# - data/processed/comment_signals_title.csv (for raw emotion/addiction/cliffhanger signals)
# - data/processed/episode_signals.csv (for retention/hook stats if needed, but task mainly mentions emotion/addiction/cliffhanger)

# Task requirements:
# For each genre:
# - median_emotional_intensity
# - top_quartile_emotional_intensity
# - median_addiction_language
# - median_cliffhanger_density
# - acceptable_risk_range (Let's define as [min_risk, max_risk] or similar. Task says "acceptable_risk_range". Let's output min and max.)

def main():
    ranking_file = Path("data/processed/greenlight_ranking.csv")
    comments_file = Path("data/processed/comment_signals_title.csv")
    episodes_file = Path("data/processed/episode_signals.csv")
    output_file = Path("data/processed/genre_profiles.csv")
    input_file = Path("data/processed/transcript_signals.csv")
    episode_file = Path("data/processed/episode_signals.csv")
    comment_file = Path("data/processed/comment_signals.csv")
    titles_file = Path("data/external/webtoon_titles.csv")
    
    if not ranking_file.exists() or not comments_file.exists():
        print("Error: Missing input files.")
        return
        
    df_ranking = pd.read_csv(ranking_file)
    
    # Load Data
    df_ep = pd.read_csv(episode_file)
    df_cm = pd.read_csv(comment_file)
    if titles_file.exists():
        df_titles = pd.read_csv(titles_file)
    else:
        df_titles = pd.DataFrame({'title': df_ep['title'].unique(), 'genre': 'Action'}) # Fallback

    df_comments = pd.read_csv(comments_file)
    
    # Merge genre from ranking to signals
    df_merged = pd.merge(df_comments, df_ranking[['webtoon_title', 'genre', 'risk_penalty']], on='webtoon_title', how='inner')
    
    # We also need dropoff_risk from episodes for "acceptable_risk_range"? 
    # Or use 'risk_penalty' from ranking which is derived from it.
    # risk_penalty is title-level. unique per title.
    
    # Aggregations
    # 1. Episode Level Aggregates (Mean & Median)
    episode_agg = df_ep.groupby('title').agg({
        'pacing_score': 'mean',
        'cliffhanger_score': 'mean',
        'emotional_intensity': 'mean',
        'likes': 'mean' # proxy for engagement
    }).reset_index()

    # 2. Comment Level Aggregates
    comment_agg = df_cm.groupby('title').agg({
        'addiction_score': 'mean',
        'theory_crafting_score': 'mean'
    }).reset_index()

    # Merge
    df_merged = pd.merge(episode_agg, comment_agg, on='title', how='left')
    df_merged = pd.merge(df_merged, df_titles[['title', 'genre']], on='title', how='left')
    
    # Fill N/A with 0 (safe default)
    df_merged = df_merged.fillna(0)
    
    # 3. Create Genre Profiles with Quartiles
    genre_profiles = []
    
    for genre in df_merged['genre'].unique():
        if not isinstance(genre, str): continue
        
        subset = df_merged[df_merged['genre'] == genre]
        count = len(subset)
        
        # Confidence Logic
        if count >= 15: confidence = "High"
        elif count >= 5: confidence = "Medium"
        else: confidence = "Low"
        
        profile = {
            'genre': genre,
            'title_count': count,
            'confidence_level': confidence,
            
            # Medians (Robust Central Tendency)
            'median_pacing': round(subset['pacing_score'].median(), 2),
            'median_cliffhanger_density': round(subset['cliffhanger_score'].median(), 2),
            'median_emotional_intensity': round(subset['emotional_intensity'].median(), 2),
            'median_addiction_language': round(subset['addiction_score'].median(), 2),
            
            # Quartiles (Spread)
            'pacing_q1': round(subset['pacing_score'].quantile(0.25), 2),
            'pacing_q3': round(subset['pacing_score'].quantile(0.75), 2),
            'emotion_q1': round(subset['emotional_intensity'].quantile(0.25), 2),
            'emotion_q3': round(subset['emotional_intensity'].quantile(0.75), 2)
        }
        genre_profiles.append(profile)
        
    # Save
    df_profiles = pd.DataFrame(genre_profiles)
    df_profiles.to_csv("data/processed/genre_profiles.csv", index=False)
    print(f"✅ Generated profiles for {len(genre_profiles)} genres.")
    print(df_profiles[['genre', 'title_count', 'confidence_level']])
    print(f"\nSaved to data/processed/genre_profiles.csv")

if __name__ == "__main__":
    main()
