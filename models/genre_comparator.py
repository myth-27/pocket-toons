import pandas as pd
from pathlib import Path

# Task 3: Genre Comparison Logic
# Compare script features to genre profiles and output:
# - strengths_vs_genre
# - weaknesses_vs_genre
# - missing_common_success_traits

class GenreComparator:
    def __init__(self, profiles_path="data/processed/genre_profiles.csv"):
        self.profiles = {}
        path = Path(profiles_path)
        if path.exists():
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                self.profiles[row['genre'].lower()] = row.to_dict()
                
    def compare(self, script_features: dict, genre: str):
        """
        Compares extracted features against the specific genre profile.
        """
        genre_key = genre.lower()
        if genre_key not in self.profiles:
            return {
                "error": f"Genre '{genre}' not found in profiles. Using generic benchmarks.",
                "comparison": {}
            }
            
        profile = self.profiles[genre_key]
        comparison = {}
        
        # 1. Emotional Intensity
        # Compare to median and top quartile
        print(f"DEBUG: Feature Emo: {script_features['emotional_intensity_score']}, Profile Median: {profile['median_emotional_intensity']}")
        
        emo_diff = script_features['emotional_intensity_score'] - profile['median_emotional_intensity']
        if emo_diff > 0:
            comparison['emotional_intensity'] = "Above Median"
            if script_features['emotional_intensity_score'] >= profile.get('emotion_q3', 0):
                comparison['emotional_intensity'] = "Top Quartile (Strong)"
        else:
            comparison['emotional_intensity'] = "Below Median"
            
        # 2. Cliffhanger Density
        cliff_diff = script_features['cliffhanger_density'] - profile['median_cliffhanger_density']
        if cliff_diff > 0:
            comparison['cliffhanger_density'] = "Above Median"
        else:
             comparison['cliffhanger_density'] = "Below Median"
             
        # 3. Addiction Language (Approximated by Pacing/Cliffhanger if strict addiction keyword density not in extractor)
        # Note: script_feature_extractor doesn't output 'addiction_language_score' directly (it does emotional/cliffhanger/trope/pacing).
        # We need to align. 
        # Feature Extractor emits: emotional_intensity_score, cliffhanger_density, trope_density, character_focus_score, pacing_proxy
        # Genre Profiles has: median_emotional_intensity, median_addiction_language, median_cliffhanger_density
        # We seem to have a mismatch on 'addiction_language'. 
        # Let's map 'pacing_proxy' or 'cliffhanger_density' or just ignore addiction for now if not extracted.
        # Or better, add addiction extraction to feature extractor? 
        # Task 2 said "Extract explainable features: emotional_intensity_score, cliffhanger_density, trope_density, character_focus_score, pacing_proxy".
        # It did NOT explicitly list "addiction_score" there, but Task 1 profiles have it.
        # I will skip direct comparison of addiction_language if not in features, or use cliffhanger as proxy.
        
        return comparison


    def generate_feedback(self, comparison: dict, script_features: dict, genre: str):
        """
        Generates text feedback based on analysis.
        """
        strengths = []
        weaknesses = []
        missing = []
        
        profile = self.profiles.get(genre.lower(), {})
        
        # Emotion
        if comparison.get('emotional_intensity') == "Top Quartile (Strong)":
            strengths.append("Exceptional Emotional Intensity")
        elif comparison.get('emotional_intensity') == "Below Median":
            weaknesses.append("Low Emotional Intensity")
            
        # Cliffhanger
        if comparison.get('cliffhanger_density') == "Above Median":
            strengths.append("Strong Hook/Cliffhanger Usage")
        else:
            weaknesses.append("Weak Cliffhanger Usage")
            
        # Pacing
        if script_features.get('pacing_proxy', 0) > 0.5:
             strengths.append("Fast Pacing (High Dialogue)")
        elif script_features.get('pacing_proxy', 0) < 0.2:
             weaknesses.append("Slow Pacing (Heavy Exposition)")
             
        # Tropes
        if script_features.get('trope_density', 0) == 0:
            missing.append("Genre-Specific Tropes")
            
        return {
            "strengths_vs_genre": strengths,
            "weaknesses_vs_genre": weaknesses,
            "missing_common_traits": missing
        }
