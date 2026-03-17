import subprocess
import sys
from pathlib import Path

def run_pipeline():
    print("STARTING EXPANDED DATA PIPELINE")
    
    # 1. Sync Registry
    print("Synchronizing Content Registry...")
    subprocess.run([sys.executable, "update_content_registry.py"], check=True)
    
    # 2. Run Data Generators (Enriched Signals)
    print("Fetching Multi-Source Enriched Signals...")
    subprocess.run([sys.executable, "generate_genre_data.py"], check=True)
    
    # 3. Unify Intelligence
    print("Unifying Content Intelligence...")
    # Using run_command style logic if it's in a subdirectory or needs python path
    subprocess.run([sys.executable, "-m", "nlp.unify_intelligence"], check=True)
    
    # 4. Create Genre Profiles
    print("Creating Genre Profiles...")
    subprocess.run([sys.executable, "create_genre_profiles.py"], check=True)
    
    # 5. Corpus Evaluation
    print("Evaluating Synthetic Corpus...")
    subprocess.run([sys.executable, "evaluate_corpus.py"], check=True)
    
    # 6. ML Dataset Preparation
    print("Preparing ML Dataset (ML-READY)...")
    subprocess.run([sys.executable, "prepare_ml_dataset.py"], check=True)
    
    print("\nEXPANDED PIPELINE COMPLETE.")
    print("New genres and titles are now live in the system.")

if __name__ == "__main__":
    run_pipeline()
