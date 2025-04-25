#Step6 tesserae matching
import os
os.environ["NUMEXPR_MAX_THREADS"] = "16"
import random
import math
import csv
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from tqdm import tqdm
from datetime import datetime

#common helper functions for this project, utils.py saved in the same folder
from utils import *
from utils_csv_io import *
from config import CONFIG


def calculate_color_distance(color1, color2):
    """Calculate Euclidean distance between two RGB colors."""
    return sum((a - b) ** 2 for a, b in zip(color1, color2))

def scale_parquet_coordinates(parquets, scale_factor):
    """Scale all parquet coordinates by the given factor."""
    for parquet in parquets:
        parquet["coordinates"] = [
            (int(x * scale_factor), int(y * scale_factor)) 
            for (x, y) in parquet["coordinates"]
        ]
    return parquets

def find_best_tessera(parquet_color, tesserae):
    """
    Find the best matching tessera for the given parquet color.
    Returns (best_tessera, distance) tuple.
    """
    # Calculate all distances and group by usage count
    usage_groups = {}
    for tessera in tesserae:
        distance = calculate_color_distance(parquet_color, tessera["average_color"])
        usage_count = tessera['usage_count']
        if usage_count not in usage_groups:
            usage_groups[usage_count] = []
        usage_groups[usage_count].append((tessera, distance))
    
    # Sort groups by usage count and get the best candidate from least used group
    sorted_groups = sorted(usage_groups.items(), key=lambda x: x[0])
    for usage_count, group in sorted_groups:
        if group:
            group.sort(key=lambda x: x[1])  # Sort by distance within group
            return group[0]
    
    return (None, float('inf'))

def create_candidate_entry(parquet, best_tessera, distance):
    """Create a dictionary with all candidate information."""
    return {
        "coordinates": parquet["coordinates"],
        "on_the_edge": parquet["on_the_edge"],
        "orientation": parquet["orientation"],
        "parquet_colors": {
            "average": parquet["average_color"],
            "top_left": parquet["top_left_color"],
            "top_right": parquet["top_right_color"],
            "bottom_left": parquet["bottom_left_color"],
            "bottom_right": parquet["bottom_right_color"]
        },
        "candidate": {
            "image_path": best_tessera["image_path"],
            "score": distance,
            "tessera_colors": {
                "average": best_tessera["average_color"],
                "top_left": best_tessera["top_left_color"],
                "top_right": best_tessera["top_right_color"],
                "bottom_left": best_tessera["bottom_left_color"],
                "bottom_right": best_tessera["bottom_right_color"]
            }
        }
    }

def calculate_brightness(rgb):
    if isinstance(rgb, tuple) and len(rgb) == 3:  # Ensure it's an RGB tuple
        r, g, b = rgb
        return 0.299 * r + 0.587 * g + 0.114 * b  # Weighted brightness formula
    elif isinstance(rgb, (int, float)):  # Already a single numerical value
        return rgb
    else:
        raise ValueError(f"Unexpected type for 'average_color': {type(rgb)}")


