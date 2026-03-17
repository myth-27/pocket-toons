"""
ML Greenlight Scoring Pipeline V2

Merges all data sources INCLUDING script evaluations and human feedback
→ engineers features → trains a model → scores all titles.

Data sources:
- content_intelligence.csv (emotion, addiction, cliffhanger, hype, risk)
- youtube_demand.jsonl (storytelling video views, likes, comments)
- reddit_posts_real.jsonl (real Reddit engagement)
- mal_ratings.jsonl (ground truth: MAL scores, member counts)
- script_evaluations.jsonl (Gemini script scores: hook, dialogue, pacing, etc.)
- human_feedback.csv (HITL: human overrides and corrections)

Output:
- data/ml_dataset/ml_features.csv (all features, merged)
- data/ml_dataset/ml_predictions.csv (ranked predictions)
- scoring/ml_model.pkl (trained model)

Usage:
    python ml_scoring_pipeline.py
    python ml_scoring_pipeline.py --score-script path/to/script.txt  # score a new script
"""

import argparse
import csv
import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

warnings.filterwarnings("ignore")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


# ─── File Paths ───
INTELLIGENCE_CSV = Path("data/unified/content_intelligence.csv")
YOUTUBE_DEMAND_JSONL = Path("data/raw/youtube_demand.jsonl")
REDDIT_REAL_JSONL = Path("data/raw/reddit_posts_real.jsonl")
MAL_RATINGS_JSONL = Path("data/raw/mal_ratings.jsonl")
OCR_CLEANED_DIR = Path("data/processed/ocr_cleaned")
SCRIPT_EVALS_JSONL = Path("data/ml_dataset/script_evaluations.jsonl")
HUMAN_FEEDBACK_CSV = Path("data/feedback/human_feedback.csv")
TRAINING_FEEDBACK_CSV = Path("data/ml_dataset/training_feedback.jsonl")

OUTPUT_DIR = Path("data/ml_dataset")
FEATURES_CSV = OUTPUT_DIR / "ml_features.csv"
PREDICTIONS_CSV = OUTPUT_DIR / "ml_predictions.csv"
MODEL_PATH = Path("scoring/ml_model.pkl")


def load_intelligence():
    return pd.read_csv(INTELLIGENCE_CSV)


