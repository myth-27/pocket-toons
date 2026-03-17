"""
Preview Generator - Visual Briefs and Keyframes
Uses Gemini 2.5 Flash for briefs and Imagen 3 for keyframes.
"""

import json
import logging
from pathlib import Path

FALLBACK_BRIEF = {
    "keyframe_prompt": "Dramatic anime girl floating above rooftop edge, city lights below, shocked expression, dark coat, cold blue moonlight, cinematic vertical 9:16 portrait orientation, webtoon art style",
    "title_text": "SHE DEFIED GRAVITY",
    "subtitle_text": "Some are born different",
    "mood": "intense",
    "color_grade": "cold_blue",
    "camera_motion": "zoom",
    "music_mood": "epic"
}

def generate_visual_brief(script_text: str, gemini_scores: dict, api_key: str) -> dict:
    """
    Calls Gemini 2.5 Flash to generate a visual brief JSON.
    """
    sys_prompt = """You are a mobile drama visual director for DramaBox and PocketToons.
Read this script and return ONLY a valid JSON object — no preamble, no markdown fences.

{
  "keyframe_prompt": "<detailed Imagen 3 prompt — the single most dramatic moment in the script. Include: character appearance, facial emotion, body language, setting, lighting mood, cinematic angle, vertical 9:16 portrait composition, webtoon anime art style>",
  "title_text": "<3-5 word dramatic hook — ALL CAPS — e.g. SHE NEVER FELL DOWN>",
  "subtitle_text": "<1 teaser line max 8 words — e.g. Some gifts come with a price>",
  "mood": "<one of: intense / romantic / mysterious / triumphant / dark / hopeful>",
  "color_grade": "<one of: golden_hour / cold_blue / deep_shadow / neon_night / warm_sunset>",
  "camera_motion": "<one of: zoom / slideLeft / slideRight / static>",
  "music_mood": "<one of: epic / romantic / suspense / uplifting / dark>"
}"""
    
    # We use a raw request wrapper from the existing script evaluator since the prompt specifies temperature and strict JSON.
    try:
        import google.generativeai as genai
        # Avoid globals by re-configuring locally if needed, assuming caller initialized.
        genai.configure(api_key=api_key)
        
        # Use simple GenerationConfig to enforce JSON structure
        model = genai.GenerativeModel('gemini-2.5-flash',
            system_instruction=sys_prompt,
            generation_config={"temperature": 0.3}
        )
        
        input_text = f"SCRIPT:\n{script_text[:15000]}\n"
        response = model.generate_content(input_text)
        
        raw = response.text
        # Strip markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.replace("```", "").strip()
            
        data = json.loads(raw)
        
        # Need to ensure all keys exist
        for key in FALLBACK_BRIEF.keys():
            if key not in data:
                data[key] = FALLBACK_BRIEF[key]
                
        return data

    except Exception as e:
        print(f"Failed to generate visual brief: {e}")
        return FALLBACK_BRIEF

def generate_keyframe(keyframe_prompt: str, script_id: str, api_key: str) -> str:
    """
    Calls Imagen 3 with keyframe_prompt.
    Saves PNG to data/previews/{script_id}_keyframe.png
    """
    import os
    from google import genai
    from google.genai import types
    
    out_dir = Path("data/previews")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{script_id}_keyframe.png"
    
    if out_path.exists():
        return str(out_path.absolute())
        
    try:
        # Use python SDK for Gemini
        client = genai.Client(api_key=api_key)
        
        # Always append mandatory style modifiers
        final_prompt = f"{keyframe_prompt}, vertical 9:16 portrait orientation, webtoon anime art style, cinematic mobile drama, dramatic lighting"
        
        # Use Imagen 3 endpoint
        result = client.models.generate_images(
            model='imagen-3.0-generate-001',
            prompt=final_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="9:16"
            )
        )
        
        if result.generated_images:
            image_bytes = result.generated_images[0].image.image_bytes
            with open(out_path, "wb") as f:
                f.write(image_bytes)
            return str(out_path.absolute())
            
        return None
        
    except Exception as e:
        print(f"Failed to generate keyframe via Imagen 3: {e}")
        return None