def prepare_mosaic_prioritized_sorted_filtered(parquets, tesserae_index_path, candidates_output_path, scale_up):
    """
    Create a mosaic by assigning tesserae to parquets in two phases with aspect ratio constraints:
    1. Assign non-zero priority tesserae considering cropability and aspect ratios
    2. Assign remaining parquets to priority 0 tesserae with minimal reuse and aspect constraints
    """
    # Load tesserae and initialize usage tracking
    tesserae = read_tesserae_index_file(tesserae_index_path)
    if not tesserae:
        print("Failed to load tesserae index.")
        return
    
    # Separate tesserae into priority groups
    priority_groups = {}
    priority_zero = []
    for tessera in tesserae:
        prio = tessera['priority']
        if prio == 0:
            priority_zero.append(tessera)
        else:
            priority_groups.setdefault(prio, []).append(tessera)
    
    # Sort non-zero priorities in ascending order (1, 2, ...)
    sorted_priorities = sorted(priority_groups.keys())


    # Get main image dimensions
    main_img = Image.open(CONFIG["image_path"])
    img_width, img_height = main_img.size
    main_img.close()
    
    # Clamp edge parquets to image boundaries
    for parquet in parquets:
        if parquet.get("on_the_edge", 0) == 1:
            clamped_coords = []
            for (x, y) in parquet["coordinates"]:
                clamped_x = max(0, min(x, img_width))
                clamped_y = max(0, min(y, img_height))
                clamped_coords.append((clamped_x, clamped_y))
            parquet["coordinates"] = clamped_coords
    # Scale parquet coordinates
    parquets = scale_parquet_coordinates(parquets, scale_up)
    
    # Track used parquets by their coordinates string representation
    used_parquets = set()
    candidates = []
    
    # Part 1: Assign tesserae by priority (1, 2, ...)
    threshold_percentage = CONFIG["threshold_percentage"]  # New parameter from config

    for priority in sorted_priorities:
        group = priority_groups[priority]
        group_sorted = sorted(group, key=lambda t: t['average_color'], reverse=True)
        for tessera in tqdm(group_sorted, desc=f"Priority {priority} tesserae"):
            valid_aspects = {1.5, 2/3} if tessera['cropable'] == 0 else None
            valid_parquets = []  # Collect all parquets meeting aspect constraints

            for parquet in parquets:
                coords_str = str(parquet["coordinates"])
                if coords_str in used_parquets:
                    continue

                # Check aspect ratio constraints
                if valid_aspects is not None:
                    aspect = parquet['width'] / parquet['height']
                    if not any(abs(aspect - va) < 0.01 for va in valid_aspects):
                        continue

                distance = calculate_color_distance(tessera["average_color"], parquet["average_color"])
                valid_parquets.append((parquet, distance))

            if not valid_parquets:
                continue  # Skip if no valid candidates

            # Calculate dynamic threshold: (max - min) * (N%)
            distances = [d for (p, d) in valid_parquets]
            min_d = min(distances)
            max_d = max(distances)
            dynamic_threshold = (max_d - min_d) * (threshold_percentage / 100) + min_d

            # Filter candidates within dynamic threshold
            #candidate_parquets = [
            #    (p, d) for (p, d) in valid_parquets
            #    if d <= dynamic_threshold  # Apply dynamic threshold
            #]

            # Filter candidates within dynamic threshold AND with priority >= pow(2, 10)   where max pow(2, 15)
            candidate_parquets = [
                (p, d) for (p, d) in valid_parquets
                if d <= dynamic_threshold and p.get("priority", 0) >= pow(2, 10)
            ]
            
            if not candidate_parquets:
                continue  # No candidates within threshold

            # Sort by priority (descending) and distance (ascending)
            #candidate_parquets.sort(key=lambda x: (-x[0].get('priority', 0), x[1]))

            # Introduce randomness to balance mosaic quality and parquet priority
            random_number = random.randint(0, 100)  # Generate a random number between 0 and 100
            prioritized_by_chance = CONFIG["prioritized_by_chance"]  # Default to 50% if not specified
            
            if random_number < prioritized_by_chance:
                # Sort by priority (descending) and distance (ascending)
                candidate_parquets.sort(key=lambda x: (-x[0].get('priority', 0), x[1]))
            else:
                # Sort by primary key color distance (ascending) and secondary priority (descending)
                candidate_parquets.sort(key=lambda x: (x[1], -x[0].get('priority', 0)))
            
            # Select top candidate and track delta
            selected_parquet, selected_distance = candidate_parquets[0]
            delta = selected_distance - min_d  # Compare to the global minimum

            # Update records
            #candidates.append(create_candidate_entry(
            #    selected_parquet, tessera, selected_distance, delta
            #))
            candidates.append(create_candidate_entry(
                selected_parquet, tessera, selected_distance
            ))
            used_parquets.add(str(selected_parquet["coordinates"]))
            tessera['usage_count'] = 1

    
    # Part 2: Assign remaining parquets to priority 0 tesserae
    remaining_parquets = [pq for pq in parquets if str(pq["coordinates"]) not in used_parquets]
    
    # Sort remaining parquets by average color in reverse order
    #remaining_parquets_sorted = sorted(remaining_parquets, key=lambda pq: pq["average_color"], reverse=True )

    #NEW: Sort remaining parquets by priority (primary) and brightness (secondary)
    remaining_parquets_sorted = sorted(
        remaining_parquets,
        key=lambda pq: (
            pq.get("priority", 0),                  # Priority (descending)
            calculate_brightness(pq["average_color"])  # Brightness (descending, for ascending via negation)
        ),
        reverse=True  # Descending order for priority; brightness is effectively ascending due to negation
    )
    
    
    # Reset usage counts for priority 0 tesserae
    for tessera in priority_zero:
        tessera['usage_count'] = 0
    
    # Assign sorted remaining parquets using priority 0 tesserae with minimal reuse
    for parquet in tqdm(remaining_parquets_sorted, desc="Priority 0 allocated"):
        # Determine aspect ratio constraints for parquet
        aspect = parquet['width'] / parquet['height']
        valid_aspect = any(abs(aspect - valid) < 0.01 for valid in {1.5, 2/3})
        
        # Filter tesserae based on parquet's aspect ratio
        candidate_tesserae = priority_zero
        if not valid_aspect:
            candidate_tesserae = [t for t in priority_zero if t['cropable'] == 1]
        
        best_tessera, distance = find_best_tessera(parquet["average_color"], candidate_tesserae)
        if best_tessera:
            best_tessera['usage_count'] += 1
            candidates.append(create_candidate_entry(parquet, best_tessera, distance))
    
    # Export results
    export_candidates_to_csv(candidates, candidates_output_path)



def main():
    setup_logging(CONFIG["log_file"])

    start_time = datetime.now()
    log_message(f"Step6 - matching tesserae... @{start_time.strftime('%Y-%m-%d %H:%M:%S')}" )
    
    width_parquet = CONFIG["parquet_unit_width"] * CONFIG["parquet_size_factor"]
    height_parquet = (width_parquet // 3) * 2
    
    tess_dimension = [CONFIG["tessera_width"],CONFIG["tessera_height"]]
    width_tessera = tess_dimension[0]
    scaling_up = width_tessera / width_parquet

    # Process the mosaic
    parquets = read_parquets_csv_stepiv(CONFIG["parquets_csv_path"])
    
    if parquets:
        prepare_mosaic_prioritized_sorted_filtered(parquets, CONFIG["tesserae_index_path"], CONFIG["candidates_output_path"], scaling_up)
    
    end_time = datetime.now()
    log_message(f"Step6 - matching tesserae... done @{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"===Total execution time: {(end_time - start_time).total_seconds():.2f} seconds===" )


if __name__ == "__main__":
    main()
