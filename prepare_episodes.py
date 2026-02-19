import json
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_date(date_str):
    """
    Parses date string like "Feb 23, 2025" into "YYYY-MM-DD".
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError as e:
        logger.warning(f"Failed to parse date: {date_str} - {e}")
        return None

def main():
    input_file = Path("data/raw/webtoon_episodes.jsonl")
    output_file = Path("data/processed/episodes_clean.csv")
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Reading raw data from {input_file}...")
    
    data = []
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
    
    if not data:
        logger.warning("No data found in input file.")
        return

    df = pd.DataFrame(data)
    logger.info(f"Loaded {len(df)} raw records.")
    
    # Select and rename columns if necessary (schema matches requirements mostly)
    # Required: webtoon_title, episode_number, episode_title, publish_date, likes, episode_url
    
    # 1. Normalize episode_number
    # Convert to numeric, coercing errors to NaN
    df['episode_number'] = pd.to_numeric(df['episode_number'], errors='coerce')
    # Drop rows where episode_number is NaN if strictly required, or keep them. 
    # Requirement: "Normalize episode_number to int". If it fails, likely bad data.
    # Let's drop invalid episode numbers or log them.
    invalid_eps = df[df['episode_number'].isna()]
    if not invalid_eps.empty:
        logger.warning(f"Dropping {len(invalid_eps)} rows with invalid episode numbers.")
        df = df.dropna(subset=['episode_number'])
    
    df['episode_number'] = df['episode_number'].astype(int)

    # 2. Parse publish_date
    df['publish_date'] = df['publish_date'].apply(parse_date)
    
    # 3. Drop duplicates
    # "Drop duplicates" - usually implies strict exact duplicates or subset.
    # Let's use (series_url, episode_number) as unique identifier if available, or just all columns.
    # The requirement just says "Drop duplicates".
    duplicates_count = df.duplicated().sum()
    logger.info(f"Found {duplicates_count} exact duplicates. Dropping...")
    df = df.drop_duplicates()
    
    # Also check for semantic duplicates? (same series, same episode number)
    # If there are multiple entries for the same episode, we should probably keep the latest or first?
    # Requirement says "Drop duplicates". Let's stick to simple deduplication first.
    # However, 'webtoon_title' and 'episode_number' should likely be unique.
    # Let's check duplicates on subset=['webtoon_title', 'episode_number'] just in case scraper ran twice.
    subset_dupes = df.duplicated(subset=['webtoon_title', 'episode_number']).sum()
    if subset_dupes > 0:
         logger.info(f"Found {subset_dupes} duplicates based on title and episode number. Keeping first.")
         df = df.drop_duplicates(subset=['webtoon_title', 'episode_number'], keep='first')

    # Select final columns
    columns_to_keep = [
        'webtoon_title',
        'episode_number',
        'episode_title',
        'publish_date',
        'likes',
        'episode_url'
    ]
    
    # Ensure all columns exist
    for col in columns_to_keep:
        if col not in df.columns:
            df[col] = None # Fill missing columns with None
            
    df = df[columns_to_keep]

    logger.info(f"Saving {len(df)} processed records to {output_file}...")
    df.to_csv(output_file, index=False)
    logger.info("Done.")

if __name__ == "__main__":
    main()
