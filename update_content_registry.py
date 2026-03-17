import pandas as pd
from pathlib import Path

def sync_registry():
    """
    Syncs data/external/webtoon_titles.csv with data/registry/content_registry.csv.
    """
    print("Synchronizing Content Registry...")
    
    titles_file = Path("data/external/webtoon_titles.csv")
    registry_file = Path("data/registry/content_registry.csv")
    
    if not titles_file.exists():
        print("Error: webtoon_titles.csv not found.")
        return
        
    df_titles = pd.read_csv(titles_file)
    
    # Load existing registry if it exists
    if registry_file.exists():
        df_registry = pd.read_csv(registry_file)
    else:
        df_registry = pd.DataFrame(columns=['content_id', 'canonical_title', 'aliases', 'genre'])
    
    existing_titles = set(df_registry['canonical_title'].tolist())
    new_entries = []
    
    for _, row in df_titles.iterrows():
        title = row['title']
        if title not in existing_titles:
            # Create a simple content_id
            cid = title.lower().replace(" ", "_").replace("'", "").replace(":", "")
            new_entries.append({
                'content_id': cid,
                'canonical_title': title,
                'aliases': f"{title}|{title} Webtoon",
                'genre': row['genre'].lower()
            })
    
    if new_entries:
        df_new = pd.DataFrame(new_entries)
        df_final = pd.concat([df_registry, df_new], ignore_index=True)
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_csv(registry_file, index=False)
        print(f"Added {len(new_entries)} new titles to registry.")
    else:
        print("Registry is already up to date.")

if __name__ == "__main__":
    sync_registry()
