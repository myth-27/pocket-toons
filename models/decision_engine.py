# Task 4: Decision Engine
# Produce:
# - decision_label: GREENLIGHT, PILOT, DEFER, REWORK
# - confidence_level
# - explanation_text
# - improvement_suggestions

class DecisionEngine:
    def evaluate(self, comparison_feedback: dict, script_features: dict, genre_confidence: str = "High"):
        strengths = comparison_feedback['strengths_vs_genre']
        weaknesses = comparison_feedback['weaknesses_vs_genre']
        missing = comparison_feedback['missing_common_traits']
        
        score = 0
        # Simple scoring heuristic for decision
        if "Exceptional Emotional Intensity" in strengths: score += 3
        if "Strong Hook/Cliffhanger Usage" in strengths: score += 2
        if "Fast Pacing (High Dialogue)" in strengths: score += 1
        
        if "Low Emotional Intensity" in weaknesses: score -= 2
        if "Weak Cliffhanger Usage" in weaknesses: score -= 1
        if "Slow Pacing (Heavy Exposition)" in weaknesses: score -= 1
        
        if "Genre-Specific Tropes" in missing: score -= 1
        
        # Decision Logic
        if score >= 4:
            decision = "GREENLIGHT"
            raw_confidence = "High"
        elif score >= 2:
            decision = "PILOT"
            raw_confidence = "Medium"
        elif score >= 0:
            decision = "REWORK"
            raw_confidence = "Medium"
        else:
            decision = "DEFER"
            raw_confidence = "High" # Confident that it's bad
            
        # Calibrate Confidence with Genre Data Strength
        # If we have little data for this genre, we can't be High confidence
        final_confidence = raw_confidence
        
        if genre_confidence == "Low":
            final_confidence = "Low"
        elif genre_confidence == "Medium" and raw_confidence == "High":
            final_confidence = "Medium"
            
        # Explanation
        explanation = f"Script evaluated as {decision}. "
        if strengths:
            explanation += f"Driven by {', '.join(strengths).lower()}. "
        if weaknesses:
            explanation += f"Hampered by {', '.join(weaknesses).lower()}. "
            
        # Suggestions
        suggestions = []
        if "Low Emotional Intensity" in weaknesses:
            suggestions.append("Increase usage of emotive language and reactions.")
        if "Weak Cliffhanger Usage" in weaknesses:
            suggestions.append("End scenes with questions or revelations.")
        if "Slow Pacing (Heavy Exposition)" in weaknesses:
            suggestions.append("Convert exposition blocks to dialogue.")
        if "Genre-Specific Tropes" in missing:
            suggestions.append("Incorporate more genre-typical elements (tropes).")
            
        return {
            "decision_label": decision,
            "confidence_level": final_confidence,
            "explanation_text": explanation,
            "improvement_suggestions": suggestions
        }
