import os
import sys

# Test script for Phase 4 video pipeline without needing the UI
from models.preview_generator import generate_preview_brief
from models.video_renderer import render_preview_video

def main():
    print("Testing Video Generator Pipeline...")
    features = {
        "hook_summary": "A high stakes battle in a falling elevator.",
        "core_tension": "Survival versus betrayal.",
        "cliffhanger_energy": "Extreme ending with a gunshot."
    }
    
    print("\n1. Generating brief via Gemini API fallback (Mocked inside if no key)...")
    brief = generate_preview_brief(features, genre="Action", emotion_band="HIGH")
    
    print("\nBrief Structure:")
    for shot in brief.get('shot_list', []):
        print(f"Shot {shot['second']}: {shot['visual']} | Motion: {shot['motion']}")
        
    print(f"\n2. Rendering video to output.mp4...")
    output_path = render_preview_video(brief, "output.mp4")
    
    if os.path.exists(output_path):
        print(f"\nSUCCESS Video successfully rendered at {output_path}")
        print(f"File size: {os.path.getsize(output_path)} bytes")
    else:
        print("\nFAILED Video rendering failed.")

if __name__ == "__main__":
    main()
