"""
ML Scoring Pipeline V2
Trains GBR only on intrinsic features + Gemini scores. No social metadata.
Includes 3-way blend evaluation and pseudo-labeling.
"""

import json
import uuid
import numpy as np
import pandas as pd
from pathlib import Path
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error

from models.similarity_engine import find_similar_scripts
from models.embeddings_pipeline import add_to_index, embed_script

FEATURE_COLUMNS = [
    # NLP features
    "emotion_score",
    "cliffhanger_rate",
    "addiction_score",
    # New Gemini intrinsic features
    "character_distinctness",
    "world_building_density",
    "narrative_arc_completeness",
    # Short-form Gemini scores
    "hook_strength",
    "cliffhanger_quality",
    "binge_pull",
    "dialogue_quality",
    "emotional_spike",
    "visual_potential",
    "pacing"
]

MODEL_DIR = Path("data/models")
MODEL_PATH = MODEL_DIR / "gbr_shortform_v2.pkl"
PREDICTIONS_CSV = Path("data/ml_dataset/ml_predictions.csv")
FEEDBACK_JSONL = Path("data/training_feedback.jsonl")  # Could be in data/ml_dataset/ depending on root vs sub

def load_training_data() -> pd.DataFrame:
    """
    Loads ml_predictions.csv + training_feedback.jsonl
    Merges and assigns sample weights:
      label_source == "hitl_verified"     → sample_weight = 3.0
      label_source == "mal_ground_truth"  → sample_weight = 1.0
      label_source == "gemini_pseudo_label" → sample_weight = 0.6
    """
    records = []
    
    # Try reading ml_predictions (treat as mal_ground_truth for older items if anime_mal_score exists, else pseudo_label)
    if PREDICTIONS_CSV.exists():
        df_pred = pd.read_csv(PREDICTIONS_CSV)
        for _, row in df_pred.iterrows():
            rec = {c: row.get(c, 0.0) for c in FEATURE_COLUMNS}
            # Infer old mappings if necessary, or just use 0 if absent
            rec["target"] = row.get("greenlight_score", 50.0)
            rec["title"] = row.get("content_id", "Unknown")
            
            # If it has a MAL score, consider it MAL ground truth
            if row.get("anime_mal_score", 0) > 0:
                rec["label_source"] = "mal_ground_truth"
                rec["sample_weight"] = 1.0
            else:
                rec["label_source"] = "gemini_pseudo_label"
                rec["sample_weight"] = 0.6
            records.append(rec)
            
    # Try reading HITL feedback
    if FEEDBACK_JSONL.exists():
        with open(FEEDBACK_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    rec = {}
                    # Attempt to extract feature dictionaries
                    feats = data.get("features", {})
                    g_scores = data.get("gemini_scores", {})
                    
                    for c in FEATURE_COLUMNS:
                        val = feats.get(c, g_scores.get(c, 0.0))
                        rec[c] = val
                        
                    rec["target"] = data.get("human_score", data.get("ai_score", 50.0))
                    rec["label_source"] = data.get("label_source", "hitl_verified")
                    
                    if rec["label_source"] == "hitl_verified":
                        rec["sample_weight"] = 3.0
                    elif rec["label_source"] == "mal_ground_truth":
                        rec["sample_weight"] = 1.0
                    else:
                        rec["sample_weight"] = 0.6
                        
                    records.append(rec)
                except Exception:
                    continue
                    
    df = pd.DataFrame(records)
    if df.empty:
        # Fallback dummy data so training doesn't fail on first run empty slate
        df = pd.DataFrame(columns=FEATURE_COLUMNS + ["target", "sample_weight", "label_source"])
    else:
        # Fill missing features with column medians or zeros
        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = df[col].fillna(0.0)
                
    return df

def train_gbr(df: pd.DataFrame) -> GradientBoostingRegressor:
    """
    Trains GBR with sample_weight parameter
    Uses 5-fold cross validation, prints MAE per fold
    Saves model to data/models/gbr_shortform_v2.pkl
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    if len(df) < 5:
        print("Not enough data to train GBR (need >= 5). Using default model.")
        # Create a dummy model
        model = GradientBoostingRegressor(n_estimators=10)
        X_dummy = np.zeros((10, len(FEATURE_COLUMNS)))
        y_dummy = np.ones(10) * 50.0
        model.fit(X_dummy, y_dummy)
        joblib.dump(model, MODEL_PATH)
        return model
        
    X = df[FEATURE_COLUMNS].values
    y = df["target"].values
    weights = df["sample_weight"].values
    
    kf = KFold(n_splits=min(5, len(df)), shuffle=True, random_state=42)
    model = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    
    maes = []
    print("Training GBR with cross-validation:")
    for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
        X_tr, y_tr, w_tr = X[train_idx], y[train_idx], weights[train_idx]
        X_va, y_va, w_va = X[val_idx], y[val_idx], weights[val_idx]
        
        # Fit with weights
        model.fit(X_tr, y_tr, sample_weight=w_tr)
        preds = model.predict(X_va)
        mae = mean_absolute_error(y_va, preds, sample_weight=w_va)
        maes.append(mae)
        print(f"  Fold {fold+1} MAE: {mae:.2f}")
        
    print(f"Average CV MAE: {np.mean(maes):.2f}")
    
    # Train final model on all data
    model = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    model.fit(X, y, sample_weight=weights)
    
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return model

def predict_ml_calibration(intrinsic_features: dict, gemini_scores: dict) -> float:
    """
    Loads saved GBR model
    Returns ml_calibration score (0-100) based on feature vector only
    """
    if not MODEL_PATH.exists():
        return 50.0  # Safe default
        
    try:
        model = joblib.load(MODEL_PATH)
    except Exception:
        return 50.0
        
    # Construct feature vector
    feat_vector = []
    for c in FEATURE_COLUMNS:
        val = intrinsic_features.get(c, gemini_scores.get(c, 0.0))
        feat_vector.append(val)
        
    X = np.array([feat_vector], dtype=np.float32)
    pred = model.predict(X)[0]
    return float(np.clip(pred, 0.0, 100.0))

def get_decision(score: float) -> str:
    """
    Returns text decision based on 0-100 score bounds.
    """
    if score >= 78:
        return "GREENLIGHT"
    elif score >= 62:
        return "PILOT"
    elif score >= 42:
        return "DEFER"
    else:
        return "REWORK"

def calculate_greenlight_score(
    similarity_score: float,
    script_overall: float,
    intrinsic_features: dict,
    gemini_scores: dict
) -> dict:
    """
    Runs full 3-way blend.
    """
    ml_calibration = predict_ml_calibration(intrinsic_features, gemini_scores)
    
    sim_contrib = similarity_score * 0.50
    gem_contrib = (script_overall * 10) * 0.35
    ml_contrib = ml_calibration * 0.15
    
    greenlight = sim_contrib + gem_contrib + ml_contrib
    greenlight = round(float(np.clip(greenlight, 0.0, 100.0)), 2)
    
    decision = get_decision(greenlight)
    
    return {
        "greenlight_score": greenlight,
        "similarity_contribution": round(sim_contrib, 2),
        "gemini_contribution": round(gem_contrib, 2),
        "ml_contribution": round(ml_contrib, 2),
        "decision": decision,
        "confidence": "HIGH"  # Will be refined by UI when looking at similarity matches
    }

def update_index_after_evaluation(script_text: str, title: str, intrinsic_features: dict, gemini_scores: dict, greenlight_score: float, decision: str) -> None:
    """
    After every evaluation, automatically add script to FAISS index as pseudo-label.
    So every new script evaluated makes the system smarter immediately.
    """
    emb = embed_script(script_text)
    
    script_data = {
        "script_id": str(uuid.uuid4()),
        "title": title,
        "embedding": emb,
        "intrinsic_features": intrinsic_features,
        "gemini_scores": gemini_scores,
        "greenlight_score": greenlight_score,
        "decision": decision,
        "label_source": "gemini_pseudo_label",
        "label_confidence": 0.6
    }
    
def score_new_script(script_path: str):
    """
    Orchestrates the evaluation: Gemini -> Intrinsic ML -> Similarity FAISS -> 3-way Blend.
    """
    from models.script_evaluator import evaluate_single_file, init_client
    import numpy as np
    
    script_text = Path(script_path).read_text(encoding="utf-8")
    
    # Get Gemini evaluation
    client = init_client()
    eval_result = evaluate_single_file(client, script_path)
    
    if not eval_result or "error" in eval_result:
        return None
        
    intrinsic = eval_result.get("intrinsic_features", {})
    gem_scores = {}
    dims = eval_result.get("dimension_scores", {})
    for k, v in dims.items():
        gem_scores[k] = v.get("score", 0.0)
        
    final_node = eval_result.get("final", {})
    script_overall = final_node.get("script_overall", 0.0)
    
    # Similarity
    sim_data = find_similar_scripts(script_text, intrinsic, top_k=5)
    
    # 3-Way Blend
    blend_result = calculate_greenlight_score(
        similarity_score=sim_data["similarity_score"],
        script_overall=script_overall,
        intrinsic_features=intrinsic,
        gemini_scores=gem_scores
    )
    
    return {
        "evaluation": eval_result,
        "greenlight_score": blend_result["greenlight_score"],
        "decision": blend_result["decision"],
        "similarity_data": sim_data,
        "blend_breakdown": blend_result
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    args = parser.parse_args()
    
    if args.train:
        df = load_training_data()
        model = train_gbr(df)
        print("Training complete.")
