import json
import pandas as pd
import logging
from pathlib import Path
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_processing_transcripts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants for filtering
EXCLUDE_KEYWORDS = {'music', 'ost', 'mv', 'official', 'visualizer', 'shorts'}
INCLUDE_KEYWORDS = {'review', 'summary', 'explained', 'episode', 'recap', 'analysis', 'story'}

def clean_transcript_text(segments):
    """Joins segments, lowercases, removes fillers, verifies word count."""
    if not segments or not isinstance(segments, list):
        return ""
    
    # 1. Join segments
    full_text = " ".join([seg.get('text', '') for seg in segments])
    
    # 2. Lowercase
    full_text = full_text.lower()
    
    # 3. Normalize whitespace
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    
    # 4. Remove filler words (basic list)
    # Note: "Remove filler words" is vague. Usually implies 'um', 'uh', 'like'.
    # Doing a simple regex replacement for common fillers if standalone words.
    # Be careful not to remove 'like' if it's used as a verb. 
    # For now, I will stick to 'um', 'uh', 'ah'.
    # A more robust approach requires NLP (spacy/nltk), but constraints say "No ML or external APIs".
    # nltk/spacy ARE external libraries (in requirements.txt though).
    # Since I cannot use "ML", I will stick to basic regex.
    fillers = [r'\bum\b', r'\buh\b', r'\bah\b', r'\bhm+\b']
    for filler in fillers:
        full_text = re.sub(filler, '', full_text)
    
    # Clean up again after removal
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    
    return full_text

def classify_content_type(row):
    """Classifies content type based on basic rules."""
    title = row.get('video_title')
    if not isinstance(title, str):
        title = ""
    title = title.lower()
    
    text = row.get('clean_text')
    if not isinstance(text, str):
        text = ""
    # text is already lowercased in clean_transcript_text
    
    # Check title first
    if any(k in title for k in ['review', 'analysis']):
        return 'review'
    if any(k in title for k in ['summary', 'recap', 'explained', 'story']):
        return 'summary'
    if 'episode' in title: 
        return 'episode_read'
    
    # Fallback rules
    if 'clip' in title:
        return 'clip'
    if 'music' in title or 'ost' in title:
        return 'music'
        
    return 'unknown'

def main():
    input_file = Path("data/raw/webtoon_youtube_transcripts.jsonl")
    output_file = Path("data/processed/transcripts_clean.csv")
    
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
                record = json.loads(line)
                # Flatten structure slightly for easier DataFrame creation
                flat_record = {
                    'webtoon_title': record.get('webtoon_title'),
                    'video_id': record.get('video', {}).get('video_id'),
                    'video_title': record.get('video', {}).get('title'),
                    'view_count': record.get('video', {}).get('view_count'),
                    'transcript_segments': record.get('transcript_segments')
                }
                data.append(flat_record)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
    
    if not data:
        logger.warning("No data found in input file.")
        return

    df = pd.DataFrame(data)
    logger.info(f"Loaded {len(df)} raw records.")

    # 1. Filtering rules based on Title
    logger.info("Filtering videos based on title...")
    
    def check_title_inclusion(title):
        if not isinstance(title, str):
            return False
        title_lower = title.lower()
        # EXCLUDE if title contains exclude keywords
        if any(k in title_lower for k in EXCLUDE_KEYWORDS):
            return False
        # INCLUDE only if title OR transcript contains keywords
        # We need to check transcript later too. 
        # But wait, "INCLUDE only if title OR transcript contains".
        # So if title has it, we keep. If title doesn't, we check transcript later.
        if any(k in title_lower for k in INCLUDE_KEYWORDS):
            return True
        return None # Undecided

    # Apply initial title filter (exclude is hard filter)
    df['keep_title'] = df['video_title'].apply(check_title_inclusion)
    
    # Drop where strictly False (excluded)
    df = df[df['keep_title'] != False] 
    
    # Clean text
    logger.info("Cleaning transcript text...")
    df['clean_text'] = df['transcript_segments'].apply(clean_transcript_text)
    
    # Calculate word count
    df['word_count'] = df['clean_text'].apply(lambda x: len(x.split()))
    
    # Drop if empty transcript segments (word count will likely be 0)
    # "Drop if transcript_segments is empty" handles implicit empty text
    df = df[df['transcript_segments'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    
    # Apply "INCLUDE only if title OR transcript contains" for the undecided ones
    def check_final_inclusion(row):
        if row['keep_title'] == True:
            return True
        # Check transcript text
        text_lower = row['clean_text']
        if any(k in text_lower for k in INCLUDE_KEYWORDS):
            return True
        return False
        
    df = df[df.apply(check_final_inclusion, axis=1)]

    # Drop if total word count < 300
    df = df[df['word_count'] >= 300]
    
    # Classify content type
    df['content_type'] = df.apply(classify_content_type, axis=1)

    # Select final columns
    columns_to_keep = [
        'webtoon_title',
        'video_id',
        'content_type',
        'view_count',
        'word_count',
        'clean_text'
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
