import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('greenlight_scoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION: Genre Mapping & Scoring Weights ---

GENRE_MAP = {
    "Tower of God": "fantasy",
    "Solo Leveling": "action",
    "Lookism": "drama",
    "True Beauty": "romance",
    "Omniscient Reader": "fantasy"
}

# A. Core Behavior Score Weights
W_HOOK = 0.4
W_RETENTION = 0.3
W_LIKES = 0.3

# B. Emotion Score Weights
W_EMOTION_INTENSITY = 0.4
W_ADDICTION = 0.4
W_CLIFFHANGER = 0.2

# C. Risk Penalty
RISK_RANGE_MAX = 0.3

# D. External Buzz
BUZZ_MULTIPLIER_BASE = 1.0
BUZZ_MULTIPLIER_FACTOR = 0.1
BUZZ_CAP_MIN = 0.9
BUZZ_CAP_MAX = 1.2

def normalize_series(series):
    """Min-Max normalization to 0-1 range. Handles single-value case by returning 0.5."""
    if series.empty:
        return series
    if len(series) == 1:
        return pd.Series([0.5], index=series.index)
        
    min_val = series.min()
    max_val = series.max()
    
    if max_val == min_val:
        return series.apply(lambda x: 0.5) 
    return (series - min_val) / (max_val - min_val)

def normalize_within_genre(df, score_col, genre_col='genre'):
    """Normalizes a score column within each genre group."""
    # Group by genre and apply normalization
    # If a genre has only 1 title, it gets 0.5 (neutral)
    return df.groupby(genre_col)[score_col].transform(normalize_series)

def main():
    # Input files
    file_episode_signals = Path("data/processed/episode_signals.csv")
    file_comment_signals = Path("data/processed/comment_signals_title.csv")
    file_transcript_signals = Path("data/processed/transcript_signals.csv")
    output_ranking_file = Path("data/processed/greenlight_ranking.csv")
    
    # 1. Load Data
    logger.info("Loading signal datasets...")
    
    try:
        df_ep = pd.read_csv(file_episode_signals)
        df_comments = pd.read_csv(file_comment_signals)
        if file_transcript_signals.exists():
            df_transcripts = pd.read_csv(file_transcript_signals)
        else:
            df_transcripts = pd.DataFrame(columns=['webtoon_title', 'external_buzz_volume'])
            logger.warning("Transcript signals missing. Defaulting buzz multiplier to 1.0.")
    except Exception as e:
        logger.error(f"Error loading files: {e}")
        return

    # 2. Feature Preparation (TITLE-LEVEL)
    
    # A. Core Behavior Score Components
    title_behavior = df_ep.groupby('webtoon_title').agg(
        mean_hook=('hook_score', 'mean'),
        mean_retention=('retention_slope', 'mean'),
        mean_log_likes=('log_likes', 'mean'),
        episode_count=('episode_number', 'count')
    ).reset_index()

    # Risk Penalty
    risk_agg = df_ep.groupby('webtoon_title')['dropoff_risk'].mean().reset_index()
    risk_agg.rename(columns={'dropoff_risk': 'risk_proportion'}, inplace=True)
    
    # Merge behavior and risk
    df_main = pd.merge(title_behavior, risk_agg, on='webtoon_title', how='left')
    
    # Merge with Comment Signals
    df_main = pd.merge(df_main, df_comments, on='webtoon_title', how='left')
    
    # Merge with External Buzz
    if not df_transcripts.empty:
        df_main = pd.merge(df_main, df_transcripts[['webtoon_title', 'external_buzz_volume']], on='webtoon_title', how='left')
    else:
        df_main['external_buzz_volume'] = 0
    df_main['external_buzz_volume'] = df_main['external_buzz_volume'].fillna(0)
    
    # Assign Genre
    df_main['genre'] = df_main['webtoon_title'].map(GENRE_MAP).fillna('unknown')

    # Handle missing values
    score_cols = ['mean_hook', 'mean_retention', 'mean_log_likes', 
                  'avg_emotional_intensity', 'avg_addiction_language', 'avg_cliffhanger_score']
    for col in score_cols:
        if col in df_main.columns:
            df_main[col] = df_main[col].fillna(0)

    # Create GLOBAL normalized features for Absolute Quality Score
    # (Independent of Genre)
    df_main['global_norm_hook'] = normalize_series(df_main['mean_hook'])
    df_main['global_norm_retention'] = normalize_series(df_main['mean_retention'])
    df_main['global_norm_log_likes'] = normalize_series(df_main['mean_log_likes'])
    
    df_main['abs_behavior_score'] = (
        W_HOOK * df_main['global_norm_hook'] +
        W_RETENTION * df_main['global_norm_retention'] +
        W_LIKES * df_main['global_norm_log_likes']
    )
    
    df_main['global_norm_emotion'] = normalize_series(df_main['avg_emotional_intensity'])
    df_main['global_norm_addiction'] = normalize_series(df_main['avg_addiction_language'])
    df_main['global_norm_cliffhanger'] = normalize_series(df_main['avg_cliffhanger_score'])
    
    df_main['abs_emotion_score'] = (
        W_EMOTION_INTENSITY * df_main['global_norm_emotion'] +
        W_ADDICTION * df_main['global_norm_addiction'] +
        W_CLIFFHANGER * df_main['global_norm_cliffhanger']
    )
    
    # Absolute Quality Score (0-100)
    # Formula: 0.5 * behavior + 0.5 * emotion
    # Normalize globally 0-100
    df_main['abs_quality_raw'] = 0.5 * df_main['abs_behavior_score'] + 0.5 * df_main['abs_emotion_score']
    df_main['absolute_quality_score'] = normalize_series(df_main['abs_quality_raw']) * 100
    df_main['absolute_quality_score'] = df_main['absolute_quality_score'].round(2)

    # --- RELATIVE PRIORITY SCORING (GENRE AWARE) ---

    # A. Calculate Behavior Score (Normalized WITHIN GENRE)
    # Normalize components within genre
    df_main['norm_hook'] = normalize_within_genre(df_main, 'mean_hook')
    df_main['norm_retention'] = normalize_within_genre(df_main, 'mean_retention')
    df_main['norm_log_likes'] = normalize_within_genre(df_main, 'mean_log_likes')
    
    df_main['behavior_score_raw'] = (
        W_HOOK * df_main['norm_hook'] +
        W_RETENTION * df_main['norm_retention'] +
        W_LIKES * df_main['norm_log_likes']
    )
    # Re-normalize final behavior score within genre to 0-1
    df_main['behavior_score'] = normalize_within_genre(df_main, 'behavior_score_raw')

    # B. Calculate Emotion & Fandom Score (Normalized WITHIN GENRE)
    df_main['norm_emotion'] = normalize_within_genre(df_main, 'avg_emotional_intensity')
    df_main['norm_addiction'] = normalize_within_genre(df_main, 'avg_addiction_language')
    df_main['norm_cliffhanger'] = normalize_within_genre(df_main, 'avg_cliffhanger_score')
    
    df_main['emotion_score_raw'] = (
        W_EMOTION_INTENSITY * df_main['norm_emotion'] +
        W_ADDICTION * df_main['norm_addiction'] +
        W_CLIFFHANGER * df_main['norm_cliffhanger']
    )
    df_main['emotion_score'] = normalize_within_genre(df_main, 'emotion_score_raw')

    # C. Risk Penalty (Applied WITHIN GENRE)
    df_main['norm_risk'] = normalize_within_genre(df_main, 'risk_proportion')
    df_main['risk_penalty'] = df_main['norm_risk'] * RISK_RANGE_MAX

    # D. External Buzz Multiplier (GLOBAL)
    df_main['buzz_log'] = np.log1p(df_main['external_buzz_volume'])
    df_main['buzz_multiplier'] = BUZZ_MULTIPLIER_BASE + (BUZZ_MULTIPLIER_FACTOR * df_main['buzz_log'])
    df_main['buzz_multiplier'] = df_main['buzz_multiplier'].clip(lower=BUZZ_CAP_MIN, upper=BUZZ_CAP_MAX)

    # 3. FINAL RELATIVE PRIORITY SCORE (Previously Greenlight Score)
    
    df_main['calc_score'] = (
        (df_main['behavior_score'] * df_main['emotion_score']) * 
        df_main['buzz_multiplier']
    ) - df_main['risk_penalty']
    
    # Normalize to 0-100 GLOBAL for final readability
    df_main['relative_priority_score'] = normalize_series(df_main['calc_score']) * 100
    
    # Rounding
    df_main['relative_priority_score'] = df_main['relative_priority_score'].round(2)
    df_main['behavior_score'] = df_main['behavior_score'].round(4)
    df_main['emotion_score'] = df_main['emotion_score'].round(4)
    df_main['risk_penalty'] = df_main['risk_penalty'].round(4)
    df_main['buzz_multiplier'] = df_main['buzz_multiplier'].round(4)

    # Decision Labels
    def get_decision(row):
        abs_q = row['absolute_quality_score']
        rel_p = row['relative_priority_score']
        
        if abs_q >= 70 and rel_p >= 50:
            return "GREENLIGHT"
        elif abs_q >= 70 and rel_p < 50:
            return "GREENLIGHT / MONITOR"
        elif abs_q < 70 and rel_p >= 50:
            return "RISKY BET"
        else:
            return "DO NOT GREENLIGHT"
            
    df_main['decision_label'] = df_main.apply(get_decision, axis=1)

    # Ranks
    # genre_rank based on RELATIVE priority
    df_main['genre_rank'] = df_main.groupby('genre')['relative_priority_score'].rank(ascending=False, method='min')
    # overall_rank
    df_main['overall_rank'] = df_main['relative_priority_score'].rank(ascending=False, method='min')

    # 4. Save Output
    output_cols = [
        'webtoon_title',
        'genre',
        'absolute_quality_score',
        'relative_priority_score', # Renamed from greenlight_score
        'decision_label',
        'behavior_score',
        'emotion_score',
        'risk_penalty',
        'buzz_multiplier',
        'genre_rank',
        'overall_rank'
    ]
    
    df_main = df_main.sort_values(['genre', 'genre_rank'])
    
    logger.info(f"Saving ranking results to {output_ranking_file}...")
    df_main[output_cols].to_csv(output_ranking_file, index=False)

    # 5. DIAGNOSTIC INSIGHTS
    print("\n=== DIAGNOSTIC INSIGHTS ===")
    with open('genre_diagnostics.txt', 'w', encoding='utf-8') as f:
        f.write("=== DIAGNOSTIC INSIGHTS ===\n")
        
        # Validation Output (Top 5 Qual vs Priority)
        print("\n--- Top 5 by Absolute Quality ---")
        f.write("\n--- Top 5 by Absolute Quality ---\n")
        top_qual = df_main.sort_values('absolute_quality_score', ascending=False).head(5)
        for _, row in top_qual.iterrows():
            line = f"{row['webtoon_title']} | Qual: {row['absolute_quality_score']} | Prio: {row['relative_priority_score']} | {row['decision_label']}"
            print(line)
            f.write(line + "\n")
            
        print("\n--- Top 5 by Relative Priority ---")
        f.write("\n--- Top 5 by Relative Priority ---\n")
        top_prio = df_main.sort_values('relative_priority_score', ascending=False).head(5)
        for _, row in top_prio.iterrows():
            line = f"{row['webtoon_title']} | Prio: {row['relative_priority_score']} | Qual: {row['absolute_quality_score']} | {row['decision_label']}"
            print(line)
            f.write(line + "\n")
            
        # Deprioritized Strong Titles
        print("\n--- Strong Titles Deprioritized (Qual >= 70, Prio < 30) ---")
        f.write("\n--- Strong Titles Deprioritized (Qual >= 70, Prio < 30) ---\n")
        deprio = df_main[(df_main['absolute_quality_score'] >= 70) & (df_main['relative_priority_score'] < 30)]
        if not deprio.empty:
            for _, row in deprio.iterrows():
                line = f"{row['webtoon_title']} | Qual: {row['absolute_quality_score']} | Prio: {row['relative_priority_score']} -> Strong title deprioritized due to competition."
                print(line)
                f.write(line + "\n")
        else:
            print("None.")
            f.write("None.\n")
        
        # A. Top 2 titles per genre (Revised Explanation)
        print("\n--- Top Titles per Genre ---")
        f.write("\n--- Top Titles per Genre ---\n")
        for genre, group in df_main.groupby('genre'):
            print(f"\nGenre: {genre.upper()}")
            f.write(f"\nGenre: {genre.upper()}\n")
            top_2 = group.sort_values('relative_priority_score', ascending=False).head(2)
            for _, row in top_2.iterrows():
                # Explanation logic
                parts = []
                if row['absolute_quality_score'] > 70: parts.append("High absolute quality")
                elif row['absolute_quality_score'] > 40: parts.append("Moderate quality")
                else: parts.append("Low quality")
                
                if row['relative_priority_score'] > 70: parts.append("high relative priority")
                elif row['relative_priority_score'] > 40: parts.append("moderate priority")
                else: parts.append("low priority")
                
                # Context
                if row['genre_rank'] == 1: parts.append(f"top in {genre}")
                else: parts.append(f"peer competition in {genre}")
                
                reason_str = ", ".join(parts) + "."
                line = f"#{int(row['genre_rank'])} {row['webtoon_title']} (Prio: {row['relative_priority_score']}): {reason_str}"
                print(line)
                f.write(line + "\n")

if __name__ == "__main__":
    main()
