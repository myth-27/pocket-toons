# Task 4: Decision Engine
# Produce:
# - decision_label: GREENLIGHT, PILOT, DEFER, REWORK
# - confidence_level
# - explanation_text
# - improvement_suggestions

class DecisionEngine:
    def evaluate(self, comparison_feedback: dict, script_features: dict, genre: str = "unknown", genre_confidence: str = "High"):
        strengths = comparison_feedback['strengths_vs_genre']
        weaknesses = comparison_feedback['weaknesses_vs_genre']
        missing = comparison_feedback['missing_common_traits']
        
        # 3-LAYER DECISION LOGIC
        
        # --- LAYER 1: HARD GATES ---
        failed_gates = []
        
        # 1. Hook Gate (Needs tension/hook)
        if "Weak Cliffhanger Usage" in weaknesses or script_features.get('cliffhanger_density', 0) < 0.2:
            failed_gates.append("Hook Gate (Weak opening/closing tension)")
            
        # 2. Clarity Gate (from pacing/exposition proxy)
        if "Slow Pacing (Heavy Exposition)" in weaknesses or script_features.get('pacing_proxy', 1) < 0.15:
            failed_gates.append("Clarity Gate (Heavy exposition/pacing flaw)")
            
        # 3. Genre Alignment Gate
        if "Genre-Specific Tropes" in missing:
            failed_gates.append("Genre Gate (Missing core tropes)")
            
        # --- LAYER 2: QUALITY BANDS (Categorical) ---
        bands = {}
        
        # Emotional Pull
        if "Exceptional Emotional Intensity" in strengths: bands['Emotion'] = "HIGH"
        elif "Low Emotional Intensity" in weaknesses: bands['Emotion'] = "LOW"
        else: bands['Emotion'] = "MEDIUM"
        
        # Addiction/Momentum
        if "Fast Pacing (High Dialogue)" in strengths or "Strong Hook/Cliffhanger Usage" in strengths:
            bands['Addiction'] = "HIGH"
        elif "Slow Pacing (Heavy Exposition)" in weaknesses:
            bands['Addiction'] = "LOW"
        else:
            bands['Addiction'] = "MEDIUM"
            
        # Risk Exposure (Historical Reddit + Structural)
        historical_risks = comparison_feedback.get('historical_risks', [])
        if historical_risks:
            bands['Risk'] = "HIGH"
        elif len(weaknesses) >= 2:
            bands['Risk'] = "MEDIUM"
        else:
            bands['Risk'] = "LOW"
            
        # Overall Quality Heuristic (Based strictly on bands)
        if bands['Emotion'] == "HIGH" and bands['Addiction'] == "HIGH": overall_q = "HIGH"
        elif bands['Emotion'] == "LOW" or bands['Addiction'] == "LOW": overall_q = "LOW"
        else: overall_q = "MEDIUM"
            
        # --- LAYER 3: DECISION MATRIX ---
        decision = "DEFER" # Default
        
        # Matrix rules
        if overall_q == "HIGH" and bands['Risk'] == "LOW":
            decision = "GREENLIGHT"
        elif overall_q == "HIGH" and bands['Risk'] == "MEDIUM":
            decision = "PILOT"
        elif overall_q == "MEDIUM" and bands['Risk'] == "LOW":
            decision = "PILOT"
        elif overall_q == "MEDIUM" and bands['Risk'] == "MEDIUM":
            decision = "DEFER"
        elif bands['Risk'] == "HIGH" or overall_q == "LOW":
            decision = "REWORK"
            
        # Gate Enforcements (HARD OVERRIDE)
        raw_confidence = "Medium"
        if decision == "GREENLIGHT": raw_confidence = "High"
        if decision == "REWORK": raw_confidence = "High"
        
        if failed_gates:
            # Cannot be greenlight or pilot if a gate fails
            if decision in ["GREENLIGHT", "PILOT"]:
                decision = "DEFER"
            raw_confidence = "High" # Confident in rejection due to gate failure
            
        # Calibrate Confidence with Multi-Source Data Strength
        final_confidence = raw_confidence
        if genre_confidence == "Low":
            final_confidence = "Low"
        elif genre_confidence == "Medium" and raw_confidence == "High":
            final_confidence = "Medium"
            
        # Check Human Feedback Memory System
        try:
            from models.feedback_memory import FeedbackMemory
            memory = FeedbackMemory()
            historical_warnings = memory.get_historical_warnings(
                genre, 
                failed_gates, 
                bands['Emotion'], 
                bands['Addiction'], 
                bands['Risk']
            )
        except ImportError:
            historical_warnings = []
            
        # Explanation
        explanation = f"Script evaluated as {decision}. "
        if strengths:
            explanation += f"Driven by {', '.join(strengths).lower()}. "
        if weaknesses:
            explanation += f"Hampered by {', '.join(weaknesses).lower()}. "
            
        if historical_warnings:
            explanation += "\n\n**HUMAN FEEDBACK MEMORY WARNING:**\n"
            for hw in historical_warnings:
                explanation += f"- {hw}\n"
        if historical_risks:
            explanation += f"WARNING: Historical metadata flags this genre for: {', '.join(historical_risks)}. "
            
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
        if historical_risks:
             suggestions.append("Address historical drop-off reasons seen on Reddit for this genre.")
            
        return {
            "decision_label": decision,
            "confidence_level": final_confidence,
            "explanation_text": explanation,
            "improvement_suggestions": suggestions,
            "failed_gates": failed_gates,
            "quality_bands": bands
        }
