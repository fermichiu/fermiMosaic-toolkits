#step8 backup the current parquets.csv & masking.jpg 
#copy from the current version to timestamp parquets.csv and its masking.jpg
import os
import shutil
from datetime import datetime
#common helper functions for this project, utils.py saved in the same folder
from utils import *
from utils_csv_io import *
from config import CONFIG

def main():
    setup_logging(CONFIG["log_file"])
    
    start_time = datetime.now()
    log_message(f"backup - parqueting ... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}" )

    base_path, ext = os.path.splitext(CONFIG["parquets_csv_path"])
    masking_jpg_path = f"{base_path}.jpg"
    csv_backup_path = f"{base_path}_{start_time.strftime('%Y%m%d_%H%M%S')}{ext}"
    masking_jpg_backup_path = f"{base_path}_{start_time.strftime('%Y%m%d_%H%M%S')}.jpg"

    source_file = CONFIG["parquets_csv_path"]
    destination_file = csv_backup_path

    backup_file(CONFIG["parquets_csv_path"],csv_backup_path)

    source_file = masking_jpg_path
    destination_file = masking_jpg_backup_path

    backup_file(masking_jpg_path,masking_jpg_backup_path)

    end_time = datetime.now()
    log_message(f"backup - parqueting... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===" )

if __name__ == "__main__":
    main()
