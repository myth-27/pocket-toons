import pandas as pd
import numpy as np
import random
from pathlib import Path

def generate_synthetic_data():
    """
    Generates synthetic episode and comment signals based on titles in webtoon_titles.csv.
    Scales signals based on genre baselines to create distinct profiles.
    """
    
    # Load Titles
    titles_path = Path("data/external/webtoon_titles.csv")
    if titles_path.exists():
        df_titles = pd.read_csv(titles_path)
    else:
        # Fallback if CSV missing
        print("Warning: webtoon_titles.csv not found. Using dummy data.")
        df_titles = pd.DataFrame({"title": ["Test Toon"], "genre": ["Action"], "episodes": [10], "likes_base": [1000]})

    print(f"Generating data for {len(df_titles)} titles...")

    # Data Containers
    episode_data = []
    comment_data = []

    # Genre Baselines (Mean, Std Dev) for signals
    genre_baselines = {
        "Action": {
            "pacing": (0.7, 0.1), "cliffhanger": (0.8, 0.15), "emotion": (0.5, 0.1), 
            "addiction": (0.85, 0.1), "drop_off_rate": (0.05, 0.02)
        },
        "Fantasy": {
            "pacing": (0.6, 0.15), "cliffhanger": (0.75, 0.1), "emotion": (0.6, 0.15), 
            "addiction": (0.8, 0.1), "drop_off_rate": (0.04, 0.02)
        },
        "Romance": {
            "pacing": (0.4, 0.1), "cliffhanger": (0.6, 0.1), "emotion": (0.9, 0.1), 
            "addiction": (0.75, 0.15), "drop_off_rate": (0.03, 0.01)
        },
        "Drama": {
            "pacing": (0.5, 0.1), "cliffhanger": (0.65, 0.15), "emotion": (0.85, 0.1), 
            "addiction": (0.7, 0.1), "drop_off_rate": (0.06, 0.03)
        },
        "Thriller": {
            "pacing": (0.65, 0.1), "cliffhanger": (0.9, 0.05), "emotion": (0.7, 0.15),
            "addiction": (0.9, 0.05), "drop_off_rate": (0.02, 0.01)
        },
        "Sci-fi": {
            "pacing": (0.6, 0.15), "cliffhanger": (0.7, 0.15), "emotion": (0.5, 0.15),
            "addiction": (0.75, 0.15), "drop_off_rate": (0.07, 0.03)
        },
        "Horror": {
            "pacing": (0.45, 0.1), "cliffhanger": (0.85, 0.1), "emotion": (0.75, 0.2), 
            "addiction": (0.8, 0.1), "drop_off_rate": (0.08, 0.04)
        },
        "Slice of Life": {
            "pacing": (0.3, 0.05), "cliffhanger": (0.2, 0.1), "emotion": (0.6, 0.2), 
            "addiction": (0.65, 0.2), "drop_off_rate": (0.02, 0.01)
        },
        "Mystery": {
            "pacing": (0.55, 0.1), "cliffhanger": (0.95, 0.03), "emotion": (0.65, 0.1), 
            "addiction": (0.9, 0.05), "drop_off_rate": (0.03, 0.01)
        },
        "Superhero": {
            "pacing": (0.75, 0.1), "cliffhanger": (0.7, 0.1), "emotion": (0.55, 0.1), 
            "addiction": (0.8, 0.1), "drop_off_rate": (0.05, 0.02)
        },
        "Sports": {
            "pacing": (0.8, 0.1), "cliffhanger": (0.6, 0.15), "emotion": (0.7, 0.1), 
            "addiction": (0.85, 0.1), "drop_off_rate": (0.04, 0.02)
        }
    }

    for _, row in df_titles.iterrows():
        title = row['title']
        genre = row.get('genre', 'Action').strip().capitalize() # Ensure format
        if genre not in genre_baselines: genre = "Action"
        
        base_likes = row.get('avg_likes', 10000)
        
        # Get baselines for this genre
        base = genre_baselines.get(genre, genre_baselines['Action'])

        # Generate ~20 episodes per title
        for ep_num in range(1, 21):
            
            # 1. Episode Signals
            pacing = np.clip(np.random.normal(base["pacing"][0], base["pacing"][1]), 0.1, 1.0)
            cliffhanger = np.clip(np.random.normal(base["cliffhanger"][0], base["cliffhanger"][1]), 0, 1.0)
            emotion = np.clip(np.random.normal(base["emotion"][0], base["emotion"][1]), 0, 1.0)
            
            # Engagement Proxy
            drop_off = np.random.normal(base["drop_off_rate"][0], base["drop_off_rate"][1])
            engagement = int(base_likes * ((1 - drop_off) ** ep_num))
            if cliffhanger > 0.8:
                engagement = int(engagement * 1.05) # Boost
                
            episode_data.append({
                "title": title,
                "episode": ep_num,
                "likes": engagement,
                "panel_count": random.randint(40, 80),
                "pacing_score": round(pacing, 2),
                "cliffhanger_score": round(cliffhanger, 2),
                "emotional_intensity": round(emotion, 2)
            })

            # 2. Comment Signals
            addiction = np.clip(np.random.normal(base["addiction"][0], base["addiction"][1]), 0, 1.0)
            
            comment_data.append({
                "title": title,
                "episode": ep_num,
                "comment_count": int(engagement * 0.05),
                "positive_sentiment": round(random.uniform(0.7, 0.95), 2),
                "addiction_score": round(addiction, 2),
                "theory_crafting_score": round(random.uniform(0.1, 0.6), 2)
            })

    # Save to CSV
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    registry_file = Path("data/registry/content_registry.csv")
    df_reg = pd.read_csv(registry_file)
    title_to_cid = {row['canonical_title']: row['content_id'] for _, row in df_reg.iterrows()}

    # 1. Episode Signals
    df_ep = pd.DataFrame(episode_data)
    df_ep.to_csv("data/processed/episode_signals.csv", index=False)
    
    # 2. Comment Signals (Title Level)
    df_cm = pd.DataFrame(comment_data)
    df_cm_title = df_cm.groupby('title').agg(
        avg_emotional_intensity=('positive_sentiment', 'mean'),
        avg_addiction_language=('addiction_score', 'mean')
    ).reset_index()
    df_cm_title.rename(columns={'title': 'webtoon_title'}, inplace=True)
    df_cm_title.to_csv("data/processed/comment_signals_title.csv", index=False)
    
    # 3. YouTube Signals
    yt_signals = []
    for title, cid in title_to_cid.items():
        yt_signals.append({
            "content_id": cid,
            "youtube_hype_score": round(random.uniform(0.3, 0.9), 2),
            "youtube_confusion_score": round(random.uniform(0.05, 0.3), 2)
        })
    pd.DataFrame(yt_signals).to_csv("data/processed/youtube_signals.csv", index=False)

    # 4. Reddit Risks
    rd_signals = []
    for title, cid in title_to_cid.items():
        num_risks = random.randint(1, 4)
        for _ in range(num_risks):
            rd_signals.append({
                "content_id": cid,
                "severity": round(random.uniform(1.0, 5.0), 1),
                "risk_type": random.choice(["Pacing", "Character Fatigue", "Plot Hole", "Art Quality"])
            })
    pd.DataFrame(rd_signals).to_csv("data/processed/reddit_risks.csv", index=False)

    # 5. Transcript Signals (compatibility)
    df_tr = df_ep.copy()
    df_tr['external_emotion_score'] = df_tr['emotional_intensity']
    df_tr.to_csv("data/processed/transcript_signals.csv", index=False)

    print(f"DONE: Generated enriched signals for {len(df_titles)} titles.")

if __name__ == "__main__":
    generate_synthetic_data()
