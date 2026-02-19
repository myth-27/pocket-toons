from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models.script_feature_extractor import extract_script_features
from models.genre_comparator import GenreComparator
from models.decision_engine import DecisionEngine

app = FastAPI()

# Data Models
class ScriptRequest(BaseModel):
    script_text: str
    genre: str

class DecisionResponse(BaseModel):
    features: dict
    decision: dict
    genre_comparison: dict

# Initialize Components
feature_extractor = extract_script_features # Function
comparator = GenreComparator() # Class instance, loads profiles
engine = DecisionEngine()

@app.post("/evaluate-script", response_model=DecisionResponse)
async def evaluate_script(request: ScriptRequest):
    try:
        # 1. Extract Features
        features = feature_extractor(request.script_text, request.genre)
        
        # 2. Compare to Genre
        comparison = comparator.compare(features, request.genre)
        
        # 3. Decision
        # We need structured feedback from comparator not just raw comparison dict
        # The comparator needs a 'generate_feedback' method or similar logic
        # My previous genre_comparator implementation had logic but returned dict?
        # Let's check genre_comparator behavior.
        # It returns a comparison dict then needs manual interpretation?
        # No, I implemented `generate_feedback(comparison, features, genre)` in previous step.
        # Wait, I implemented `GenreComparator` with `compare` and `generate_feedback`?
        # Let's use it.
        
        feedback = comparator.generate_feedback(comparison, features, request.genre)
        
        # 4. Engine Decision
        decision = engine.evaluate(feedback, features) # The engine logic I wrote takes feedback dict
        
        return {
            "features": features,
            "decision": decision,
            "genre_comparison": feedback
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
