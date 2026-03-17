"""
Embeddings Pipeline - Memory of the system
Uses sentence-transformers and FAISS to store and retrieve scripts.
"""

import os
import json
import uuid
from pathlib import Path
import numpy as np

# Load faiss and sentence-transformers only when needed to save memory
try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    pass

_model = None

INDEX_DIR = Path("data/faiss_index")
INDEX_PATH = INDEX_DIR / "scripts.index"
METADATA_PATH = INDEX_DIR / "metadata.json"


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_script(script_text: str) -> np.ndarray:
    """
    Returns 384-dim embedding vector for a script using all-MiniLM-L6-v2.
    """
    model = get_model()
    # model.encode returns (D,) array for a single string
    emb = model.encode([script_text])[0]
    return np.array(emb, dtype=np.float32)


def load_index() -> tuple['faiss.Index', list[dict]]:
    """
    Loads FAISS index + metadata from disk.
    Creates empty index if none exists yet.
    """
    import faiss
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    if INDEX_PATH.exists() and METADATA_PATH.exists():
        index = faiss.read_index(str(INDEX_PATH))
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return index, metadata
    
    # all-MiniLM-L6-v2 uses 384 dimensions
    dim = 384
    # IndexFlatIP used for Cosine Similarity (requires normalized vectors)
    index = faiss.IndexFlatIP(dim)
    return index, []


def save_index(index: 'faiss.Index', metadata: list[dict]) -> None:
    """
    Persists FAISS index + metadata to disk.
    """
    import faiss
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def add_to_index(script_data: dict) -> str:
    """
    Adds a new script to FAISS index, returns script_id.
    Saves metadata to data/faiss_index/metadata.json alongside FAISS index.
    """
    import faiss
    index, metadata = load_index()
    
    # Make a copy to avoid mutating the original dict
    data_copy = dict(script_data)
    
    script_id = data_copy.get("script_id", str(uuid.uuid4()))
    data_copy["script_id"] = script_id
    
    emb = data_copy.pop("embedding")
    if not isinstance(emb, np.ndarray):
        emb = np.array(emb, dtype=np.float32)
        
    emb_reshaped = emb.reshape(1, -1)
    faiss.normalize_L2(emb_reshaped)
    
    index.add(emb_reshaped)
    metadata.append(data_copy)
    
    save_index(index, metadata)
    return script_id


def get_index_stats() -> dict:
    """
    Returns: total scripts, breakdown by label_source, average greenlight_score
    """
    _, metadata = load_index()
    total = len(metadata)
    if total == 0:
        return {
            "total_scripts": 0, 
            "label_source_breakdown": {}, 
            "average_greenlight_score": 0.0
        }
    
    breakdown = {}
    total_score = 0.0
    for m in metadata:
        src = m.get("label_source", "unknown")
        breakdown[src] = breakdown.get(src, 0) + 1
        total_score += m.get("greenlight_score", 0.0)
        
    return {
        "total_scripts": total,
        "label_source_breakdown": breakdown,
        "average_greenlight_score": round(total_score / total, 2)
    }
