import json
import csv
import random
from pathlib import Path

# --- STEP 2: REDDIT INGESTION ---

def load_registry(registry_path):
    registry = []
    with open(registry_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            registry.append(row)
    return registry

def simulate_reddit_scrape(registry):
    """
    Simulates scraping Reddit for content based on aliases.
    Real implementation would use PRAW here.
    """
    subreddits = ['r/webtoons', 'r/anime', 'r/manga', 'r/animesuggest']
    simulated_posts = []

    # Mock phrases that will later trigger risk extraction
    pacing_phrases = ["it got so slow", "pacing is terrible lately", "dragging on"]
    confusion_phrases = ["I don't understand what's happening", "confusing power system", "plot makes no sense"]
    fatigue_phrases = ["another generic OP MC", "too many cliches", "tired of this trope"]
    drop_phrases = ["I dropped it at season 2", "stopped reading", "gave up on it"]
    praise_phrases = ["absolute peak", "so good", "the art is amazing"]

    for item in registry:
        content_id = item['content_id']
        aliases = item['aliases'].split('|')
        
        # Generate 3-10 simulated posts per content
        num_posts = random.randint(3, 10)
        for _ in range(num_posts):
            sub = random.choice(subreddits)
            alias = random.choice(aliases)
            
            # Mix some risk and praise
            text_parts = [f"I was reading {alias} the other day."]
            if random.random() > 0.5: text_parts.append(random.choice(praise_phrases))
            if random.random() > 0.7: text_parts.append(random.choice(pacing_phrases))
            if random.random() > 0.8: text_parts.append(random.choice(confusion_phrases))
            if random.random() > 0.75: text_parts.append(random.choice(fatigue_phrases))
            if random.random() > 0.8: text_parts.append(random.choice(drop_phrases))
            
            text = " ".join(text_parts)
            upvotes = random.randint(5, 5000)
            
            post = {
                "content_id": content_id,
                "subreddit": sub,
                "text": text,
                "upvotes": upvotes
            }
            simulated_posts.append(post)
            
    return simulated_posts

def main():
    registry_file = Path('data/registry/content_registry.csv')
    output_file = Path('data/raw/reddit_posts.jsonl')
    
    if not registry_file.exists():
        print("ERROR: Content registry not found. Run Step 1 first.")
        return
        
    registry = load_registry(registry_file)
    print(f"Loaded {len(registry)} items from registry.")
    
    posts = simulate_reddit_scrape(registry)
    
    # Save output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for post in posts:
            f.write(json.dumps(post) + '\n')
            
    print(f"✅ Saved {len(posts)} Reddit posts to {output_file}")

if __name__ == "__main__":
    main()
