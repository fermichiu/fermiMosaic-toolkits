#step8 restore the last version of parquets.csv & masking.jpg
#copy from the last version (parquets.csv & masking.jpg) to parquets.csv and its masking.jpg
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
    log_message(f"undo - parqueting ... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}" )

    base_path, ext = os.path.splitext(CONFIG["parquets_csv_path"])
    masking_jpg_path = f"{base_path}.jpg"
    csv_backup_path = f"{base_path}_last{ext}"
    masking_jpg_backup_path = f"{base_path}_last.jpg"

#destination_file = CONFIG["parquets_csv_path"]  #source_file = csv_backup_path
    backup_file(csv_backup_path,CONFIG["parquets_csv_path"])

# destination_file = masking_jpg_path   #source_file = masking_jpg_backup_path
    backup_file(masking_jpg_backup_path, masking_jpg_path)
    
   
    end_time = datetime.now()
    log_message(f"undo - parqueting... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===" )


if __name__ == "__main__":
    main()


