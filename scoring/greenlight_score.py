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
    unified_file = Path("data/unified/content_intelligence.csv")
    output_ranking_file = Path("data/processed/greenlight_ranking.csv")
    
    # 1. Load Data
    logger.info("Loading unified signal dataset...")
    
    try:
        df_unified = pd.read_csv(unified_file)
    except Exception as e:
        logger.error(f"Error loading {unified_file}: {e}")
        return

    # 2. Feature Preparation (TITLE-LEVEL)
    df_main = df_unified.copy()
    
    # Use content_id instead of webtoon_title moving forward
    # Re-map legacy 'webtoon_title' for output compatibility since it's expected
    registry_file = Path("data/registry/content_registry.csv")
    if registry_file.exists():
        df_reg = pd.read_csv(registry_file)
        cid_to_title = {row['content_id']: row['canonical_title'] for _, row in df_reg.iterrows()}
        df_main['webtoon_title'] = df_main['content_id'].map(cid_to_title)
    else:
        df_main['webtoon_title'] = df_main['content_id']

    # Create Normalized Features
    df_main['global_norm_emotion'] = normalize_series(df_main['webtoon_emotion_score'])
    df_main['global_norm_addiction'] = normalize_series(df_main['webtoon_addiction_score'])
    df_main['global_norm_cliffhanger'] = normalize_series(df_main['webtoon_cliffhanger_rate'])

    # Absolute Quality (Narrative Strength from Webtoon)
    df_main['abs_emotion_score'] = (
        W_EMOTION_INTENSITY * df_main['global_norm_emotion'] +
        W_ADDICTION * df_main['global_norm_addiction'] +
        W_CLIFFHANGER * df_main['global_norm_cliffhanger']
    )
    df_main['absolute_quality_score'] = normalize_series(df_main['abs_emotion_score']) * 100
    df_main['absolute_quality_score'] = df_main['absolute_quality_score'].round(2)

    # --- RELATIVE PRIORITY SCORING (GENRE AWARE) ---
    
    # Normalize Narrative Strength within genre
    df_main['norm_emotion'] = normalize_within_genre(df_main, 'webtoon_emotion_score')
    df_main['norm_addiction'] = normalize_within_genre(df_main, 'webtoon_addiction_score')
    df_main['norm_cliffhanger'] = normalize_within_genre(df_main, 'webtoon_cliffhanger_rate')
    
    df_main['emotion_score_raw'] = (
        W_EMOTION_INTENSITY * df_main['norm_emotion'] +
        W_ADDICTION * df_main['norm_addiction'] +
        W_CLIFFHANGER * df_main['norm_cliffhanger']
    )
    df_main['behavior_score'] = 1.0 # Legacy fallback
    df_main['emotion_score'] = normalize_within_genre(df_main, 'emotion_score_raw')

    # D. External Buzz Multiplier (YouTube)
    df_main['buzz_log'] = np.log1p(df_main['youtube_hype_score'])
    df_main['buzz_multiplier'] = BUZZ_MULTIPLIER_BASE + (BUZZ_MULTIPLIER_FACTOR * df_main['buzz_log'])
    df_main['buzz_multiplier'] = df_main['buzz_multiplier'].clip(lower=BUZZ_CAP_MIN, upper=BUZZ_CAP_MAX)

    # --- LAYER 1: HARD GATES ---
    def evaluate_gates(row):
        failed_gates = []
        # Hook Gate: Cliffhanger rate extremely low (bottom 15% globally or absolute < 0.1)
        if row['webtoon_cliffhanger_rate'] < 0.1 or row['global_norm_cliffhanger'] < 0.15:
            failed_gates.append("Hook Gate (Weak tension)")
            
        # Clarity Gate: High confusion on YouTube or Reddit
        if row.get('youtube_confusion_score', 0) > 0.7:
            failed_gates.append("Clarity Gate (High YouTube Confusion)")
            
        if len(failed_gates) == 0:
            return "Passed"
        return " | ".join(failed_gates)
        
    df_main['failed_gates'] = df_main.apply(evaluate_gates, axis=1)

    # --- LAYER 2: QUALITY BANDS ---
    # Convert numerical scores to High/Medium/Low bands within genres
    def get_band(val):
        if pd.isna(val): return "MEDIUM"
        if val >= 0.75: return "HIGH"
        if val <= 0.25: return "LOW"
        return "MEDIUM"
        
    df_main['Emotion_Band'] = df_main['norm_emotion'].apply(get_band)
    df_main['Addiction_Band'] = df_main['norm_addiction'].apply(get_band)
    
    # Risk Band (combines Reddit Risk and YouTube Confusion)
    df_main['norm_risk'] = normalize_within_genre(df_main, 'reddit_risk_score')
    df_main['norm_confusion'] = normalize_within_genre(df_main, 'youtube_confusion_score')
    df_main['combined_risk_norm'] = normalize_series(df_main['norm_risk'] * 0.7 + df_main['norm_confusion'] * 0.3)
    df_main['Risk_Band'] = df_main['combined_risk_norm'].apply(get_band)
    
    # Narrative Structure Band (simplification based on cliffhangers)
    df_main['Structure_Band'] = df_main['norm_cliffhanger'].apply(get_band)

    # --- LAYER 3: DECISION MATRIX ---
    def apply_decision_matrix(row):
        em = row['Emotion_Band']
        ad = row['Addiction_Band']
        risk = row['Risk_Band']
        
        # Overall Quality Heuristic
        if em == "HIGH" and ad == "HIGH":
            overall_q = "HIGH"
        elif em == "LOW" or ad == "LOW":
            overall_q = "LOW"
        else:
            overall_q = "MEDIUM"
            
        # Initial Matrix Decision
        decision = "DEFER"
        if overall_q == "HIGH" and risk == "LOW":
            decision = "GREENLIGHT"
        elif overall_q == "HIGH" and risk == "MEDIUM":
            decision = "PILOT"
        elif overall_q == "MEDIUM" and risk == "LOW":
            decision = "PILOT"
        elif overall_q == "MEDIUM" and risk == "MEDIUM":
            decision = "DEFER"
        elif risk == "HIGH" or overall_q == "LOW":
            decision = "REWORK"
            
        # Gate Enforcement
        if row['failed_gates'] != "Passed":
            if decision in ["GREENLIGHT", "PILOT"]:
                decision = "DEFER"
                
        reasoning = f"Quality: {overall_q} (Emotion: {em}, Addiction: {ad}) | Risk: {risk}"
        if row['failed_gates'] != "Passed":
            reasoning += f" | DOWNGRADED: Failed {row['failed_gates']}"
            
        return pd.Series([decision, reasoning])

    df_main[['decision_label', 'explicit_reasoning']] = df_main.apply(apply_decision_matrix, axis=1)

    # Legacy numeric score for internal sorting / debugging only
    df_main['calc_score'] = (df_main['norm_emotion'] * 0.4 + df_main['norm_addiction'] * 0.4 + df_main['norm_cliffhanger'] * 0.2) - (df_main['combined_risk_norm'] * 0.5)
    df_main['calc_score'] = normalize_within_genre(df_main, 'calc_score') * 100
    df_main['relative_priority_score'] = df_main['calc_score'].round(2)
    
    # Ranks (Using the internal score for tie-breaking)
    df_main['genre_rank'] = df_main.groupby('genre')['relative_priority_score'].rank(ascending=False, method='min')
    df_main['overall_rank'] = df_main['relative_priority_score'].rank(ascending=False, method='min')

    # 4. Save Output
    output_cols = [
        'webtoon_title',
        'genre',
        'decision_label',
        'failed_gates',
        'Emotion_Band',
        'Addiction_Band',
        'Structure_Band',
        'Risk_Band',
        'explicit_reasoning',
        'relative_priority_score', # retained for debug/sorting
    ]
    
    df_main = df_main.sort_values(['genre', 'genre_rank'])
    
    logger.info(f"Saving ranking results to {output_ranking_file}...")
    df_main[output_cols].to_csv(output_ranking_file, index=False)

    # 5. DIAGNOSTIC INSIGHTS
    print("\n=== STRICT DECISION MATRIX INSIGHTS ===")
    print(f"Total Evaluated: {len(df_main)}")
    print(df_main['decision_label'].value_counts())
    
    with open('genre_diagnostics.txt', 'w', encoding='utf-8') as f:
        f.write("=== STRICT DECISION MATRIX INSIGHTS ===\n")
        f.write(f"Total Evaluated: {len(df_main)}\n\n")
        
        counts = df_main['decision_label'].value_counts()
        for label, count in counts.items():
            f.write(f"{label}: {count}\n")
            
        print("\n--- Titles Approved for GREENLIGHT ---")
        f.write("\n--- Titles Approved for GREENLIGHT ---\n")
        greenlights = df_main[df_main['decision_label'] == 'GREENLIGHT']
        if greenlights.empty:
            msg = "None. The threshold is extremely strict."
            print(msg)
            f.write(msg + "\n")
        else:
            for _, row in greenlights.iterrows():
                line = f"{row['webtoon_title']} [{row['genre']}] - {row['explicit_reasoning']}"
                print(line)
                f.write(line + "\n")
                
        print("\n--- Gate Failures ---")
        f.write("\n--- Gate Failures ---\n")
        failures = df_main[df_main['failed_gates'] != 'Passed']
        print(f"Total Gate Failures: {len(failures)}")
        f.write(f"Total Gate Failures: {len(failures)}\n")
        for _, row in failures.head(5).iterrows():
            line = f"{row['webtoon_title']} -> Failed: {row['failed_gates']}"
            print(line)
            f.write(line + "\n")

if __name__ == "__main__":
    main()
