import pandas as pd
import os
from pathlib import Path
from models.script_features import extract_script_features
from models.genre_comparator import GenreComparator
from models.decision_engine import DecisionEngine

def evaluate_corpus():
    corpus_dir = Path("data/script_like_corpus")
    output_file = Path("data/processed/script_evaluation_history.csv")
    
    # Init Models
    extractor = extract_script_features
    comparator = GenreComparator()
    engine = DecisionEngine()
    
    results = []
    
    print(f"Evaluating corpus from {corpus_dir}...")
    
    files = list(corpus_dir.glob("*.txt"))
    if not files:
        print("No files found!")
        return

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        # Extract Genre from filename (Format: Genre_Quality_ID.txt)
        try:
            filename = file_path.stem
            genre = filename.split("_")[0].lower()
        except:
            genre = "action" # fallback
            
        # Run Pipeline
        try:
            features = extractor(text, genre)
            comparison = comparator.compare(features, genre)
            feedback = comparator.generate_feedback(comparison, features, genre)
            decision = engine.evaluate(feedback, features)
            
            results.append({
                "doc_id": file_path.name,
                "genre": genre,
                "decision": decision['decision_label'],
                "confidence": decision['confidence_level'],
                "word_count": features['word_count'],
                "emotional_score": features['emotional_intensity_score'],
                "pacing": features['pacing_proxy']
            })
            debug_msg = f"DEBUG: Processing {file_path.name}\nDEBUG: Features: {features}\n"
            print(debug_msg)
            with open("debug_log.txt", "a", encoding="utf-8") as log_file:
                log_file.write(debug_msg)
            
            results.append({
                "doc_id": file_path.name,
                "genre": genre,
                "decision": decision['decision_label'],
                "confidence": decision['confidence_level'],
                "word_count": features['word_count'],
                "emotional_score": features['emotional_intensity_score'],
                "pacing": features['pacing_proxy']
            })
            print(f"Processed {file_path.name}: {decision['decision_label']} | Emo: {features['emotional_intensity_score']}")
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
            
    # Save Results
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"Evaluation complete. Saved to {output_file}")
    print(df['decision'].value_counts())

if __name__ == "__main__":
    evaluate_corpus()
