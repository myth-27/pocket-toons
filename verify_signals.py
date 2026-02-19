import pandas as pd
import sys

# Force pure ASCII and no special chars
def clean_print(text, f):
    f.write(str(text) + "\n")

with open('validation_results.txt', 'w', encoding='utf-8') as f:
    try:
        df_ep = pd.read_csv('data/processed/comment_signals_episode.csv')
        f.write("TOP_5_EPISODES_ADDICTION\n")
        top_ep = df_ep.sort_values('addiction_language_score', ascending=False).head(5)
        for _, row in top_ep.iterrows():
            f.write(f"{row['webtoon_title']} | Ep {row['episode_number']} | Score: {row['addiction_language_score']}\n")
    except Exception as e:
        f.write(f"Error reading episodes: {e}\n")

    f.write("\n")

    try:
        df_title = pd.read_csv('data/processed/comment_signals_title.csv')
        f.write("TOP_5_TITLES_EMOTIONAL\n")
        top_title = df_title.sort_values('avg_emotional_intensity', ascending=False).head(5)
        for _, row in top_title.iterrows():
            f.write(f"{row['webtoon_title']} | Score: {row['avg_emotional_intensity']}\n")
    except Exception as e:
        f.write(f"Error reading titles: {e}\n")
