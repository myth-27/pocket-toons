import pandas as pd
from pathlib import Path
from datetime import datetime
import os

FEEDBACK_FILE = Path("data/feedback/human_feedback.csv")

class FeedbackMemory:
    def __init__(self):
        self.file_path = FEEDBACK_FILE
        self._ensure_file()
        
    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(columns=[
                'script_id', 'genre', 'ai_decision', 'human_decision', 'disagreement',
                'fingerprint', 'failed_gates', 'emotion_band', 'addiction_band', 'risk_band', 
                'notes', 'timestamp'
            ])
            df.to_csv(self.file_path, index=False)
            
    def _create_fingerprint(self, genre, emotion, addiction, risk):
        return f"{genre}|{emotion}|{addiction}|{risk}"
        
    def record_feedback(self, script_id, genre, ai_decision, human_decision, failed_gates, emotion_band, addiction_band, risk_band, notes=""):
        disagreement = ai_decision != human_decision
        fingerprint = self._create_fingerprint(genre, emotion_band, addiction_band, risk_band)
        
        new_row = {
            'script_id': script_id,
            'genre': genre,
            'ai_decision': ai_decision,
            'human_decision': human_decision,
            'disagreement': disagreement,
            'fingerprint': fingerprint,
            'failed_gates': " | ".join(failed_gates) if failed_gates else "Passed",
            'emotion_band': emotion_band,
            'addiction_band': addiction_band,
            'risk_band': risk_band,
            'notes': notes,
            'timestamp': datetime.now().isoformat()
        }
        
        df = pd.read_csv(self.file_path)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(self.file_path, index=False)
        
    def get_historical_warnings(self, genre, failed_gates, emotion_band, addiction_band, risk_band):
        """Checks if this profile was historically downgraded by humans."""
        fingerprint = self._create_fingerprint(genre, emotion_band, addiction_band, risk_band)
        gates_str = " | ".join(failed_gates) if failed_gates else "Passed"
        
        try:
            df = pd.read_csv(self.file_path)
            if df.empty:
                return []
                
            # Find exact fingerprint matches where human downgraded the AI (i.e. AI=GREENLIGHT/PILOT, Human=DEFER/REWORK)
            downgrades = df[
                (df['fingerprint'] == fingerprint) & 
                (df['disagreement'] == True) &
                (df['human_decision'].isin(['DEFER', 'REWORK'])) &
                (df['ai_decision'].isin(['GREENLIGHT', 'PILOT']))
            ]
            
            warnings = []
            if len(downgrades) > 0:
                most_common = downgrades['human_decision'].mode()[0]
                warnings.append(f"Similar {emotion_band} Emotion / {addiction_band} Addiction profiles in {genre} were historically downgraded to {most_common} by humans.")
                
            # Gate specific warnings
            if gates_str != "Passed":
                gate_downgrades = df[
                    (df['failed_gates'] == gates_str) & 
                    (df['human_decision'] == 'REWORK')
                ]
                if len(gate_downgrades) > 0:
                    warnings.append(f"Scripts failing [{gates_str}] strictly result in REWORK from human reviewers.")
                    
            return warnings
            
        except Exception:
            return []
