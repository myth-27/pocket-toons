from models.decision_engine import DecisionEngine
from models.feedback_memory import FeedbackMemory

print("1. Recording a historical human downgrade...")
fm = FeedbackMemory()
# Simulate a script that AI thought was GREENLIGHT but Human said REWORK due to bad hooks
fm.record_feedback(
    script_id="test_001",
    genre="fantasy",
    ai_decision="GREENLIGHT",
    human_decision="REWORK",
    failed_gates=[],
    emotion_band="HIGH",
    addiction_band="MEDIUM",
    risk_band="LOW",
    notes="The hook was actually extremely generic despite the numbers."
)

print("2. Simulating a new script with identical bands...")
# Construct features that lead to HIGH emotion, MEDIUM addiction, LOW risk
# Strengths: Exceptional Emotional Intensity -> Emotion = HIGH
# No Fast Pacing -> Addiction = MEDIUM
# Weaknesses: None -> Risk = LOW

features = {}
comparison = {
    'strengths_vs_genre': ["Exceptional Emotional Intensity"],
    'weaknesses_vs_genre': [],
    'missing_common_traits': [],
    'historical_risks': []
}

engine = DecisionEngine()
res = engine.evaluate(comparison, features, genre="fantasy", genre_confidence="High")

print("\n--- AI EVALUATION ---")
print("Decision:", res['decision_label'])
print("Explanation:", res['explanation_text'])
print("Bands:", res['quality_bands'])
