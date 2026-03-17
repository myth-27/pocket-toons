import os
import random
from pathlib import Path
import logging

# Ensure moviepy uses ImageMagick if needed for TextClip, though we might just simulate text overlays
# if ImageMagick is not installed on the system to prevent crashes.
try:
    from moviepy import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips, vfx
except ImportError as e:
    logger.warning(f"Moviepy import warning (v2 syntax): {e}. Falling back to old syntax.")
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips, vfx
    except ImportError:
        pass

logger = logging.getLogger(__name__)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def render_preview_video(brief: dict, output_path: str) -> str:
    """
    Renders an 8-second abstract video based on the Gemini JSON brief using MoviePy.
    """
    OUTPUT_FILE = Path(output_path)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        from moviepy import VideoClip, TextClip, CompositeVideoClip, concatenate_videoclips, vfx
        import numpy as np
    except ImportError:
        try:
            from moviepy.editor import VideoClip, TextClip, CompositeVideoClip, concatenate_videoclips, vfx
            import numpy as np
        except ImportError:
            logger.error("MoviePy or Numpy is not installed. Video cannot be rendered.")
            return ""
        
    colors = brief.get("color_palette", ["#000000", "#333333", "#666666"])
    scenes = brief.get("scenes", [])
    
    # Calculate total duration from scenes, default to 8s if missing
    duration = sum(s.get("duration", 2) for s in scenes) if scenes else 8

    # We might not have a global text overlay anymore, scenes have their own text
    # But for simplicity, we can extract the last text overlay if it exists
    text_overlay_str = next((s.get("text") for s in reversed(scenes) if s.get("text") and s.get("text").lower() != "none"), "CONCEPT PREVIEW")
    
    # --- GOOGLE VEO API INTEGRATION ---
    try:
        import os
        from google import genai
        from google.genai import types
        import time
        
        if os.environ.get("GOOGLE_API_KEY"):
            logger.info("GOOGLE_API_KEY detected. Attempting actual Google Veo Video Generation...")
            client = genai.Client()
            
            # Combine the scenes into one cohesive prompt for Veo
            scene_descriptions = [
                f"Scene {i+1} ({s.get('duration', 2)}s): {s.get('visual', '')}, Camera: {s.get('camera', '')}, Lighting: {s.get('lighting', '')}." 
                for i, s in enumerate(scenes)
            ]
            full_prompt = "Cinematic trailer with characters. " + " ".join(scene_descriptions)
            
            operation = client.models.generate_videos(
                model='veo-2.0-generate-001',
                prompt=full_prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    person_generation="ALLOW_ALL"
                )
            )
            
            logger.info("Veo operation started. Waiting for completion...")
            while not operation.done:
                time.sleep(5) # Poll every 5 seconds
                if hasattr(client.models, 'get_generate_videos_operation'):
                    operation = client.models.get_generate_videos_operation(operation.name)
                else:
                    break
                    
            if hasattr(operation, 'result') and operation.result and hasattr(operation.result, 'video'):
                video_bytes = operation.result.video.video_bytes
                with open(OUTPUT_FILE, 'wb') as f:
                    f.write(video_bytes)
                logger.info("Google Veo generated the video successfully.")
                return str(OUTPUT_FILE)
            else:
                logger.warning("Veo operation completed but no bytes were returned. Falling back to local python renderer.")
                
    except Exception as e:
        logger.warning(f"Google Veo API generation failed: {e}. Falling back to Python Ken Burns animator.")
    # --- END GOOGLE VEO API INTEGRATION ---
    
    # Ensure exactly 3 colors
    while len(colors) < 3:
        colors.append("#111111")
        
    clips = []
    
    import urllib.request
    from PIL import Image
    
    for i, shot in enumerate(scenes):
        shot_duration = shot.get("duration", 2)
        color_hex = colors[i % len(colors)]
        try:
            r, g, b = hex_to_rgb(color_hex)
        except:
            r, g, b = (10, 10, 10)
            
        motion = shot.get("camera", "").lower()
        lighting = shot.get("lighting", "").lower()
        
        # Download a random placeholder image per scene based on text hash
        visual_text = shot.get("visual", f"scene_{i}")
        seed = abs(hash(visual_text)) % 10000
        img_path = f"temp_scene_{i}.jpg"
        
        try:
            # Get a 1280x720 image to allow room for panning (output is 800x450)
            urllib.request.urlretrieve(f"https://picsum.photos/seed/{seed}/1280/720", img_path)
            pil_img = Image.open(img_path).convert('RGB')
        except Exception as e:
            logger.warning(f"Failed to fetch image, using solid color: {e}")
            pil_img = Image.new('RGB', (1280, 720), color=(r,g,b))
            
        img_array = np.array(pil_img)
        img_h, img_w, _ = img_array.shape
        out_w, out_h = 800, 450
        
        # Generative function for camera motion (Ken Burns effect)
        def make_frame(t):
            progress = t / shot_duration if shot_duration > 0 else 0
            
            # Determine crop window based on 'camera' parameter
            if "pan" in motion:
                # Pan left to right
                start_x = 0
                end_x = img_w - out_w
                current_x = int(start_x + (end_x - start_x) * progress)
                current_y = (img_h - out_h) // 2
                current_w = out_w
                current_h = out_h
            elif "zoom out" in motion:
                # Zoom out: start with a tight crop in center, expand out
                start_scale = 0.6
                end_scale = 1.0
                scale = start_scale + (end_scale - start_scale) * progress
                current_w = int(out_w * scale)
                current_h = int(out_h * scale)
                current_x = (img_w - current_w) // 2
                current_y = (img_h - current_h) // 2
            else: 
                # Zoom in (default)
                start_scale = 1.0
                end_scale = 0.6
                scale = start_scale + (end_scale - start_scale) * progress
                current_w = max(int(out_w * scale), 10)
                current_h = max(int(out_h * scale), 10)
                current_x = (img_w - current_w) // 2
                current_y = (img_h - current_h) // 2
                
            # Bounds check
            current_x = max(0, min(current_x, img_w - current_w))
            current_y = max(0, min(current_y, img_h - current_h))
            
            # Slice the array
            cropped = img_array[current_y:current_y+current_h, current_x:current_x+current_w]
            
            # Resize via PIL for smooth scaling to out_w x out_h
            frame_img = Image.fromarray(cropped).resize((out_w, out_h), Image.Resampling.LANCZOS)
            frame = np.array(frame_img).astype(np.float32)
                
            # Apply simple lighting (Color Tint based on palette)
            tint = np.array([r, g, b], dtype=np.float32)
            frame = frame * 0.7 + tint * 0.3
            
            # Flicker/Strobe
            if "strobe" in lighting or "flicker" in lighting:
                if int(t * 15) % 2 == 0:
                    frame = frame * 0.2
                    
            # Fade to black if requested
            if "fade to black" in lighting:
                fade = max(0, 1.0 - (t / shot_duration))
                frame = frame * fade

            return frame.astype(np.uint8)
            
        clip = VideoClip(make_frame, duration=shot_duration)
        clips.append(clip)
        
    if not clips:
        # Fallback empty clip
        def empty_frame(t): return np.zeros((450, 800, 3), dtype=np.uint8)
        clips.append(VideoClip(empty_frame, duration=duration))

    # Stitch clips with crossfades
    final_sequence = concatenate_videoclips(clips, method="compose")
    
    # Add Text Overlay
    # Note: TextClip requires ImageMagick. If not installed on Windows, it fails.
    # We wrap in a try-except to fallback to no text if ImageMagick is missing.
    try:
        # In moviepy v2, TextClip handles fonts differently. Try basic syntax first.
        txt_clip = TextClip(text=text_overlay_str, font_size=40, color='white', font='Arial', method='label')
        txt_clip = txt_clip.with_position('center').with_duration(duration)
        txt_clip = txt_clip.with_effects([vfx.CrossFadeIn(1.0), vfx.CrossFadeOut(1.0)])
        final_video = CompositeVideoClip([final_sequence, txt_clip])
    except Exception as e:
        logger.warning(f"Text overlay skipped (v2 syntax adjustment needed or ImageMagick missing): {e}")
        final_video = final_sequence
        
    # Write to file (silently, low fps for speed)
    logger.info(f"Rendering preview video to {output_path}...")
    final_video.write_videofile(
        str(OUTPUT_FILE),
        fps=15, 
        codec="libx264", 
        audio=False, 
        logger=None # Disable MoviePy progress bar in API backend
    )
    
    return str(OUTPUT_FILE)
