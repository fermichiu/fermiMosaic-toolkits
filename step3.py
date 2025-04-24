# step3.ipynb - Parquet Generation 
import os
os.environ["NUMEXPR_MAX_THREADS"] = "16"

from PIL import Image, ImageDraw
import csv
import random
import shutil
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime

from config import CONFIG

#common helper functions for this project, utils.py saved in the same folder
from utils import calculate_average_color 
from utils import log_message
from utils import setup_logging
from utils import average_colour_n_fallback
from utils_csv_io import backup_file
from utils_csv_io import save_parquet_csv


def analyze_target(imode, ratio, image_path, width_parquet, height_parquet, csv_path, seed=None):
    """Analyze image and generate parquet data."""
    current_time = datetime.now().strftime("@%H:%M:%S @%Y-%m-%d ")
    print(f"Analyzing Motif - the main image {current_time}")
    try:
        if seed is not None:
            random.seed(seed)
        img = Image.open(image_path)
        img_width, img_height = img.size

        # Validate image dimensions
        if img_width == 0 or img_height == 0:
            raise ValueError("Invalid image dimensions (0x0). Check the input image.")
        
        middle_x = img_width // 2 - width_parquet // 2
        middle_y = img_height // 2 - height_parquet // 2
        parquets = []
        x_off = random.randint(0, width_parquet-1)
        y_off = random.randint(0, width_parquet-1)
        
        # Initial parquet setup
        if imode == 1:
            x1, y1 = -middle_x - 2 * img_width + x_off, -middle_y + y_off   
        elif imode == -1: 
            x1, y1 = -middle_x + x_off, -middle_y - 2 * img_width + y_off   
        else:
            x1, y1 = middle_x*2 + x_off, -middle_y*2 + y_off   
        
        first_parquet = {
            "average_color": (0, 0, 0),
            "on_the_edge": 0,            
            "priority": 0,
            "top_left_color": (0, 0, 0),
            "top_right_color": (0, 0, 0),
            "bottom_left_color": (0, 0, 0),
            "bottom_right_color": (0, 0, 0)
        }
        
        # Orientation-specific coordinate setup
        if imode != -1:
            first_parquet["coordinates"] = [
                (x1, y1),
                (x1 + width_parquet, y1),
                (x1 + width_parquet, y1 + height_parquet),
                (x1, y1 + height_parquet)                
            ]
            first_parquet["orientation"] = "landscape"
        else:
            first_parquet["coordinates"] = [
                (x1, y1),
                (x1 + height_parquet, y1),
                (x1 + height_parquet, y1 + width_parquet),
                (x1, y1 + width_parquet)                
            ]
            first_parquet["orientation"] = "portrait"
        
        parquets.append(first_parquet)
        unit_row = [first_parquet]
        itwist = 1
        
        # Generate parquet grid
        for col in range(1, 4 * (img_width // width_parquet)):
            last = unit_row[-1]["coordinates"]
            new_parquet = {
                "average_color": (0, 0, 0),
                "on_the_edge": 0,   
                "priority": 0,
                "top_left_color": (0, 0, 0),
                "top_right_color": (0, 0, 0),
                "bottom_left_color": (0, 0, 0),
                "bottom_right_color": (0, 0, 0)
            }
            
            if imode == 1:
                new_parquet["coordinates"] = [
                    (last[0][0] + width_parquet, last[0][1]),
                    (last[1][0] + width_parquet, last[1][1]),
                    (last[2][0] + width_parquet, last[2][1]),
                    (last[3][0] + width_parquet, last[3][1])
                ]
                new_parquet["orientation"] = "landscape"
            elif imode == -1:
                new_parquet["coordinates"] = [
                    (last[0][0], last[0][1] + width_parquet),
                    (last[1][0], last[1][1] + width_parquet),
                    (last[2][0], last[2][1] + width_parquet),
                    (last[3][0], last[3][1] + width_parquet)
                ]
                new_parquet["orientation"] = "portrait"
            else:
                if random.random() > ratio:
                    itwist += 1               
                if itwist % 2 == 0:
                    new_parquet["coordinates"] = [
                        (last[2][0] + 0, last[2][1] - height_parquet),
                        (last[2][0] + width_parquet, last[2][1] - height_parquet),
                        (last[2][0] + width_parquet, last[2][1] + 0),
                        (last[2][0] + 0, last[2][1] + 0)
                    ]
                    new_parquet["orientation"] = "landscape"
                else:
                    new_parquet["coordinates"] = [
                        (last[2][0] - height_parquet, last[2][1] + 0),
                        (last[2][0] + 0, last[2][1] + 0),
                        (last[2][0] + 0, last[2][1] + width_parquet),
                        (last[2][0] - height_parquet, last[2][1] + width_parquet)
                    ]
                    new_parquet["orientation"] = "portrait"
                itwist += 1
            parquets.append(new_parquet)
            unit_row.append(new_parquet)
        
        current_row = unit_row.copy()
        for row in range(1, 4 * (img_height // height_parquet)):
            if random.random() > ratio:
              row_shift = 0               
            else: row_shift = random.randint(4*width_parquet//10, 7*width_parquet//10)
            
            new_row = []
            for p in current_row:
                coords = p["coordinates"]
                if imode == 1:
                    new_parquet = {
                        "coordinates": [
                            (coords[0][0] + row_shift, coords[0][1] + height_parquet),
                            (coords[1][0] + row_shift, coords[1][1] + height_parquet),
                            (coords[2][0] + row_shift, coords[2][1] + height_parquet),
                            (coords[3][0] + row_shift, coords[3][1] + height_parquet)
                        ],
                        "average_color": (0, 0, 0),
                        "on_the_edge": 1,
                        "orientation": "landscape",
                        "priority": 0,
                        "top_left_color": (0, 0, 0),
                        "top_right_color": (0, 0, 0),
                        "bottom_left_color": (0, 0, 0),
                        "bottom_right_color": (0, 0, 0)
                    }
                elif imode == -1:
                    new_parquet = {
                        "coordinates": [
                            (coords[0][0] + height_parquet, coords[0][1] + row_shift),
                            (coords[1][0] + height_parquet, coords[1][1] + row_shift),
                            (coords[2][0] + height_parquet, coords[2][1] + row_shift),
                            (coords[3][0] + height_parquet, coords[3][1] + row_shift)
                        ],
                        "average_color": (0, 0, 0),
                        "on_the_edge": 1,
                        "orientation": "portrait",
                        "priority": 0,
                        "top_left_color": (0, 0, 0),
                        "top_right_color": (0, 0, 0),
                        "bottom_left_color": (0, 0, 0),
                        "bottom_right_color": (0, 0, 0)
                    }
                else: 
                    new_parquet = {
                        "coordinates": [
                            (coords[0][0] - height_parquet, coords[0][1] + height_parquet),
                            (coords[1][0] - height_parquet, coords[1][1] + height_parquet),
                            (coords[2][0] - height_parquet, coords[2][1] + height_parquet),
                            (coords[3][0] - height_parquet, coords[3][1] + height_parquet)
                        ],
                        "average_color": (0, 0, 0),
                        "on_the_edge": 1,
                        "orientation": p["orientation"],
                        "priority": 0,
                        "top_left_color": (0, 0, 0),
                        "top_right_color": (0, 0, 0),
                        "bottom_left_color": (0, 0, 0),
                        "bottom_right_color": (0, 0, 0)
                    }
                parquets.append(new_parquet)
                new_row.append(new_parquet)
            current_row = new_row
        
        # Crop and filter parquets
        filtered = []
        p_priority = 0     ###
        for p in tqdm(parquets, "Cropping the parquets on the edge"):
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p["coordinates"]
            inside = sum([
                0 <= x < img_width and 0 <= y < img_height
                for x, y in [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
            ])
            on_the_edge = 0 if inside > 3 else 1

            p_priority = pow(2, 13)

            if img_width/3 < x1 < 2*img_width/3 and img_height/3 < y1 < 2*img_height/3: p_priority = pow(2, 14) 
            if img_width/3 < x3 < 2*img_width/3 and img_height/3 < y3 < 2*img_height/3: p_priority = pow(2, 14)
            
            if x1<= img_width/3 <=x3: p_priority = pow(2, 15)           
            if x1<= 2*img_width/3 <=x3: p_priority = pow(2, 15)
            if y1<= img_height/3 <=y3: p_priority = pow(2, 15)
            if y1<= 2*img_height/3 <=y3: p_priority = pow(2, 15)

#            if x1<= img_width/3 <=x3 and y1<= img_height/3 <=y3: p_priority = pow(2, 16)
#            if x1<= 2*img_width/3 <=x3 and y1<= img_height/3 <=y3: p_priority = pow(2, 16)
#            if x1<= img_width/3 <=x3 and y1<= 2*img_height/3 <=y3: p_priority = pow(2, 16)    
#            if x1<= 2*img_width/3 <=x3 and y1<= 2*img_height/3 <=y3: p_priority = pow(2, 16)
                
            if inside > 0:
                if on_the_edge == 1: p_priority = 0         ###assign parquet on the edge priority to lowest 
                
                crop_x1 = max(x1, 0)
                crop_y1 = max(y1, 0)
                crop_x2 = min(x3, img_width)
                crop_y2 = min(y3, img_height)
                cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                avg_color = calculate_average_color(cropped)
                width, height = cropped.size
                if width == 0 or height == 0:
                    continue

            
                
                tl = cropped.crop((0, 0, width//2, height//2))
                avg_tl = average_colour_n_fallback(tl)
                tr = cropped.crop((width//2, 0, width, height//2))
                avg_tr = average_colour_n_fallback(tr)
                bl = cropped.crop((0, height//2, width//2, height))
                avg_bl = average_colour_n_fallback(bl)
                br = cropped.crop((width//2, height//2, width, height))
                avg_br = average_colour_n_fallback(br)
                filtered.append({
                    "coordinates": [
                        (x1, y1), (x2, y2), (x3, y3), (x4, y4)  # experimental
                    ],
                    "average_color": avg_color,
                    "on_the_edge": on_the_edge,
                    "orientation": p["orientation"],
                    "priority": p_priority,                   
                    "top_left_color": avg_tl,
                    "top_right_color": avg_tr,
                    "bottom_left_color": avg_bl,
                    "bottom_right_color": avg_br
                })
        
        # Save CSV  
        current_time = datetime.now().strftime("@%H:%M:%S @%Y-%m-%d ")
        # In analyze_target, after filtering
        print(f"Filtered {len(filtered)} parquets out of {len(parquets)} total")
        print(f"Parquet index file of {len(filtered)} saving...{current_time}")
        
        # Call the new function to save the CSV from utils_csv_io.py
        save_parquet_csv(filtered, csv_path)

        return True, csv_path, filtered
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, None, None

def main():
    setup_logging(CONFIG["log_file"])
    
    start_time = datetime.now()
    log_message(f"Step3 - parqueting motif... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    base_path, ext = os.path.splitext(CONFIG["parquets_csv_path"])
    masking_jpg_path = f"{base_path}.jpg"
    csv_backup_path = f"{base_path}_last{ext}"
    masking_jpg_backup_path = f"{base_path}_last.jpg"

    backup_file(CONFIG["parquets_csv_path"], csv_backup_path)
    backup_file(masking_jpg_path, masking_jpg_backup_path)
    
    try:
        # Calculate parquet dimensions
        width_parquet = CONFIG["parquet_unit_width"] * CONFIG["parquet_size_factor"]
        height_parquet = (width_parquet // 3) * 2

        #it was backward compatible with config.py _config['ratio'] = (_config['randomness_percentage']*1.0) / 100.0
        #randomness = CONFIG["ratio"]   #ratio a float (0,1) the probability threshold to give randomness
        
        randomness = (CONFIG["randomness_percentage"]*1.0) / 100.0    
        
        # Analyze image and generate parquets    
        success, csv_file, parquets = analyze_target(
            CONFIG["imode"], 
            randomness, 
            CONFIG["image_path"], 
            width_parquet, 
            height_parquet, 
            CONFIG["parquets_csv_path"]
        )

        
        if success:
            log_message(f"Tesserae index file generated: {csv_file}")
        else:
            log_message("Processing Tesserae index failed")
        
        # visualization and saving to jpg file
        #save_visualization(CONFIG["image_path"], parquets, masking_jpg_path)
        try:
            if not parquets:  # Check if parquets is empty or None
                log_message("No parquets to visualize. Saving placeholder image.")
                Image.new('RGB', (100, 100), color='gray').save(masking_jpg_path)
            else:
                img = Image.open(CONFIG["image_path"]).convert("RGB")
                draw = ImageDraw.Draw(img)
                for p in parquets:
                    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p["coordinates"]
                    draw.rectangle([x1, y1, x3, y3], outline="blue", width=2)
                img.save(masking_jpg_path, 'JPEG', quality=50)
                log_message(f"Visualization saved to: {masking_jpg_path}")
        
                plt.figure(figsize=(CONFIG["plt_width"], CONFIG["plt_height"]))
                plt.imshow(img)
                plt.axis('on')
                plt.show()
            
        except Exception as e:
            log_message(f"Visualization error: {str(e)}")
        
        end_time = datetime.now()
        log_message(f"Step3 - parqueting Motif... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===")
        
    except Exception as e:
        log_message(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()
