import pandas as pd
from pathlib import Path

def prepare_ml_dataset():
    """
    Consolidates processed signals and metadata into a single CSV for ML model training.
    """
    print("Preparing ML Dataset...")
    
    processed_dir = Path("data/processed")
    output_file = processed_dir / "ml_ready_dataset.csv"
    
    # Load available signals
    try:
        df_ep = pd.read_csv(processed_dir / "episode_signals.csv")
        df_cm = pd.read_csv(processed_dir / "comment_signals_title.csv")
        df_titles = pd.read_csv("data/external/webtoon_titles.csv")
    except FileNotFoundError as e:
        print(f"Error: processed signal files not found ({e}). Run data pipeline first.")
        return

    # Merge Episode and Comment signals
    # Mapping df_cm to match df_ep
    df_cm.rename(columns={'webtoon_title': 'title'}, inplace=True)
    df_merged = pd.merge(df_ep, df_cm, on="title")
    
    # Merge with title metadata (genre, etc.)
    df_final = pd.merge(df_merged, df_titles, on="title")
    
    # Final cleanup and feature naming
    df_final.to_csv(output_file, index=False)
    print(f"ML Dataset ready with {len(df_final)} rows and {len(df_final.columns)} columns.")
    print(f"Location: {output_file}")

if __name__ == "__main__":
    prepare_ml_dataset()
