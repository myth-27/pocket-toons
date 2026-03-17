import json
import csv
from pathlib import Path

# --- STEP 3: REDDIT SIGNAL EXTRACTION ---

def load_reddit_posts(file_path):
    posts = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                posts.append(json.loads(line))
    return posts

def analyze_risk_signals(posts):
    """
    Extracts risk signals from the text of Reddit posts.
    Calculates severity based on occurrences.
    """
    # Define risk keywords
    risk_keywords = {
        'pacing_risk': ["slow", "terrible lately", "dragging", "boring now", "too long"],
        'confusion_risk': ["don't understand", "make sense", "confusing", "lost track", "what is happening"],
        'trope_fatigue': ["generic", "cliche", "tired of", "same old", "predictable"],
        'drop_off_reason': ["dropped", "stopped reading", "gave up", "quit"]
    }

    # Aggregate by content_id and risk_type
    # Keep track of counts
    risk_counts = {}  # {content_id: {risk_type: count}}
    
    for post in posts:
        cid = post['content_id']
        text = post['text'].lower()
        upvotes = post.get('upvotes', 1)
        
        # We weigh the occurrence by upvotes (log scaled to prevent outliers dominating)
        import math
        weight = 1 + math.log10(max(1, upvotes))

        if cid not in risk_counts:
            risk_counts[cid] = {k: 0 for k in risk_keywords.keys()}
            risk_counts[cid]['total_weight'] = 0

        risk_counts[cid]['total_weight'] += weight

        for risk_type, keywords in risk_keywords.items():
            for kw in keywords:
                if kw in text:
                    risk_counts[cid][risk_type] += weight

    # Calculate severity (0 to 1)
    risks = []
    for cid, counts in risk_counts.items():
        total_weight = max(1, counts['total_weight'])
        for risk_type in risk_keywords.keys():
            # Calculate proportion of weighted posts mentioning the risk
            severity = min(1.0, counts[risk_type] / total_weight * 2.5) # multiplier to make signal visible
            if severity > 0:
                risks.append({
                    'content_id': cid,
                    'risk_type': risk_type,
                    'severity': round(severity, 4)
                })

    return risks

def save_risks(risks, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['content_id', 'risk_type', 'severity'])
        writer.writeheader()
        writer.writerows(risks)

def main():
    input_file = Path('data/raw/reddit_posts.jsonl')
    output_file = Path('data/processed/reddit_risks.csv')
    
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return
        
    posts = load_reddit_posts(input_file)
    print(f"Loaded {len(posts)} Reddit posts.")
    
    risks = analyze_risk_signals(posts)
    save_risks(risks, output_file)
    
    print(f"✅ Extracted {len(risks)} risk signals and saved to {output_file}")

if __name__ == "__main__":
    main()
