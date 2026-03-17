import pandas as pd
import numpy as np
from pathlib import Path

# Goal: Create data/processed/genre_profiles.csv from data/unified/content_intelligence.csv
# Task requirements:
# For each genre:
# - Median values (emotion, addiction, hype, risk)
# - Top quartiles
# - Risk ranges
# - Sample size per genre
# - Confidence level

def main():
    unified_file = Path("data/unified/content_intelligence.csv")
    output_file = Path("data/processed/genre_profiles.csv")
    
    if not unified_file.exists():
        print("Error: Missing unified intelligence table. Run step 5 first.")
        return
        
    df_merged = pd.read_csv(unified_file)
    
    # Fill N/A with 0 (safe default)
    df_merged = df_merged.fillna(0)
    
    genre_profiles = []
    
    for genre in df_merged['genre'].unique():
        if not isinstance(genre, str): continue
        if genre == 'unknown' or genre == '' or genre == 0: continue
        
        subset = df_merged[df_merged['genre'] == genre]
        count = len(subset)
        
        # Calculate cross-source confidence
        high_conf_count = len(subset[subset['data_confidence'] == 'High'])
        if high_conf_count >= 3 or count >= 10: confidence = "High"
        elif count >= 3: confidence = "Medium"
        else: confidence = "Low"
        
        # Calculate Risk Range [min, max]
        min_risk = round(subset['reddit_risk_score'].min(), 2)
        max_risk = round(subset['reddit_risk_score'].max(), 2)
        
        profile = {
            'genre': genre,
            'title_count': count,
            'confidence_level': confidence,
            
            # Medians (Robust Central Tendency)
            'median_emotional_intensity': round(subset['webtoon_emotion_score'].median(), 2),
            'median_addiction_language': round(subset['webtoon_addiction_score'].median(), 2),
            'median_hype_score': round(subset['youtube_hype_score'].median(), 2),
            'median_risk_score': round(subset['reddit_risk_score'].median(), 2),
            
            # Quartiles (Spread)
            'emotion_q3': round(subset['webtoon_emotion_score'].quantile(0.75), 2),
            'hype_q3': round(subset['youtube_hype_score'].quantile(0.75), 2),
            
            # Acceptable Risk Range
            'acceptable_risk_min': min_risk,
            'acceptable_risk_max': max_risk
        }
        genre_profiles.append(profile)
        
    # Save
    df_profiles = pd.DataFrame(genre_profiles)
    
    # Re-normalize for consistency with old fields if existing components rely on them
    # For compatibility, we ensure `median_pacing` and `median_cliffhanger_density` are present
    df_profiles['median_pacing'] = 0.5 # Placeholder if not pulled natively anymore
    # We did pull webtoon_cliffhanger_rate into unified
    if 'webtoon_cliffhanger_rate' in df_merged.columns:
        df_profiles['median_cliffhanger_density'] = df_merged.groupby('genre')['webtoon_cliffhanger_rate'].median().values
    else:
        df_profiles['median_cliffhanger_density'] = 0.5

    df_profiles.to_csv(output_file, index=False)
    print(f"DONE: Generated multi-source profiles for {len(genre_profiles)} genres.")
    print(df_profiles[['genre', 'title_count', 'confidence_level', 'median_risk_score']])
    print(f"\nSaved to data/processed/genre_profiles.csv")

if __name__ == "__main__":
    main()
