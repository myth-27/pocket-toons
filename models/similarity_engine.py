"""
Similarity Engine - Hybrid Search matching
Finds the most similar scripts to any new upload using HYBRID search (semantic + feature vector).
"""

import numpy as np
from pathlib import Path
from models.embeddings_pipeline import embed_script, load_index

def normalize_features(intrinsic_features: dict) -> np.ndarray:
    """
    Normalize the intrinsic features for cosine similarity.
    Takes the 6 intrinsic features required.
    """
    keys = [
        "emotion_score", "cliffhanger_rate", "addiction_score", 
        "character_distinctness", "world_building_density", "narrative_arc_completeness"
    ]
    feats = [intrinsic_features.get(k, 0.0) for k in keys]
    vec = np.array(feats, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec

def get_feature_vector_from_meta(script_meta: dict) -> np.ndarray:
    """Extract and normalize feature vector from stored metadata."""
    return normalize_features(script_meta.get("intrinsic_features", {}))

def calculate_similarity_score(matches: list[dict]) -> float:
    """
    Weighted average of top 5 greenlight scores.
    Weight = hybrid_similarity score of each match.
    Higher similarity match = more influence on final score.
    """
    if not matches:
        return 50.0
        
    total_weight = 0.0
    weighted_sum = 0.0
    
    for m in matches:
        w = max(0.01, m["hybrid_similarity"])
        total_weight += w
        weighted_sum += m["greenlight_score"] * w
        
    if total_weight == 0:
        return 50.0
        
    return weighted_sum / total_weight

def get_confidence_flag(matches: list[dict]) -> str:
    """
    Returns "HIGH" / "MEDIUM" / "LOW" based on std deviation of top 5 greenlight scores.
    LOW confidence = top 5 similar scripts had very different outcomes = flag in UI.
    """
    if not matches or len(matches) < 2:
        return "LOW"
        
    scores = [m["greenlight_score"] for m in matches]
    std_dev = np.std(scores)
    
    if std_dev < 10.0:
        return "HIGH"
    elif std_dev < 20.0:
        return "MEDIUM"
    else:
        return "LOW"

def find_similar_scripts(script_text: str, intrinsic_features: dict, top_k: int = 5) -> dict:
    """
    Returns top similar scripts using hybrid search.
    - Semantic similarity: cosine similarity on FAISS embeddings (70% weight)
    - Feature similarity: cosine similarity on normalized intrinsic_features vector (30% weight)
    Handles cold start gracefully.
    """
    import faiss
    
    index, metadata = load_index()
    total_scripts = len(metadata)
    
    if total_scripts == 0:
        # Cold start: empty index
        return {
            "matches": [],
            "similarity_score": 50.0,
            "confidence": "LOW",
            "cold_start": True,
            "dominant_genre_match": "None"
        }
    
    # 1. Semantic Search
    emb = embed_script(script_text).reshape(1, -1)
    faiss.normalize_L2(emb)
    
    # Retrieve more candidates to re-rank via hybrid if possible, or all if small
    k_search = min(total_scripts, 100)
    sem_distances, sem_indices = index.search(emb, k_search)
    
    # 2. Feature Search & Hybrid scoring
    query_feats = normalize_features(intrinsic_features)
    
    hybrid_results = []
    
    for rank_idx, meta_idx in enumerate(sem_indices[0]):
        if meta_idx == -1: continue
        
        meta = metadata[meta_idx]
        sem_sim = float(sem_distances[0][rank_idx])
        
        meta_feats = get_feature_vector_from_meta(meta)
        feat_sim = float(np.dot(query_feats, meta_feats))
        
        # Hybrid Similarity (70% semantic, 30% feature)
        hybrid_sim = (sem_sim * 0.7) + (feat_sim * 0.3)
        
        hybrid_results.append({
            "idx": meta_idx,
            "meta": meta,
            "semantic_similarity": round(sem_sim, 4),
            "feature_similarity": round(feat_sim, 4),
            "hybrid_similarity": round(hybrid_sim, 4)
        })
        
    hybrid_results.sort(key=lambda x: x["hybrid_similarity"], reverse=True)
    top_matches = hybrid_results[:top_k]
    
    matches_out = []
    for i, res in enumerate(top_matches):
        m = res["meta"]
        matches_out.append({
            "rank": i + 1,
            "title": m.get("title", "Unknown"),
            "semantic_similarity": res["semantic_similarity"],
            "feature_similarity": res["feature_similarity"],
            "hybrid_similarity": res["hybrid_similarity"],
            "greenlight_score": m.get("greenlight_score", 0.0),
            "decision": m.get("decision", "REWORK"),
            "label_source": m.get("label_source", "unknown"),
            "label_confidence": m.get("label_confidence", 0.0)
        })
        
    sim_score = calculate_similarity_score(matches_out)
    conf_flag = get_confidence_flag(matches_out)
    
    # Dominant decision (requirement asks for "most common decision among top 5")
    decisions = [m["decision"] for m in matches_out]
    dominant_decision = max(set(decisions), key=decisions.count) if decisions else "None"
    
    return {
        "matches": matches_out,
        "similarity_score": round(sim_score, 2),
        "confidence": conf_flag,
        "cold_start": total_scripts < top_k,  # Flag cold start if we have fewer scripts than requested
        "dominant_genre_match": dominant_decision
    }
