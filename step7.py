#Step7 pasting mosaic
import os
os.environ["NUMEXPR_MAX_THREADS"] = "16"
import csv
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime
import math
import random
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = 268435456  # 16,384 x 16,384 pixels (268 million pixels)
# Or disable the limit entirely (not recommended for untrusted images):
# Image.MAX_IMAGE_PIXELS = None

#import imageio  # NEW: Import imageio
#import numpy as np  # NEW: Import numpy

#common helper functions for this project, utils.py saved in the same folder
from utils import *
from utils_csv_io import *
from config import CONFIG


def get_cropped_tessera_quadrant_colors(tessera):
    """Calculate quadrant colors for a cropped tessera image."""
    width, height = tessera.size
    colors = {}
    
    # Define quadrants and their coordinates
    quadrants = {
        'top_left': (0, 0, width//2, height//2),
        'top_right': (width//2, 0, width, height//2),
        'bottom_left': (0, height//2, width//2, height),
        'bottom_right': (width//2, height//2, width, height)
    }
    
    for name, coords in quadrants.items():
        quadrant = tessera.crop(coords)
        colors[name] = calculate_average_color(quadrant)
    
    return colors

def calculate_color_distance(color1, color2):
    """Calculate squared Euclidean distance between two RGB colors."""
    return sum((c1 - c2)**2 for c1, c2 in zip(color1, color2))

def get_best_transform(candidate, current_colors):
    """Determine the best transformation for the tessera based on color distances."""
    parquet_colors = {
        'top_left': candidate['parquet_colors']['top_left'],
        'top_right': candidate['parquet_colors']['top_right'],
        'bottom_left': candidate['parquet_colors']['bottom_left'],
        'bottom_right': candidate['parquet_colors']['bottom_right']
    }
    
    transformations = [
        {
            'name': 'original',
            'method': None,
            'color_map': current_colors
        },
        {
            'name': 'flip_horizontal',
            'method': lambda img: img.transpose(Image.FLIP_LEFT_RIGHT),
            'color_map': {
                'top_left': current_colors['top_right'],
                'top_right': current_colors['top_left'],
                'bottom_left': current_colors['bottom_right'],
                'bottom_right': current_colors['bottom_left']
            }
        },
        {
            'name': 'flip_vertical',
            'method': lambda img: img.transpose(Image.FLIP_TOP_BOTTOM),
            'color_map': {
                'top_left': current_colors['bottom_left'],
                'top_right': current_colors['bottom_right'],
                'bottom_left': current_colors['top_left'],
                'bottom_right': current_colors['top_right']
            }
        },
        {
            'name': 'rotate_180',
            'method': lambda img: img.rotate(180),
            'color_map': {
                'top_left': current_colors['bottom_right'],
                'top_right': current_colors['bottom_left'],
                'bottom_left': current_colors['top_right'],
                'bottom_right': current_colors['top_left']
            }
        }
    ]

    best_transform = None
    min_distance = float('inf')
    for transform in transformations:
        distance = sum(
            calculate_color_distance(transform['color_map'][q], parquet_colors[q])
            for q in ['top_left', 'top_right', 'bottom_left', 'bottom_right']
        )
        if distance < min_distance:
            min_distance = distance
            best_transform = transform
    
    return best_transform

def rotate_or_flip_tessera(candidate, tessera):
    """Optimize tessera orientation by applying transformations to minimize color distance."""
    current_colors = get_cropped_tessera_quadrant_colors(tessera)
    best_transform = get_best_transform(candidate, current_colors)
    
    if best_transform and best_transform['method']:
        return best_transform['method'](tessera)
    return tessera

def prepare_tessera_image(candidate, tessera_path):
    """Load, orient, crop and resize tessera image to match parquet dimensions."""
    tessera = Image.open(tessera_path).convert('RGB')
    tessera_width, tessera_height = tessera.size
    
    # Handle orientation first
    candidate_is_landscape = candidate['orientation'] == "landscape"
    is_portrait = tessera_height > tessera_width
    
    if candidate_is_landscape and is_portrait:
        tessera = tessera.rotate(90, expand=True)
    elif not candidate_is_landscape and not is_portrait:
        tessera = tessera.rotate(90, expand=True)
    
    # Crop and resize to match parquet dimensions
    x1, y1 = candidate['coords'][0]
    x2, y2 = candidate['coords'][2]
    width, height = x2 - x1, y2 - y1
    parquet_aspect = width / height
    
    tessera_width, tessera_height = tessera.size
    tessera_aspect = tessera_width / tessera_height
    
    if tessera_aspect > parquet_aspect:
        new_width = int(tessera_height * parquet_aspect)
        left = (tessera_width - new_width) // 2
        top, right, bottom = 0, left + new_width, tessera_height
    else:
        new_height = int(tessera_width / parquet_aspect)
        left, top = 0, (tessera_height - new_height) // 2
        right, bottom = tessera_width, top + new_height
    
    return tessera.crop((left, top, right, bottom)).resize((width, height))


def create_mosaic(candidates_index_path, output_path):
    """Create final mosaic from candidates index and generate an animated GIF of the process."""    
    candidates = read_candidates_csv(candidates_index_path)
    if not candidates:
        print("Failed to load candidates index.")
        return False

    # Determine mosaic dimensions
    coords = [c['coords'][0] for c in candidates] + [c['coords'][2] for c in candidates]
    min_x = min(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_x = max(c[0] for c in coords)
    max_y = max(c[1] for c in coords)
    
    mosaic_width = max_x - min_x
    mosaic_height = max_y - min_y
    mosaic = Image.new('RGB', (mosaic_width, mosaic_height))
    
    # Prepare for animated GIF (it is 1/CONFIG["anime_size_downsize"] the output mosaic)
    gif_width = mosaic_width // CONFIG["anime_size_downsize"]
    gif_height = mosaic_height // CONFIG["anime_size_downsize"]
    gif_frames = []

    #frame_interval = 1  # Changed to 1 to capture every tessera placement
    #frame_interval = max(1, len(candidates) // 400)  # Aim for about 400 frames
    frame_interval = max(1, len(candidates) // CONFIG["anime_fps"])

    total_score = 0.0
    total = len(candidates)
    
    for i, candidate in enumerate(tqdm(candidates, desc="Creating mosaic")):
        try:
            tessera = prepare_tessera_image(candidate, candidate['candidate']['image_path'])
            tessera = rotate_or_flip_tessera(candidate, tessera)
            
            x1, y1 = candidate['coords'][0]
            paste_pos = (x1 - min_x, y1 - min_y)
            mosaic.paste(tessera, paste_pos)
            
            # Add frame to GIF at specified intervals or for the last candidate
            if i % frame_interval == 0 or i == len(candidates) - 1:
                # Create downscaled version for GIF
                gif_frame = mosaic.resize((gif_width, gif_height), Image.Resampling.LANCZOS)
                gif_frames.append(gif_frame)
            
            tessera.close()
            total_score += candidate['candidate']['score']
            
        except Exception as e:
            print(f"\nError processing {candidate['candidate']['image_path']}: {str(e)}")

   
    # Save the final mosaic
    mosaic.save(output_path, 'JPEG', quality=CONFIG["mosaic_jpg_quality"])
    print(f"\nMosaic saved to: {output_path}")

    if CONFIG["mosaic_anime"]:
        print(f"Mosaic animation saving...")
        # Save the animated GIF if we collected frames
        if gif_frames:
            gif_path = os.path.splitext(output_path)[0] + "_progress.gif"
            # Save first frame for longer duration

            # NEW: Wrap the GIF-saving process in a tqdm progress bar
            with tqdm(total=len(gif_frames), desc="Saving GIF") as pbar:
                gif_frames[0].save(
                    gif_path,
                    save_all=True,
                    append_images=gif_frames[1:],
                    duration=250,  # milliseconds per frame
                    loop=0,  # infinite loop
                    optimize=True,
                    disposal=2  # CHANGED: Added disposal parameter for proper frame handling
                )
                pbar.update(len(gif_frames))  # CHANGED: Update progress bar after saving all frames
                                 
            log_message(f"Mosaic animation saved to: {gif_path}")

    # Calculate and print scores
    max_score = math.sqrt(195075)  # 3*(255^2)
    avg_score = math.sqrt(total_score)/len(candidates)
    normalized_score = 10*math.log10(avg_score / max_score)
    
    log_message(f"Colour Variance = {avg_score:.2f}")
    log_message(f"Normalized Mosaic Noise: {normalized_score:.2f} dB")

    return True



def main():
    setup_logging(CONFIG["log_file"])
 
    start_time = datetime.now()
    log_message(f"Step7 - mosaicing... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}" )
    
    candidates_index_path = CONFIG["candidates_output_path"]
     
    if os.path.exists(candidates_index_path):
        print("Starting mosaic composition...")
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"mosaic_{current_time}.jpg"
        output_path_filename = CONFIG["output_path"] + "\\" + output_filename
        success = create_mosaic(candidates_index_path, output_path_filename)
        if success:
            current_time = datetime.now().strftime("@%H:%M:%S @%Y-%m-%d ")
            print(f"Mosaic composition completed successfully {current_time}")
            img = Image.open(output_path_filename)
            plt.figure(figsize=(CONFIG["plt_width"], CONFIG["plt_height"]))
            plt.imshow(img)
            plt.axis('on')
            plt.show()
    else:
        print("Candidates index not found. Skipping final composition.")

    end_time = datetime.now()
    log_message(f"Step7 - mosaicing... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===" )
    
if __name__ == "__main__":
    main()






