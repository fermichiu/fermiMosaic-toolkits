# step4 split parquets
import os
os.environ["NUMEXPR_MAX_THREADS"] = "16"
import shutil
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
import csv
from datetime import datetime
import math
import random
from tqdm import tqdm

#common helper functions for this project, utils.py saved in the same folder
from utils import *
from utils_csv_io import *
from config import CONFIG

def snap_to_grid(value, grid_size=1):
    """Snap a value to the nearest grid point."""
    return round(value / grid_size) * grid_size

def meets_min_dimensions(width, height, orientation):
    MIN_WIDTH_LANDSCAPE = 4*CONFIG["parquet_unit_width"]   #says 24
    MIN_HEIGHT_LANDSCAPE = 2*(MIN_WIDTH_LANDSCAPE//3)      #says 16
    MIN_WIDTH_PORTRAIT = MIN_HEIGHT_LANDSCAPE
    MIN_HEIGHT_PORTRAIT = MIN_WIDTH_LANDSCAPE
    if orientation == "landscape":
        return width >= MIN_WIDTH_LANDSCAPE and height >= MIN_HEIGHT_LANDSCAPE
    elif orientation == "portrait":
        return width >= MIN_WIDTH_PORTRAIT and height >= MIN_HEIGHT_PORTRAIT
    return False  # or True, depending on what makes sense for your context


def parquet_split(parquets, main_image_path, ithres):
    try:
        main_img = Image.open(main_image_path)
        img_width, img_height = main_img.size
        updated_parquets = []
        split_count = 0
        min_sized_parquet_count = 0
        for parquet in tqdm(parquets, desc="Splitting parquets"):

            # Split logic with edge handling
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = parquet["coordinates"]
            original_width = x2 - x1
            original_height = y3 - y1
            
            #check if its dimension great than the minimum says 12x8 (or 8x12 portrait) if not skip splitting
            if not meets_min_dimensions(original_width, original_height, parquet["orientation"]):
                updated_parquets.append(parquet)
                min_sized_parquet_count +=1
                continue

            # **New Aspect Ratio Check**     
            #aspect_ratio = original_width / original_height    #it is a float?????
            #if aspect_ratio not in [1.5, 2/3]:  # 3:2 or 2:3   #better checking needed.... 
            #    updated_parquets.append(parquet)
            #    continue

            aspect_ratio = original_width / original_height 
            accepted_ratios = (3/2, 2/3)
            tolerance = 1e-2                #relative tolerance
            if not any(math.isclose(aspect_ratio, target, rel_tol=tolerance) for target in accepted_ratios):
                updated_parquets.append(parquet)
                continue

           
            # Existing color variation check
            tl = parquet["top_left_color"]
            tr = parquet["top_right_color"]
            bl = parquet["bottom_left_color"]
            br = parquet["bottom_right_color"]
            distances = [
                sum((a - b)**2 for a, b in zip(tl, tr)),
                sum((a - b)**2 for a, b in zip(tl, bl)),
                sum((a - b)**2 for a, b in zip(tl, br)),
                sum((a - b)**2 for a, b in zip(tr, bl)),
                sum((a - b)**2 for a, b in zip(tr, br)),
                sum((a - b)**2 for a, b in zip(bl, br))
            ]
            max_distance = max(distances)
            threshold = 3 * (ithres**2)
            if max_distance <= threshold:
                updated_parquets.append(parquet)
                continue
            
            # Use floating-point arithmetic for splitting
            split_x = original_width / 2
            split_y = original_height / 2

            sub_parquets = []
            for i in range(2):
                for j in range(2):
                    # Original coordinates (unclamped)
                    new_x1 = x1 + j * split_x
                    new_y1 = y1 + i * split_y
                    new_x2 = new_x1 + split_x
                    new_y2 = new_y1 + split_y

                    # Snap coordinates to a grid
                    new_x1 = snap_to_grid(new_x1)
                    new_y1 = snap_to_grid(new_y1)
                    new_x2 = snap_to_grid(new_x2)
                    new_y2 = snap_to_grid(new_y2)

                    # Check if subparquet is completely outside
                    all_outside = True
                    for x, y in [(new_x1, new_y1), (new_x2, new_y1),
                                 (new_x2, new_y2), (new_x1, new_y2)]:
                        if 0 <= x < img_width and 0 <= y < img_height:
                            all_outside = False
                            break
                    if all_outside:
                        continue

                    # Clamped coordinates for cropping
                    crop_x1 = max(new_x1, 0)
                    crop_y1 = max(new_y1, 0)
                    crop_x2 = min(new_x2, img_width)
                    crop_y2 = min(new_y2, img_height)
                    if crop_x1 >= crop_x2 or crop_y1 >= crop_y2:
                        continue

                    # Calculate colors using clamped coordinates
                    cropped = main_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                    avg_color = average_colour_n_fallback(cropped)
                    width, height = cropped.size
                    if width == 0 or height == 0:
                        continue

                    # Quadrant colors
                    tl_q = cropped.crop((0, 0, width // 2, height // 2))
                    avg_tl = average_colour_n_fallback(tl_q)
                    tr_q = cropped.crop((width // 2, 0, width, height // 2))
                    avg_tr = average_colour_n_fallback(tr_q)
                    bl_q = cropped.crop((0, height // 2, width // 2, height))
                    avg_bl = average_colour_n_fallback(bl_q)
                    br_q = cropped.crop((width // 2, height // 2, width, height))
                    avg_br = average_colour_n_fallback(br_q)

                    # Determine on_the_edge status
                    inside_corners = sum(
                        0 <= x < img_width and 0 <= y < img_height
                        for x, y in [(new_x1, new_y1), (new_x2, new_y1),
                                     (new_x2, new_y2), (new_x1, new_y2)]
                    )
                    on_the_edge_sub = 1 if inside_corners < 4 else 0

                    sub_parquets.append({
                        "coordinates": [
                            (new_x1, new_y1),
                            (new_x2, new_y1),
                            (new_x2, new_y2),
                            (new_x1, new_y2)
                        ],
                        "average_color": avg_color,
                        "on_the_edge": on_the_edge_sub,
                        "orientation": parquet["orientation"],
                        "priority": parquet["priority"]//4,    #downgrade its priority for matching
                        "top_left_color": avg_tl,
                        "top_right_color": avg_tr,
                        "bottom_left_color": avg_bl,
                        "bottom_right_color": avg_br
                    })

            if sub_parquets:
                updated_parquets.extend(sub_parquets)
                split_count += 1
            else:
                updated_parquets.append(parquet)

        main_img.close()
        print(f"Split {split_count} parquets into four-quarters ")
        print(f"{min_sized_parquet_count} parquets are at the minimum dimensions threshold")
        return updated_parquets
    except Exception as e:
        print(f"Error in parquet_split: {str(e)}")
        if 'main_img' in locals():
            main_img.close()
        return parquets



def main():
    setup_logging(CONFIG["log_file"])
 
    start_time = datetime.now()
    log_message(f"Step4 - splitting parquets threshold:{CONFIG["split_diff"]}... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}" )

    base_path, ext = os.path.splitext(CONFIG["parquets_csv_path"])
    masking_jpg_path = f"{base_path}.jpg"
    csv_backup_path = f"{base_path}_last{ext}"
    masking_jpg_backup_path = f"{base_path}_last.jpg"

    backup_file(CONFIG["parquets_csv_path"], csv_backup_path)
    backup_file(masking_jpg_path, masking_jpg_backup_path)

    
    try:
        # Read input parquets from CSV (now as floats) now moved to utils_csv_io.py
        parquets = read_parquets_csv(CONFIG["parquets_csv_path"])
        
        # Perform parquet splitting
        filtered = parquet_split(parquets, CONFIG["image_path"], CONFIG["split_diff"])
        
        # Save updated parquets to CSV
        current_time = datetime.now().strftime("@%H:%M:%S @%Y-%m-%d ")
        log_message(f"Parquet index file of {len(filtered)} saving...{current_time}")

        # Refactored version using save_parquet_csv
        save_parquet_csv(filtered, CONFIG["parquets_csv_path"])

        # Create visualization
        try:
            img = Image.open(CONFIG["image_path"]).convert("RGB")
            draw = ImageDraw.Draw(img)
            for p in filtered:
                (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p["coordinates"]
                draw.rectangle([x1, y1, x3, y3], outline="red", width=2)
            img.save(masking_jpg_path, 'JPEG', quality=30)
            log_message(f"Masking visualization saved to: {masking_jpg_path}")
            plt.figure(figsize=(CONFIG["plt_width"], CONFIG["plt_height"]))
            plt.imshow(img)
            plt.axis('on')
            plt.show()
        except Exception as e:
            log_message(f"Visualization error: {str(e)}")

        end_time = datetime.now()
        log_message(f"Step4 - splitting parquets... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===" )
   
    except Exception as e:
        log_message(f"Error in split_parquets execution: {str(e)}")
        raise
 
if __name__ == "__main__":
    main()

