import subprocess
import sys
from pathlib import Path

# Task 3: Scale Data Ingestion (Safe Way)
# Running the pipeline automatically:
# - updates episode signals
# - updates comment signals
# - updates genre_profiles.csv

def run_step(script_name, description):
    print(f"\n--- {description} ({script_name}) ---")
    script_path = Path(script_name)
    if not script_path.exists():
        print(f"Error: {script_name} not found.")
        sys.exit(1)
        
    try:
        # Use simple python command assuming venv is active or available via 'python'
        # In this environment, we use 'venv\Scripts\python.exe' if available, else 'python'
        cmd = [sys.executable, str(script_path)]
        
        # If running in a specific venv structure manually
        venv_python = Path("venv/Scripts/python.exe")
        if venv_python.exists():
            cmd = [str(venv_python), str(script_path)]
            
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}:")
        print(e.stderr)
        sys.exit(1)

def main():
    print("Starting Pipeline Update...")
    
    # 1. Ingest Data (Simulated Scraping)
    # Reads data/external/webtoon_titles.csv -> writes data/processed/*_signals.csv
    run_step("generate_genre_data.py", "Ingesting & Processing New Titles")
    
    # 2. Score & Rank
    # Reads *_signals.csv -> writes data/processed/greenlight_ranking.csv
    run_step("scoring/greenlight_score.py", "Calculating Greenlight Scores")
    
    # 3. Update Genre Profiles
    # Reads greenlight_ranking.csv -> writes data/processed/genre_profiles.csv
    run_step("create_genre_profiles.py", "Updating Genre Profiles")
    
    print("\n✅ Pipeline Update Complete.")
    print("New titles added alongside existing data.")

if __name__ == "__main__":
    main()
