#!/usr/bin/env python3
"""
Remove white background from PNGs and crop to content.
"""

from PIL import Image
import os

INPUT_DIR = "/mnt/c/png/with_bg"
OUTPUT_DIR = "/mnt/c/png/nobg"

# White threshold - pixels with R,G,B all above this are considered "white"
WHITE_THRESHOLD = 240

def remove_white_bg_and_crop(input_path, output_path):
    """Remove white background and crop to content."""
    img = Image.open(input_path).convert("RGBA")
    pixels = img.load()
    
    width, height = img.size
    
    # Make white pixels transparent
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # If pixel is white-ish, make it transparent
            if r >= WHITE_THRESHOLD and g >= WHITE_THRESHOLD and b >= WHITE_THRESHOLD:
                pixels[x, y] = (r, g, b, 0)
    
    # Get bounding box of non-transparent pixels
    bbox = img.getbbox()
    
    if bbox:
        # Add a small margin (optional)
        margin = 2
        left = max(0, bbox[0] - margin)
        top = max(0, bbox[1] - margin)
        right = min(width, bbox[2] + margin)
        bottom = min(height, bbox[3] + margin)
        
        img = img.crop((left, top, right, bottom))
    
    img.save(output_path, "PNG")
    print(f"Processed: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")


def main():
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Process all PNGs in input directory
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".png"):
            input_path = os.path.join(INPUT_DIR, filename)
            output_path = os.path.join(OUTPUT_DIR, f"card__{filename}")
            remove_white_bg_and_crop(input_path, output_path)
    
    print("Done!")


if __name__ == "__main__":
    main()