def load_youtube_demand():
    records = []
    with open(YOUTUBE_DEMAND_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    df = pd.DataFrame(records)
    df = df.rename(columns={
        "video_count": "yt_demand_videos",
        "total_views": "yt_demand_views",
        "total_likes": "yt_demand_likes",
        "total_comments": "yt_demand_comments",
        "avg_views": "yt_demand_avg_views",
        "top_video_views": "yt_demand_top_views",
    })
    return df[["content_id", "yt_demand_videos", "yt_demand_views",
               "yt_demand_likes", "yt_demand_comments", "yt_demand_avg_views",
               "yt_demand_top_views"]]


def load_reddit_real():
    posts = []
    if not REDDIT_REAL_JSONL.exists():
        return pd.DataFrame(columns=["content_id", "reddit_post_count",
                                      "reddit_avg_score", "reddit_total_comments",
                                      "reddit_avg_upvote_ratio"])
    with open(REDDIT_REAL_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            try:
                posts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not posts:
        return pd.DataFrame(columns=["content_id", "reddit_post_count",
                                      "reddit_avg_score", "reddit_total_comments",
                                      "reddit_avg_upvote_ratio"])
    df = pd.DataFrame(posts)
    agg = df.groupby("content_id").agg(
        reddit_post_count=("score", "count"),
        reddit_avg_score=("score", "mean"),
        reddit_max_score=("score", "max"),
        reddit_total_comments=("num_comments", "sum"),
        reddit_avg_upvote_ratio=("upvote_ratio", "mean"),
    ).reset_index()
    return agg


def load_mal_ratings():
    records = []
    with open(MAL_RATINGS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    df = pd.DataFrame(records)
    return df[["content_id", "is_adapted", "anime_mal_score", "anime_members",
               "anime_rank", "manga_mal_score", "manga_members"]]


def load_ocr_features():
    if not OCR_CLEANED_DIR.exists():
        return pd.DataFrame(columns=["content_id", "ocr_avg_dialogue_lines",
                                      "ocr_avg_word_count", "ocr_episodes_available"])
    records = {}
    for json_file in OCR_CLEANED_DIR.glob("*_clean.json"):
        fname = json_file.stem
        parts = fname.rsplit("_ep", 1)
        content_id = parts[0] if len(parts) == 2 else fname
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if content_id not in records:
                records[content_id] = {"dialogue_lines": [], "word_counts": []}
            dialogue = data.get("dialogue", [])
            records[content_id]["dialogue_lines"].append(len(dialogue))
            records[content_id]["word_counts"].append(data.get("word_count", 0))
        except Exception:
            continue
    rows = []
    for cid, vals in records.items():
        rows.append({
            "content_id": cid,
            "ocr_avg_dialogue_lines": np.mean(vals["dialogue_lines"]) if vals["dialogue_lines"] else 0,
            "ocr_avg_word_count": np.mean(vals["word_counts"]) if vals["word_counts"] else 0,
            "ocr_episodes_available": len(vals["dialogue_lines"]),
        })
    return pd.DataFrame(rows)


def load_script_evaluations():
    """Load Gemini script evaluation scores, aggregated per title."""
    if not SCRIPT_EVALS_JSONL.exists():
        return pd.DataFrame(columns=["content_id", "script_hook", "script_dialogue",
                                      "script_pacing", "script_emotion", "script_visual",
                                      "script_adaptation", "script_overall"])
    records = []
    with open(SCRIPT_EVALS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not records:
        return pd.DataFrame(columns=["content_id", "script_hook", "script_dialogue",
                                      "script_pacing", "script_emotion", "script_visual",
                                      "script_adaptation", "script_overall"])
    df = pd.DataFrame(records)
    # Aggregate per title (average across episodes)
    score_cols = {
        "hook_strength": "script_hook",
        "dialogue_quality": "script_dialogue",
        "pacing": "script_pacing",
        "emotional_depth": "script_emotion",
        "visual_potential": "script_visual",
        "adaptation_potential": "script_adaptation",
        "overall_score": "script_overall",
    }
    
    # Rename and aggregate
    rename_map = {k: v for k, v in score_cols.items() if k in df.columns}
    df = df.rename(columns=rename_map)
    
    agg_cols = [v for v in score_cols.values() if v in df.columns]
    if not agg_cols:
        return pd.DataFrame(columns=["content_id"] + list(score_cols.values()))
    
    agg = df.groupby("content_id")[agg_cols].mean().reset_index()
    return agg


def load_human_feedback():
    """Load human feedback and convert to training signal adjustments."""
    if not HUMAN_FEEDBACK_CSV.exists():
        return {}
    
    try:
        df = pd.read_csv(HUMAN_FEEDBACK_CSV)
        if df.empty:
            return {}
        
        # Convert human decisions to score adjustments
        decision_scores = {"GREENLIGHT": 1.0, "PILOT": 0.5, "DEFER": -0.5, "REWORK": -1.0}
        adjustments = {}
        
        for _, row in df.iterrows():
            genre = row.get("genre", "unknown")
            ai_dec = row.get("ai_decision", "PILOT")
            human_dec = row.get("human_decision", "PILOT")
            
            if ai_dec != human_dec:
                fingerprint = row.get("fingerprint", "")
                adjustment = decision_scores.get(human_dec, 0) - decision_scores.get(ai_dec, 0)
                adjustments[fingerprint] = adjustment
        
        return adjustments
    except Exception:
        return {}


def merge_all_data():
    """Merge all data sources into one feature table."""
    print("  Loading data sources...")
    
    intel = load_intelligence()
    print(f"    Content Intelligence: {len(intel)} titles")
    
    yt = load_youtube_demand()
    print(f"    YouTube Demand: {len(yt)} titles")
    
    reddit = load_reddit_real()
    print(f"    Reddit Real: {len(reddit)} titles")
    
    mal = load_mal_ratings()
    print(f"    MAL Ratings: {len(mal)} titles")
    
    ocr = load_ocr_features()
    print(f"    OCR Scripts: {len(ocr)} titles")
    
    script_evals = load_script_evaluations()
    print(f"    Script Evaluations: {len(script_evals)} titles")
    
    feedback = load_human_feedback()
    print(f"    Human Feedback Adjustments: {len(feedback)} entries")
    
    # Merge
    df = intel.merge(yt, on="content_id", how="left")
    df = df.merge(reddit, on="content_id", how="left")
    df = df.merge(mal, on="content_id", how="left")
    df = df.merge(ocr, on="content_id", how="left")
    df = df.merge(script_evals, on="content_id", how="left")
    
    # Fill NaN with 0 for numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    df["is_adapted"] = df["is_adapted"].fillna(False)
    
    print(f"    Merged: {len(df)} titles, {len(df.columns)} columns")
    return df


def engineer_features(df):
    """Create derived features for ML."""
    # YouTube demand score (normalized)
    if df["yt_demand_views"].max() > 0:
        df["yt_demand_score"] = MinMaxScaler().fit_transform(
            np.log1p(df[["yt_demand_views"]]))
    else:
        df["yt_demand_score"] = 0
    
    # Reddit engagement score
    if df["reddit_post_count"].max() > 0:
        df["reddit_engagement_score"] = MinMaxScaler().fit_transform(
            np.log1p(df[["reddit_total_comments"]]))
    else:
        df["reddit_engagement_score"] = 0
    
    # Quality composite
    df["quality_composite"] = (
        df["webtoon_emotion_score"] * 0.35 +
        df["webtoon_addiction_score"] * 0.35 +
        df["webtoon_cliffhanger_rate"] * 0.15 +
        df["youtube_hype_score"] * 0.15
    )
    
    # Demand composite
    df["demand_composite"] = (
        df["yt_demand_score"] * 0.6 +
        df["reddit_engagement_score"] * 0.4
    )
    
    # Risk normalized (invert)
    if df["reddit_risk_score"].max() > 0:
        df["risk_normalized"] = 1 - MinMaxScaler().fit_transform(
            df[["reddit_risk_score"]])
    else:
        df["risk_normalized"] = 0.5
    
    # Script quality composite (from Gemini evaluations)
    script_cols = ["script_hook", "script_dialogue", "script_pacing",
                   "script_emotion", "script_visual", "script_adaptation"]
    has_script = any(df[c].sum() > 0 for c in script_cols if c in df.columns)
    
    if has_script:
        df["script_quality_score"] = (
            df.get("script_hook", 0) * 0.15 +
            df.get("script_dialogue", 0) * 0.20 +
            df.get("script_pacing", 0) * 0.15 +
            df.get("script_emotion", 0) * 0.20 +
            df.get("script_visual", 0) * 0.15 +
            df.get("script_adaptation", 0) * 0.15
        ) / 10  # Normalize to 0-1
    else:
        df["script_quality_score"] = 0
    
    # MAL popularity
    if df["anime_members"].max() > 0:
        df["mal_popularity_score"] = MinMaxScaler().fit_transform(
            np.log1p(df[["anime_members"]]))
    else:
        df["mal_popularity_score"] = 0
    
    return df


def train_model(df):
    """Train ML model with script evaluation + metadata + reaction features."""
    feature_cols = [
        # Content signals
        "webtoon_emotion_score", "webtoon_addiction_score",
        "webtoon_cliffhanger_rate", "youtube_hype_score",
        "youtube_confusion_score", "reddit_risk_score",
        # Demand signals
        "yt_demand_videos", "yt_demand_score",
        "reddit_engagement_score", "reddit_post_count",
        "reddit_avg_score", "reddit_avg_upvote_ratio",
        # Script evaluation signals (from Gemini)
        "script_hook", "script_dialogue", "script_pacing",
        "script_emotion", "script_visual", "script_adaptation",
        "script_overall", "script_quality_score",
        # Composite signals
        "quality_composite", "demand_composite", "risk_normalized",
    ]
    
    # Only use columns that exist
    feature_cols = [c for c in feature_cols if c in df.columns]
    
    # Filter to titles with MAL scores
    train_mask = (df["anime_mal_score"] > 0) & (df["is_adapted"] == True)
    train_df = df[train_mask].copy()
    
    if len(train_df) < 10:
        print("  ⚠️  Not enough training data, using rule-based scoring")
        return None, feature_cols
    
    X_train = train_df[feature_cols].values
    y_train = train_df["anime_mal_score"].values
    
    print(f"\n  Training data: {len(train_df)} titles with MAL scores")
    print(f"  Target range: {y_train.min():.2f} – {y_train.max():.2f}")
    print(f"  Features: {len(feature_cols)}")
    
    # Include script eval features count
    script_feats = [c for c in feature_cols if c.startswith("script_")]
    print(f"  Script evaluation features: {len(script_feats)}")
    
    model = GradientBoostingRegressor(
        n_estimators=100, max_depth=3, learning_rate=0.1,
        min_samples_split=5, min_samples_leaf=3, random_state=42,
    )
    model.fit(X_train, y_train)
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=min(5, len(train_df)),
                                 scoring="neg_mean_absolute_error")
    print(f"  Cross-val MAE: {-cv_scores.mean():.3f} (±{cv_scores.std():.3f})")
    
    y_pred_train = model.predict(X_train)
    train_r2 = r2_score(y_train, y_pred_train)
    train_mae = mean_absolute_error(y_train, y_pred_train)
    print(f"  Train R²: {train_r2:.3f}, Train MAE: {train_mae:.3f}")
    
    # Feature importance
    importances = sorted(zip(feature_cols, model.feature_importances_),
                          key=lambda x: -x[1])
    print(f"\n  Top 8 Feature Importances:")
    for feat, imp in importances[:8]:
        bar = "█" * int(imp * 50)
        print(f"    {feat:<30} {imp:.3f} {bar}")
    
    return model, feature_cols


def predict_and_rank(df, model, feature_cols):
    """Score all titles and create rankings."""
    X_all = df[feature_cols].values
    
    if model is not None:
        df["ml_predicted_score"] = model.predict(X_all)
    else:
        df["ml_predicted_score"] = df["quality_composite"] * 10
    
    # Normalize ML Score to 0-100
    pred_min = df["ml_predicted_score"].min()
    pred_max = df["ml_predicted_score"].max()
    if pred_max > pred_min:
        df["ml_norm"] = (df["ml_predicted_score"] - pred_min) / (pred_max - pred_min) * 100
    else:
        df["ml_norm"] = 50.0

    # Blend 70% intrinsic AI script quality with 30% ML simulated baseline
    # just like the standalone UI upload. If script metrics don't exist, rely 100% on ML.
    def calculate_blended_score(row):
        ml_base = row['ml_norm']
        if row.get('script_overall', 0) > 0:
            script_score = row['script_overall'] * 10
            return (script_score * 0.7) + (ml_base * 0.3)
        return ml_base
        
    df["greenlight_score"] = df.apply(calculate_blended_score, axis=1).round(1)
    
    # Apply human feedback adjustments
    feedback_adj = load_human_feedback()
    if feedback_adj:
        for fp, adj in feedback_adj.items():
            # Adjust scores for matching fingerprints
            parts = fp.split("|")
            if len(parts) >= 1:
                genre = parts[0]
                mask = df["genre"] == genre
                df.loc[mask, "greenlight_score"] = (
                    df.loc[mask, "greenlight_score"] + adj * 5
                ).clip(0, 100)
    
    def label(score):
        if score >= 78: return "GREENLIGHT"
        elif score >= 62: return "PILOT"
        elif score >= 42: return "DEFER"
        else: return "REWORK"
    
    df["decision"] = df["greenlight_score"].apply(label)
    
    def confidence(row):
        signals = 0
        if row.get("yt_demand_views", 0) > 0: signals += 1
        if row.get("reddit_post_count", 0) > 0: signals += 1
        if row.get("anime_mal_score", 0) > 0: signals += 1
        if row.get("ocr_episodes_available", 0) > 0: signals += 1
        if row.get("script_overall", 0) > 0: signals += 1
        if signals >= 4: return "HIGH"
        if signals >= 2: return "MEDIUM"
        return "LOW"
    
    df["confidence"] = df.apply(confidence, axis=1)
    return df


def save_results(df, model, feature_cols):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Path("scoring").mkdir(parents=True, exist_ok=True)
    
    df.to_csv(FEATURES_CSV, index=False)
    
    pred_cols = [
        "content_id", "genre", "greenlight_score", "decision", "confidence",
        "ml_predicted_score", "anime_mal_score", "is_adapted",
        "quality_composite", "demand_composite", "risk_normalized",
        "script_quality_score", "script_overall",
        "yt_demand_views", "reddit_post_count", "anime_members",
    ]
    pred_cols = [c for c in pred_cols if c in df.columns]
    pred_df = df[pred_cols].sort_values("greenlight_score", ascending=False)
    pred_df.to_csv(PREDICTIONS_CSV, index=False)
    
    if model is not None:
        joblib.dump({"model": model, "features": feature_cols}, MODEL_PATH)
    
    return pred_df


def score_new_script(script_path):
    """Score a new uploaded script using the trained model + Gemini evaluation."""
    from script_evaluator import evaluate_single_file, init_client
    
    model_data = joblib.load(MODEL_PATH)
    model = model_data["model"]
    feature_cols = model_data["features"]
    
    # Get Gemini evaluation
    client = init_client()
    eval_result = evaluate_single_file(client, script_path)
    
    print(f"DEBUG: eval_result = {eval_result}")
    
    if not eval_result or "error" in eval_result:
        print("  ❌ Script evaluation failed")
        return None
    
    # Create a feature vector using evaluation + defaults for missing signals
    features = {col: 0 for col in feature_cols}
    
    # Map Gemini scores (Handle new Short-Form Mobile rubric vs old Legacy rubric)
    dims = eval_result.get("dimension_scores", {})
    final_node = eval_result.get("final", {})

    if dims:
        features["script_hook"] = dims.get("hook_strength", {}).get("score", 0)
        features["script_dialogue"] = dims.get("dialogue_quality", {}).get("score", 0)
        features["script_pacing"] = dims.get("pacing", {}).get("score", 0)
        features["script_emotion"] = dims.get("emotional_spike", {}).get("score", 0)
        features["script_visual"] = dims.get("visual_potential", {}).get("score", 0)
        features["script_adaptation"] = dims.get("binge_pull", {}).get("score", 0) 
        features["script_overall"] = final_node.get("script_overall", 0)
        features["script_quality_score"] = final_node.get("script_overall", 0) / 10
    else:
        features["script_hook"] = eval_result.get("hook_strength", 0)
        features["script_dialogue"] = eval_result.get("dialogue_quality", 0)
        features["script_pacing"] = eval_result.get("pacing", 0)
        features["script_emotion"] = eval_result.get("emotional_depth", 0)
        features["script_visual"] = eval_result.get("visual_potential", 0)
        features["script_adaptation"] = eval_result.get("adaptation_potential", 0)
        features["script_overall"] = eval_result.get("overall_score", 0)
        features["script_quality_score"] = (
            features["script_hook"] * 0.15 +
            features["script_dialogue"] * 0.20 +
            features["script_pacing"] * 0.15 +
            features["script_emotion"] * 0.20 +
            features["script_visual"] * 0.15 +
            features["script_adaptation"] * 0.15
        ) / 10
    
    # Use 85th percentile values for positive metadata features that are unknown
    # (Use 15th percentile for risk/confusion)
    try:
        import pandas as pd
        full_df = pd.read_csv(FEATURES_CSV)
        for col in feature_cols:
            if col not in features or features[col] == 0:
                if col in full_df.columns:
                    if "risk" in col or "confusion" in col:
                        features[col] = full_df[col].quantile(0.15)
                    else:
                        features[col] = full_df[col].quantile(0.85)
    except Exception:
        pass
    
    X = np.array([[features.get(c, 0) for c in feature_cols]])
    predicted_score = model.predict(X)[0]
    
    # Normalize ML Score using global distribution
    try:
        full_df = pd.read_csv(PREDICTIONS_CSV)
        min_s = full_df["ml_predicted_score"].min()
        max_s = full_df["ml_predicted_score"].max()
        ml_norm = ((predicted_score - min_s) / (max_s - min_s) * 100) if max_s > min_s else 50
    except Exception:
        ml_norm = predicted_score * 10
        
    ml_norm = max(0, min(100, ml_norm))
    
    # For standalone uploaded scripts, intrinsic script quality is the strongest signal we have.
    # Blend 70% intrinsic script quality with 30% ML simulated baseline.
    script_based_score = features["script_overall"] * 10  # e.g., 7.5 -> 75
    greenlight = (script_based_score * 0.7) + (ml_norm * 0.3)
    
    greenlight = max(0, min(100, round(greenlight, 1)))
    
    if greenlight >= 78: decision = "GREENLIGHT"
    elif greenlight >= 62: decision = "PILOT"
    elif greenlight >= 42: decision = "DEFER"
    else: decision = "REWORK"
    
    return {
        "greenlight_score": greenlight,
        "decision": decision,
        "ml_predicted_score": round(predicted_score, 2),
        "evaluation": eval_result,
        "script_quality_score": round(features["script_quality_score"], 3),
    }


def main():
    parser = argparse.ArgumentParser(description="ML Greenlight Scoring Pipeline V2")
    parser.add_argument("--score-script", type=str, help="Score a single uploaded script")
    args = parser.parse_args()
    
    if args.score_script:
        print(f"\n  Scoring: {args.score_script}")
        result = score_new_script(args.score_script)
        if result:
            print(f"\n  {'='*40}")
            print(f"  GREENLIGHT SCORE: {result['greenlight_score']}")
            print(f"  DECISION: {result['decision']}")
            print(f"  ML Score: {result['ml_predicted_score']}")
            print(f"  Script Quality: {result['script_quality_score']}")
            print(f"\n  Evaluation Details:")
            for k, v in result["evaluation"].items():
                if k not in ["strengths", "weaknesses", "one_line_verdict"]:
                    print(f"    {k}: {v}")
            print(f"\n  Verdict: {result['evaluation'].get('one_line_verdict', 'N/A')}")
            print(f"  {'='*40}")
        return
    
    print(f"\n{'='*60}")
    print(f"  ML GREENLIGHT SCORING PIPELINE V2")
    print(f"  (with Script Evaluations + Human Feedback)")
    print(f"{'='*60}\n")
    
    print("Step 1: Merging data sources...")
    df = merge_all_data()
    
    print("\nStep 2: Engineering features...")
    df = engineer_features(df)
    
    print("\nStep 3: Training ML model...")
    model, feature_cols = train_model(df)
    
    print("\nStep 4: Scoring and ranking all titles...")
    df = predict_and_rank(df, model, feature_cols)
    
    print("\nStep 5: Saving results...")
    pred_df = save_results(df, model, feature_cols)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"\n  Decision Distribution:")
    for label, count in pred_df["decision"].value_counts().items():
        print(f"    {label}: {count}")
    
    print(f"\n  Top 10 Greenlight Candidates:")
    print(f"  {'Rank':<5} {'Title':<35} {'Score':>6} {'Decision':<12} {'MAL':>5} {'Script':>7}")
    print(f"  {'─'*5} {'─'*35} {'─'*6} {'─'*12} {'─'*5} {'─'*7}")
    for i, (_, row) in enumerate(pred_df.head(10).iterrows(), 1):
        mal = f"{row['anime_mal_score']:.1f}" if row.get("anime_mal_score", 0) > 0 else "N/A"
        scr = f"{row.get('script_overall', 0):.1f}" if row.get("script_overall", 0) > 0 else "N/A"
        print(f"  {i:<5} {row['content_id']:<35} {row['greenlight_score']:>5.1f} "
              f"{row['decision']:<12} {mal:>5} {scr:>7}")
    
    print(f"\n  📊 Full features: {FEATURES_CSV}")
    print(f"  📋 Rankings: {PREDICTIONS_CSV}")
    print(f"  🤖 Model: {MODEL_PATH}" if model else "  ⚠️ No model")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
