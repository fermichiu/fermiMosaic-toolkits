#Step5 merge parquets
from PIL import Image, ImageDraw
import csv
import os
import shutil
os.environ["NUMEXPR_MAX_THREADS"] = "16"
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime

#common helper functions for this project, utils.py saved in the same folder
from utils import *
from utils_csv_io import *

from config import CONFIG

def get_merged_coords(p1, p2):
    (p1_x1, p1_y1), (p1_x2, p1_y1_), (p1_x2_, p1_y2), (p1_x1_, p1_y2_) = p1["coordinates"]
    (p2_x1, p2_y1), (p2_x2, p2_y1_), (p2_x2_, p2_y2), (p2_x1_, p2_y2_) = p2["coordinates"]
    
    # Horizontal merge check
    if abs(p1_y1 - p2_y1) < 1e-6 and abs(p1_y2 - p2_y2) < 1e-6:
        if abs(p1_x2 - p2_x1) < 1e-6:
            merged_x1, merged_y1 = p1_x1, p1_y1
            merged_x2, merged_y2 = p2_x2, p1_y2
        elif abs(p2_x2 - p1_x1) < 1e-6:
            merged_x1, merged_y1 = p2_x1, p2_y1
            merged_x2, merged_y2 = p1_x2, p2_y2
        else:
            return None, None
            
        new_width = merged_x2 - merged_x1
        new_height = merged_y2 - merged_y1
        aspect = new_width / new_height
        
        #if 0.75/1.1 < aspect < 4/3*1.1:
        if 0.666 < aspect < 1.501:
            orientation = "landscape" if new_width > new_height else "portrait"
            return [
                (merged_x1, merged_y1),
                (merged_x2, merged_y1),
                (merged_x2, merged_y2),
                (merged_x1, merged_y2)
            ], orientation

    # Vertical merge check
    if abs(p1_x1 - p2_x1) < 1e-6 and abs(p1_x2 - p2_x2) < 1e-6:
        if abs(p1_y2 - p2_y1) < 1e-6:
            merged_x1, merged_y1 = p1_x1, p1_y1
            merged_x2, merged_y2 = p1_x2, p2_y2
        elif abs(p2_y2 - p1_y1) < 1e-6:
            merged_x1, merged_y1 = p2_x1, p2_y1
            merged_x2, merged_y2 = p2_x2, p1_y2
        else:
            return None, None
            
        new_width = merged_x2 - merged_x1
        new_height = merged_y2 - merged_y1
        aspect = new_width / new_height
        
        # Allow aspect ratios of 4:3 (or 3:4) only
        #if 0.75/1.1 < aspect < 4/3*1.1:
        # Allow aspect ratios of 4:3 (or 3:4) and 3:2 (or 2:3)
        if (0.75/1.1 < aspect < 4/3*1.1) or (2/3/1.1 < aspect < 3/2*1.1):
            orientation = "landscape" if new_width > new_height else "portrait"
            return [
                (merged_x1, merged_y1),
                (merged_x2, merged_y1),
                (merged_x2, merged_y2),
                (merged_x1, merged_y2)
            ], orientation

    return None, None

def snap_to_grid(value, grid_size=1):
    """Snap a value to the nearest grid point."""
    return round(value / grid_size) * grid_size


