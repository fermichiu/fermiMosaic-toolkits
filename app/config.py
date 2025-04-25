import json
import os
from pathlib import Path
# Import the log_message function from utils.py
from utils import log_message

# Load the configuration from config.json
with open('config.json', 'r') as f:
    _config = json.load(f)

# Resolve paths using user's home directory
home = str(Path.home())
base_path = os.path.expanduser(_config['base_path'])  # Handles ~ in path

# Update configuration paths
_config.update({
    'base_path': base_path,
    'tile_folder': os.path.join(base_path, 'tiles'),
    'tesserae_folder': os.path.join(base_path, 'tesserae'),
    'index_folder': os.path.join(base_path, 'index-n-log'),
})

# Resolve motif folder and filename
motif_folder = _config.get('motif_folder', 'motif')  # Default to 'motif' if not specified
motif_filename = _config.get('motif_filename', 'input.jpg')  # Default to 'input.jpg' if not specified
_config['image_path'] = os.path.join(base_path, motif_folder, motif_filename)

_config['output_path'] = os.path.join(base_path, 'mosaics')

# Resolve CSV paths relative to base_path
for key, default in {
    'parquets_csv_path': 'index-n-log/parquets.csv',
    'tesserae_index_path': 'index-n-log/tesserae_index.csv',
    'candidates_output_path': 'index-n-log/candidates_index.csv',
    'log_file': 'index-n-log/log-message.txt',
    'hash_file_directory': 'index-n-log',
}.items():
    _config[key] = os.path.normpath(os.path.join(base_path, _config.get(key, default)))

# Configuration Validation
REQUIRED_KEYS = [
    "tessera_width", "tessera_height",                # Parameters for step 1
    "base_path", "hash_file_directory",               # Parameters for step 1
    "motif_folder", "motif_filename",                 # Parameters for config.py
    "force_refresh", "optional_tesserae",             # A checkbox in webui for step 2
    "index_n_log_folder", "log_file",                 # Paths for utils.py logging message
    "tesserae_folder", "tile_folder",                 # Paths for steps 1-7
    "image_path", "output_path",                      # join in config.py for steps 1-7  
    "parquets_csv_path", "tesserae_index_path",       # Paths for steps 1-7
    "candidates_output_path",                         # Paths for steps 1-7
    "imode", "parquet_size_factor",                   # Parameters for step 3
    "randomness_percentage", "parquet_unit_width",    # Parameters for step 3
    "split_diff", "merge_diff",                       # Parameters for steps 4 and 5
    "threshold_percentage", "prioritized_by_chance",  # Parameters for step 6
    "mosaic_anime", "anime_size_downsize",            # Parameters for step 7
    "anime_fps", "mosaic_jpg_quality",                # Parameters for step 7
    "plt_width", "plt_height"                         # Showing the image on webui/popup
]

for key in REQUIRED_KEYS:
    if key not in _config:
        raise ValueError(f"Missing required configuration key: {key}")

# For compatibility with existing logic.
# Add logic to convert randomness_percentage to a decimal format (ratio)
_config['ratio'] = (_config['randomness_percentage']*1.0) / 100.0
# Log a message indicating successful validation
log_message("===Configuration validated===")



# Make config read-only
class Config(dict):
    def __setattr__(self, key, value):
        raise AttributeError("Configuration is read-only")

# Create a read-only configuration object
CONFIG = Config(_config)