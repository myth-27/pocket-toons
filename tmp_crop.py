from PIL import Image

def crop_avatar():
    img_path = r"C:\Users\Nitin\.gemini\antigravity\brain\e006fe49-dc6f-450f-9c21-4899ec357a96\anime_pirate_boy_mascot_sheet_1772868445554.png"
    out_path = r"c:\Users\Nitin\Documents\pocket_toons\assets\avatar.png"
    
    img = Image.open(img_path).convert("RGBA")
    
    # Needs to cut off the bottom entirely since we captured the blue frame below it.
    # We used: box = (30, 10, 270, 250)
    # The blue panel is at the very bottom, let's just make the bottom coordinate y=230
    box = (30, 10, 270, 230)
    cropped = img.crop(box)
    
    # Make white background transparent
    datas = cropped.getdata()
    new_data = []
    
    threshold = 245
    
    for item in datas:
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            # Change to transparent
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    cropped.putdata(new_data)
    
    # Save it out
    cropped.save(out_path, "PNG")
    print(f"Saved avatar to {out_path}")

if __name__ == "__main__":
    crop_avatar()
