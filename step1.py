import os
os.environ["NUMEXPR_MAX_THREADS"] = "16"

from datetime import datetime
import hashlib
from tqdm import tqdm
from PIL import Image
import shutil

# Import the centralized configuration
from config import CONFIG  # Import the read-only CONFIG object

#common helper functions for this project, utils.py saved in the same folder
from utils import *

def get_all_image_paths(root_folder):
    """Get all image paths from a root folder recursively."""
    image_paths = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_paths.append(os.path.join(root, file))
    return image_paths

def calculate_folder_hash(image_paths):
    """Calculate MD5 hash of folder contents based on paths and modification times."""
    hash_md5 = hashlib.md5()
    for image_path in sorted(image_paths):
        hash_md5.update(image_path.encode('utf-8'))
        hash_md5.update(str(os.path.getmtime(image_path)).encode('utf-8'))
    return hash_md5.hexdigest()

def get_folder_size(folder_path):
    """Calculate folder size in megabytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def clear_tesserae_folders(tesserae_folder):
    """Clear and recreate tesserae folders."""
    if os.path.exists(tesserae_folder):
        shutil.rmtree(tesserae_folder)
    os.makedirs(tesserae_folder)

def crop_and_resize_image(img, aspect_ratio, tess_size):
    """Crop and resize image to specified aspect ratio and size."""
    try:
        width, height = img.size
        if width / height > aspect_ratio:
            new_height = height
            new_width = int(new_height * aspect_ratio)
        else:
            new_width = width
            new_height = int(new_width / aspect_ratio)

        left = (width - new_width) // 2
        top = (height - new_height) // 2
        right = (width + new_width) // 2
        bottom = (height + new_height) // 2

        cropped_img = img.crop((left, top, right, bottom))
        cropped_width, cropped_height = cropped_img.size

        if (width > height and (cropped_width < tess_size[0] or cropped_height < tess_size[1])) or \
           (width <= height and (cropped_width < tess_size[1] or cropped_height < tess_size[0])):
            return None, "Tile image is too small"
        else:
            resized_img = cropped_img.resize(tess_size if width > height else tess_size[::-1])
            return resized_img, None

    except Exception as e:
        raise Exception(f"Error cropping and resizing image: {e}")

def process_image(image_path, tesserae_folder, tile_folder, tess_size):
    """Process a single image - crop, resize, and save to the appropriate subfolder."""
    try:
        img = Image.open(image_path)
        width, height = img.size

        # Determine the relative path of the image in the tile folder
        relative_path = os.path.relpath(os.path.dirname(image_path), tile_folder)

        # Create the corresponding subfolder in the tesserae folder
        dest_folder = os.path.join(tesserae_folder, relative_path)
        os.makedirs(dest_folder, exist_ok=True)

        # Crop and resize the image
        if width > height:
            aspect_ratio = 1.5
        else:
            aspect_ratio = 2 / 3

        cropped_resized_img, error = crop_and_resize_image(img, aspect_ratio, tess_size)
        
        if error:
            log_message(f"\nSkipping {image_path}: {error}")
            return False

        # Save the processed image
        filename = os.path.splitext(os.path.basename(image_path))[0] + '.png'
        save_path = os.path.join(dest_folder, filename)
        cropped_resized_img.save(save_path, 'PNG')
        return True
    except Exception as e:
        log_message(f"Error processing {image_path}: {e}")
        return False

def crop_tiles_and_save(tile_folder, tesserae_folder, tess_size):
    """Main function to process all images in the tile folder."""
    clear_tesserae_folders(tesserae_folder)
    log_message(f"Tesserae folder cleared at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    image_paths = get_all_image_paths(tile_folder)
    success_count = 0

    for image_path in tqdm(image_paths, desc="Crop-n-Resizing images"):
        if process_image(image_path, tesserae_folder, tile_folder, tess_size):
            success_count += 1

    total_size_mb = get_folder_size(tesserae_folder)
    log_message(f"Total size of tesserae folder: {total_size_mb:.2f} MB")
    log_message(f"Cropped and resized {success_count} images and saved them in the respective folders.")
    log_message(f"Skipped {len(image_paths) - success_count} image(s) due to errors or small size.")
    return success_count

def check_folder_changes(tile_folder, tile_hash_file_path):
    """Check if tile folder has changed since last run."""
    all_image_paths = get_all_image_paths(tile_folder)
    current_tile_folder_hash = calculate_folder_hash(all_image_paths)
    
    if os.path.exists(tile_hash_file_path):
        with open(tile_hash_file_path, 'r') as hashfile:
            saved_tile_folder_hash = hashfile.read()
        return current_tile_folder_hash, current_tile_folder_hash != saved_tile_folder_hash
    return current_tile_folder_hash, True

def main():
    setup_logging(CONFIG["log_file"])
    #validate_config()
    
    tess_dimension = [CONFIG["tessera_width"], CONFIG["tessera_height"]]
    
    start_time = datetime.now()
    log_message(f"Step1 - centre-cropping {tess_dimension[0]}x{tess_dimension[1]}  @{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"Processing images from: {CONFIG['tile_folder']}")

    # Use the resolved hash file directory from CONFIG
    tile_hash_file_path = os.path.join(CONFIG["hash_file_directory"], 'tile_folder.hash')

    # Ensure the directory exists
    os.makedirs(CONFIG["hash_file_directory"], exist_ok=True)

    current_hash, has_changes = check_folder_changes(
        CONFIG["tile_folder"], 
        tile_hash_file_path
    )

    if CONFIG["force_refresh"]:
        log_message("Force refresh enabled. Regenerating tesserae.")
        crop_tiles_and_save(
            CONFIG["tile_folder"], 
            CONFIG["tesserae_folder"], 
            tess_dimension
        )
        # Save the new hash after regeneration
        current_hash = calculate_folder_hash(get_all_image_paths(CONFIG["tile_folder"]))
        with open(tile_hash_file_path, 'w') as hashfile:
            hashfile.write(current_hash)
    elif has_changes:
        log_message("Changes detected in the tile folder. Regenerating tesserae.")
        crop_tiles_and_save(
            CONFIG["tile_folder"], 
            CONFIG["tesserae_folder"], 
            tess_dimension
        )
        # Save the new hash after regeneration
        with open(tile_hash_file_path, 'w') as hashfile:
            hashfile.write(current_hash)
    else:
        log_message("No changes detected in the tile folder. Tesserae generation skipped.")

    end_time = datetime.now()
    log_message(f"Step1 - tiles-cropping... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===")

if __name__ == "__main__":
    main()