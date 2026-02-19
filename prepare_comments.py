import json
import pandas as pd
import logging
from pathlib import Path
import hashlib
from langdetect import detect, LangDetectException
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_processing_comments.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_comment_id(text, timestamp):
    """Generates MD5 hash of text + timestamp."""
    if not isinstance(text, str):
        text = ""
    if not isinstance(timestamp, str):
        timestamp = ""
    content = f"{text}{timestamp}".encode('utf-8')
    return hashlib.md5(content).hexdigest()

def clean_text(text):
    """Normalizes whitespace."""
    if not isinstance(text, str):
        return ""
    # Replace newlines and multiple spaces with single space
    return re.sub(r'\s+', ' ', text).strip()

def detect_language(text):
    """Detects language code. Returns 'unknown' on failure."""
    try:
        if not text or len(text.strip()) < 3:
            return 'unknown'
        return detect(text)
    except LangDetectException:
        return 'unknown'

def main():
    input_file = Path("data/raw/webtoon_comments_test.jsonl")
    output_file = Path("data/processed/comments_clean.csv")
    
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

    # Requirements:
    # webtoon_title
    # episode_number
    # comment_id (hash of text + timestamp)
    # comment_text
    # comment_timestamp (ISO)
    # language
    # word_count

    # 1. Normalize whitespace
    logger.info("Normalizing whitespace...")
    df['comment_text'] = df['comment_text'].apply(clean_text)

    # 2. Drop duplicates
    # "De-duplicate comments"
    # Using text + timestamp + episode_number + webtoon_title
    logger.info("Dropping duplicates...")
    df = df.drop_duplicates(subset=['webtoon_title', 'episode_number', 'comment_text', 'comment_timestamp'])

    # 3. Drop comments with < 5 words
    logger.info("Filtering short comments...")
    # Calculate word count
    df['word_count'] = df['comment_text'].apply(lambda x: len(x.split()))
    df = df[df['word_count'] >= 5]
    logger.info(f"Remaining records after word count filter: {len(df)}")

    # 4. Generate comment_id
    logger.info("Generating comment IDs...")
    df['comment_id'] = df.apply(lambda row: generate_comment_id(row['comment_text'], row['comment_timestamp']), axis=1)

    # 5. Detect language (keep EN only)
    logger.info("Detecting language...")
    # This might be slow for large datasets, but the instructions say "keep EN only for now"
    # To speed up, we can use tqdm or apply directly. langdetect is not super fast.
    # Given requirements, we must do it.
    df['language'] = df['comment_text'].apply(detect_language)
    
    initial_len = len(df)
    df = df[df['language'] == 'en']
    logger.info(f"Filtered non-English comments. {initial_len} -> {len(df)}")

    # Select final columns
    columns_to_keep = [
        'webtoon_title',
        'episode_number',
        'comment_id',
        'comment_text',
        'comment_timestamp',
        'language',
        'word_count'
    ]
    
    # Ensure all columns exist
    for col in columns_to_keep:
        if col not in df.columns:
            df[col] = None
            
    df = df[columns_to_keep]

    logger.info(f"Saving {len(df)} processed records to {output_file}...")
    df.to_csv(output_file, index=False)
    logger.info("Done.")

if __name__ == "__main__":
    main()
