# step2.ipynb generate index file for tesserae cropped by step1.ipynb
import os
os.environ["NUMEXPR_MAX_THREADS"] = "16"

from PIL import Image
from tqdm import tqdm
from datetime import datetime
import numpy as np
import csv
import hashlib

#common helper functions for this project, utils.py saved in the same folder
from utils import *
from utils_csv_io import *
from config import CONFIG

def get_all_image_paths(root_folder):
    image_paths = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.png') or file.endswith('.jpg'):
                image_paths.append(os.path.join(root, file))
    return image_paths

def classify_orientation(image):
    width, height = image.size
    return "landscape" if width > height else "portrait"

def calculate_folder_hash(image_paths):
    hash_md5 = hashlib.md5()
    for image_path in sorted(image_paths):
        hash_md5.update(image_path.encode('utf-8'))
        hash_md5.update(str(os.path.getmtime(image_path)).encode('utf-8'))
    return hash_md5.hexdigest()

def process_image_quadrants(img, original_dimensions):
    top_left = img.crop((0, 0, original_dimensions[0] // 2, original_dimensions[1] // 2))
    top_right = img.crop((original_dimensions[0] // 2, 0, original_dimensions[0], original_dimensions[1] // 2))
    bottom_left = img.crop((0, original_dimensions[1] // 2, original_dimensions[0] // 2, original_dimensions[1]))
    bottom_right = img.crop((original_dimensions[0] // 2, original_dimensions[1] // 2, original_dimensions[0], original_dimensions[1]))
    
    return (
        calculate_average_color(top_left),
        calculate_average_color(top_right),
        calculate_average_color(bottom_left),
        calculate_average_color(bottom_right)
    )

def generate_tess_index(tesserae_paths, index_file):
    index_data = []
    landscape_count = 0
    portrait_count = 0
    priority_count = 0
    optional_count = 0
    nocrop_count = 0
    included_count = 0
    unused_count = 0
    for image_path in tqdm(tesserae_paths, desc="Registering tesserae metadata"):
        # Determine priority based on subfolder structure
        iused = 1     # Default using img except it is the folder unused
        priority = 0  # Default priority 0 for other subfolders the will be assigned to the lowest 
        icropable = 1 # Default image can be cropped from 3x2 to 4x3, except images in the folder nocrop
        image_path_parts = image_path.split(os.sep)  # Split path into components
        
        try:
            # Check if the image is in a priority subfolder
            if 'priority' in image_path_parts:
                priority_index = image_path_parts.index('priority') + 1
                priority_suffix = int(image_path_parts[priority_index])  # Extract numeric suffix from subfolder
                priority = priority_suffix               #they take +ve priority
                priority_count += 1
            # Check if the image is in an optional subfolder
            elif 'optional' in image_path_parts:
                optional_index = image_path_parts.index('optional') + 1
                optional_suffix = int(image_path_parts[optional_index])  # Extract numeric suffix from subfolder
                priority = (0 + optional_suffix)*(-1)     #optional images take -ve priority
                optional_count += 1          
            # Check if the image is in a nocrop subfolder
            elif 'nocrop' in image_path_parts:                
                priority_index = image_path_parts.index('nocrop') + 1
                priority_suffix = int(image_path_parts[priority_index])  # Extract numeric suffix from subfolder
                priority = priority_suffix               #they take +ve priority
                icropable = 0
                nocrop_count += 1 
            elif 'unused' in image_path_parts:
                iused = 0
                unused_count +=1
            else: included_count += 1
            
        except (ValueError, IndexError):
            # Fallback to default priority if parsing fails
            pass

        if CONFIG["optional_tesserae"]: 
            if priority<0: priority=(-1)*priority
        
        if (priority >= 0) and (iused == 1):
            img = Image.open(image_path).convert('RGBA')
      
            original_dimensions = img.size
            avg_color = calculate_average_color(img)
            quadrant_colors = process_image_quadrants(img, original_dimensions)
            orientation = classify_orientation(img)        
            if orientation == "landscape": landscape_count += 1
            else: portrait_count += 1
   
            index_data.append([
                image_path, avg_color, original_dimensions, orientation,
                *quadrant_colors,
                priority, icropable  # priority, cropable
            ])

    #new integration of write_tesserae_index_file imported from utils_csv_io.py
    write_tesserae_index_file(index_file, index_data)  
    
    stats = {
        "Tile Orientation": f"Landscape: {landscape_count}, Portrait: {portrait_count}",
        "Tile Categories": f"Priority: {priority_count},  NoCrop: {nocrop_count}, Included: {included_count}",
        "Auxiliary Tiles": f"Optional: {optional_count}, Unused: {unused_count}"
    }
    for category, value in stats.items():
        log_message(f"{category}: {value}")
   
    return index_file


def check_for_changes(index_file, current_hash, force_refresh):
    hash_file = index_file + '.hash'
    if os.path.exists(hash_file) and not force_refresh:
        with open(hash_file, 'r') as hashfile:
            saved_hash = hashfile.read()
        return current_hash != saved_hash
    return True

def check_for_changes(index_file, current_hash, force_refresh):
    hash_file = index_file + '.hash'
    # Check if index file is missing or force refresh is requested
    if not os.path.exists(index_file) or force_refresh:
        return True
    # If hash file exists, compare hashes
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as hashfile:
            saved_hash = hashfile.read()
        return current_hash != saved_hash
    # If hash file doesn't exist, regenerate
    return True

def main():

    refresh = CONFIG["force_refresh"]
    setup_logging(CONFIG["log_file"])
     
    start_time = datetime.now()
    log_message(f"Step2 - indexing @{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tesserae_paths = get_all_image_paths(CONFIG["tesserae_folder"])
    current_hash = calculate_folder_hash(tesserae_paths)

    if check_for_changes(CONFIG["tesserae_index_path"], current_hash, refresh):
        log_message("Changes detected or forced refresh. Regenerating tesserae index.")
        generate_tess_index(tesserae_paths, CONFIG["tesserae_index_path"])
        with open(CONFIG["tesserae_index_path"] + '.hash', 'w') as hashfile:
            hashfile.write(current_hash)
    else:
        log_message(f"No changes detected. Using existing tesserae index file: {CONFIG['tesserae_index_path']}")

    end_time = datetime.now()
    log_message(f"Step2 - Tesserae Indexing... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===")

if __name__ == "__main__":
    main()