def meets_max_dimensions(width, height, orientation):
    #######conditions to skip merging a pair of parquets 
    MAX_WIDTH_LANDSCAPE = CONFIG["parquet_unit_width"] * CONFIG["parquet_size_factor"] 
    MAX_HEIGHT_LANDSCAPE = (MAX_WIDTH_LANDSCAPE // 3) * 2
    MAX_WIDTH_PORTRAIT = MAX_HEIGHT_LANDSCAPE
    MAX_HEIGHT_PORTRAIT = MAX_WIDTH_LANDSCAPE
    if orientation == "landscape":
        return width <= MAX_WIDTH_LANDSCAPE and height <= MAX_HEIGHT_LANDSCAPE
    elif orientation == "portrait":
        return width <= MAX_WIDTH_PORTRAIT and height <= MAX_HEIGHT_PORTRAIT
    return False  # or True, depending on what makes sense for your context


def parquet_merge(parquets, main_image_path, ithreshold):
    main_img = Image.open(main_image_path)
    img_width, img_height = main_img.size
    merged_parquets = []
    processed = set()
    merge_count = 0
    max_sized_parquet_count = 0
    
    for i in tqdm(range(len(parquets)), desc="Merging parquets"):
        if i in processed:
            continue

        p1 = parquets[i]
        for j in range(i + 1, len(parquets)):
            if j in processed:
                continue

            p2 = parquets[j]
            merged_coords, orientation = get_merged_coords(p1, p2)
            if not merged_coords:
                continue
         
            # Snap merged coordinates to a grid
            snapped_coords = [
                (snap_to_grid(x), snap_to_grid(y)) for x, y in merged_coords
            ]

            # Check if merged parquet overlaps image boundaries
            inside_corners = sum(
                0 <= x < img_width and 0 <= y < img_height
                for x, y in snapped_coords  # Use snapped_coords here
            )
            on_the_edge_merged = 1 if inside_corners < 4 else 0

            # Clamp coordinates for cropping
            crop_x1 = max(snapped_coords[0][0], 0)  # Use snapped_coords here
            crop_y1 = max(snapped_coords[0][1], 0)  # Use snapped_coords here
            crop_x2 = min(snapped_coords[2][0], img_width)  # Use snapped_coords here
            crop_y2 = min(snapped_coords[2][1], img_height)  # Use snapped_coords here

            if crop_x1 >= crop_x2 or crop_y1 >= crop_y2:
                continue

            # Validate area conservation
            p1_area = (p1["coordinates"][1][0] - p1["coordinates"][0][0]) * \
                      (p1["coordinates"][2][1] - p1["coordinates"][0][1])
            p2_area = (p2["coordinates"][1][0] - p2["coordinates"][0][0]) * \
                      (p2["coordinates"][2][1] - p2["coordinates"][0][1])
            merged_area = (snapped_coords[1][0] - snapped_coords[0][0]) * \
                          (snapped_coords[2][1] - snapped_coords[0][1])  # Use snapped_coords here

            if abs((p1_area + p2_area) - merged_area) > 1e-6:
                continue

            # Color distance check
            color_dist = sum((a - b)**2 for a, b in zip(p1["average_color"], p2["average_color"]))
            if color_dist > 3 * (ithreshold ** 2):
                continue

            # Crop and calculate colors
            cropped = main_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            avg_color = average_colour_n_fallback(cropped)
            width_c, height_c = cropped.size
         
            if width_c == 0 or height_c == 0:
                continue

            #check if its dimension great than the minimum says 12x8 (or 8x12 portrait) if not skip splitting
            orientation_c = "landscape" if width_c > height_c else "portrait"
            if not meets_max_dimensions(width_c, height_c, orientation_c):
                max_sized_parquet_count += 1
                continue
            
            # Quadrant colors
            tl = cropped.crop((0, 0, width_c // 2, height_c // 2))
            tr = cropped.crop((width_c // 2, 0, width_c, height_c // 2))
            bl = cropped.crop((0, height_c // 2, width_c // 2, height_c))
            br = cropped.crop((width_c // 2, height_c // 2, width_c, height_c))

            merged_parquet = {
                "coordinates": snapped_coords,  # Use snapped_coords here
                "average_color": avg_color,
                "on_the_edge": on_the_edge_merged,
                "orientation": orientation,
                "priority": max(p1["priority"], p2["priority"])*2,
                "top_left_color": average_colour_n_fallback(tl),
                "top_right_color": average_colour_n_fallback(tr),
                "bottom_left_color": average_colour_n_fallback(bl),
                "bottom_right_color": average_colour_n_fallback(br)
            }

            processed.add(i)
            processed.add(j)
            merged_parquets.append(merged_parquet)
            merge_count += 1
            break

    # Add unprocessed parquets
    for i in range(len(parquets)):
        if i not in processed:
            merged_parquets.append(parquets[i])

    main_img.close()
    print(f"Merged {merge_count} pairs of parquets")
    print(f"Aborted merging for {max_sized_parquet_count} pairs at the maximum dimensions")
    return merged_parquets


def snap_to_grid(value, grid_size=1):
    """Snap a value to the nearest grid point."""
    return round(value / grid_size) * grid_size


def main():
    setup_logging(CONFIG["log_file"])
    
    start_time = datetime.now()
    log_message(f"Step5 - merging parquets threshold:{CONFIG["merge_diff"]}... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}" )

    base_path, ext = os.path.splitext(CONFIG["parquets_csv_path"])
    masking_jpg_path = f"{base_path}.jpg"
    csv_backup_path = f"{base_path}_last{ext}"
    masking_jpg_backup_path = f"{base_path}_last.jpg"

    backup_file(CONFIG["parquets_csv_path"], csv_backup_path)
    backup_file(masking_jpg_path, masking_jpg_backup_path)

    
    try:
        parquets = read_parquets_csv(CONFIG["parquets_csv_path"])
        merged = parquet_merge(parquets, CONFIG["image_path"], CONFIG["merge_diff"])
        
        current_time = datetime.now().strftime("@%H:%M:%S @%Y-%m-%d ")
        print(f"Parquet index file of {len(merged)} saving...{current_time}")

        
        # Refactored version using save_parquet_csv
        save_parquet_csv(merged, CONFIG["parquets_csv_path"])         

                
        # Create visualization
        try:
            img = Image.open(CONFIG["image_path"]).convert("RGB")
            draw = ImageDraw.Draw(img)
            for p in merged:
                (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p["coordinates"]
                draw.rectangle([x1, y1, x3, y3], outline="green", width=2)
            img.save(masking_jpg_path, 'JPEG', quality=30)
            print(f"Masking visualization saved to: {masking_jpg_path}")
            plt.figure(figsize=(CONFIG["plt_width"], CONFIG["plt_height"]))
            plt.imshow(img)
            plt.axis('on')
            plt.show()
        except Exception as e:
            print(f"Visualization error: {str(e)}")
            
    except Exception as e:
        print(f"Error in parquet_merge execution: {str(e)}")
        raise
        
    end_time = datetime.now()
    log_message(f"Step5 - merging parquets... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===" )

if __name__ == "__main__":
    main()


