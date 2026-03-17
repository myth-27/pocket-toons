import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- STEP 5: UNIFIED CONTENT INTELLIGENCE TABLE ---

def merge_intelligence():
    # File Paths
    registry_file = Path('data/registry/content_registry.csv')
    webtoon_ep_file = Path('data/processed/episode_signals.csv')
    webtoon_cm_file = Path('data/processed/comment_signals_title.csv')
    youtube_file = Path('data/processed/youtube_signals.csv')
    reddit_file = Path('data/processed/reddit_risks.csv')
    output_file = Path('data/unified/content_intelligence.csv')
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Registry as base
    try:
        df_registry = pd.read_csv(registry_file)
    except FileNotFoundError:
        logger.error("Registry not found.")
        return
        
    df_unified = df_registry[['content_id', 'canonical_title', 'genre']].copy()
    
    # helper: map title to content_id
    title_to_cid = {row['canonical_title']: row['content_id'] for _, row in df_registry.iterrows()}
    
    # 2. Load and Map Webtoon Episode Signals
    if webtoon_ep_file.exists():
        df_ep = pd.read_csv(webtoon_ep_file)
        df_ep_title = df_ep.groupby('title').agg(
            webtoon_cliffhanger_rate=('cliffhanger_score', 'mean')
        ).reset_index()
        df_ep_title['content_id'] = df_ep_title['title'].map(title_to_cid)
        df_ep_title = df_ep_title.dropna(subset=['content_id'])
        df_unified = pd.merge(df_unified, df_ep_title[['content_id', 'webtoon_cliffhanger_rate']], on='content_id', how='left')
    else:
        df_unified['webtoon_cliffhanger_rate'] = 0.0

    # 3. Load and Map Webtoon Comment Signals
    if webtoon_cm_file.exists():
        df_cm = pd.read_csv(webtoon_cm_file)
        df_cm['content_id'] = df_cm['webtoon_title'].map(title_to_cid)
        df_cm = df_cm.dropna(subset=['content_id'])
        
        df_cm.rename(columns={
            'avg_emotional_intensity': 'webtoon_emotion_score',
            'avg_addiction_language': 'webtoon_addiction_score'
        }, inplace=True)
        
        df_unified = pd.merge(df_unified, df_cm[['content_id', 'webtoon_emotion_score', 'webtoon_addiction_score']], on='content_id', how='left')
    else:
        df_unified['webtoon_emotion_score'] = 0.0
        df_unified['webtoon_addiction_score'] = 0.0

    # 4. Load YouTube Signals
    if youtube_file.exists():
        df_yt = pd.read_csv(youtube_file)
        # Rename for clarity as per spec
        if 'hype_level' in df_yt.columns:
            df_yt.rename(columns={'hype_level': 'youtube_hype_score'}, inplace=True)
        if 'confusion_mentions' in df_yt.columns:
            df_yt.rename(columns={'confusion_mentions': 'youtube_confusion_score'}, inplace=True)
            
        df_unified = pd.merge(df_unified, df_yt[['content_id', 'youtube_hype_score', 'youtube_confusion_score']], on='content_id', how='left')
    else:
        df_unified['youtube_hype_score'] = 0.0
        df_unified['youtube_confusion_score'] = 0.0

    # 5. Load Reddit Risks
    if reddit_file.exists():
        df_rd = pd.read_csv(reddit_file)
        df_rd_agg = df_rd.groupby('content_id').agg(
            reddit_risk_score=('severity', 'sum')
        ).reset_index()
        df_unified = pd.merge(df_unified, df_rd_agg, on='content_id', how='left')
    else:
        df_unified['reddit_risk_score'] = 0.0
        
    # 6. Calculate Data Coverage Confidence
    def calc_confidence(row):
        sources = 0
        if row['webtoon_emotion_score'] > 0: sources += 1
        if row['youtube_hype_score'] > 0: sources += 1
        sources += 1 
        
        if sources == 3: return "High"
        elif sources == 2: return "Medium"
        else: return "Low"
        
    df_unified = df_unified.fillna(0.0)
    df_unified['data_confidence'] = df_unified.apply(calc_confidence, axis=1)

    final_cols = [
        'content_id', 'genre', 
        'webtoon_emotion_score', 'webtoon_addiction_score', 'webtoon_cliffhanger_rate',
        'youtube_hype_score', 'youtube_confusion_score', 
        'reddit_risk_score', 'data_confidence'
    ]
    
    for col in final_cols:
        if col not in df_unified.columns:
            df_unified[col] = 0.0
            
    df_final = df_unified[final_cols]
    df_final.to_csv(output_file, index=False)
    logger.info(f"DONE: Generated Unified Intelligence Table: {output_file} with {len(df_final)} entries.")

if __name__ == "__main__":
    merge_intelligence()
