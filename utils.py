#this common helper functinon need for each step*.py
import os

import logging
def log_message(message):
    """Log a message to both console and log file."""
    logging.info(message)
    print(message)

def setup_logging(log_file):
    """Initialize logging configuration."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),  # Writes to the log file
            #logging.StreamHandler()         # Writes to the console
        ]
    )


#def get_average_color(image):   #it was previously defined as get_average_color.
def average_colour_n_fallback(image):
    """Calculate the average color of an image."""
    width, height = image.size
    pixels = image.load()
    r, g, b, count = 0, 0, 0, 0
    for x in range(width):
        for y in range(height):
            pixel = pixels[x, y]
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
            count += 1
    return (r // count, g // count, b // count) if count > 0 else (0, 0, 0)



#############not working sometimes 
"""Faster implementation using ImageStat"""
def calculate_average_color(image):
    from PIL.ImageStat import Stat
    stat = Stat(image.convert('RGB'))
    return tuple(map(int, stat.mean))
"""to be called from step2, 3 ,4, 5, 6 and 7"""


# Check if quadrants are non-zero before calculating average color  oversimplified
def safe_avg(region):
    """Return average color or fallback to (0,0,0) if region is empty."""
    w, h = region.size
    return calculate_average_color(region) if w > 0 and h > 0 else (0, 0, 0)

# Check if quadrants are non-zero before calculating average color #############not working sometimes 
def __average_colour_n_fallback(region):                                   
    """Return average color or fallback to (0,0,0) if region is empty."""
    w, h = region.size
    if w <= 0 or h <= 0:
        return (0, 0, 0)
    try:
        return calculate_average_color(region)
    except Exception as ex:
        # Log the unexpected error details if needed
        print(f"Warning: Couldn't compute average color for region with size ({w}, {h}): {ex}")
        return (0, 0, 0)
###############################################################not working sometimes
# File "C:\Users\kchiu\AppData\Local\anaconda3\Lib\site-packages\PIL\ImageStat.py", line 123, in mean
#    return [self.sum[i] / self.count[i] for i in self.bands]
