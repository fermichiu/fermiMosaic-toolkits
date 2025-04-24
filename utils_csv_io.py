#this common helper functinon need for each step*.py
import os
import csv

#common helper functions for this project, utils.py saved in the same folder
from utils import *


def parse_tuple(value, dtype=float):
    """Parses a string representation of a tuple into an actual tuple."""
    return tuple(dtype(x.strip()) for x in value.strip('()').split(','))

def parse_row(row):
    """Parses a single row from tesserae_index.csv into a structured dictionary."""
    return {
        'image_path': row['Image Path'],
        'average_color': parse_tuple(row['Average Color']),
        'original_dimensions': parse_tuple(row['Original Dimensions'], int),
        'orientation': row['Orientation'],
        'top_left_color': parse_tuple(row['Top-Left Color']),
        'top_right_color': parse_tuple(row['Top-Right Color']),
        'bottom_left_color': parse_tuple(row['Bottom-Left Color']),
        'bottom_right_color': parse_tuple(row['Bottom-Right Color']),
        'priority': int(row['Priority']),
        'cropable': int(row['Cropable'])
    }

def write_tesserae_index_file(index_file, index_data):
    os.makedirs(os.path.dirname(index_file), exist_ok=True)
    with open(index_file, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Image Path', 'Average Color', 'Original Dimensions', 'Orientation',
                           'Top-Left Color', 'Top-Right Color', 'Bottom-Left Color', 'Bottom-Right Color',
                           'Priority', 'Cropable'])
        csvwriter.writerows(index_data)

def read_tesserae_index_file(csv_path):
    """
    Reads and parses the tesserae_index.csv file.
    Args:
        csv_path (str): Path to the tesserae_index.csv file.
    Returns:
        list: A list of dictionaries, where each dictionary represents a tessera.
    """
    tesserae = []
    try:
        with open(csv_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tessera = parse_row(row)
                tesserae.append(tessera)
        
        print(f"Successfully read {len(tesserae)} tesserae from {csv_path}")
        return tesserae
    except Exception as e:
        print(f"Error reading tesserae index file: {str(e)}")
        return None

import shutil
def backup_file(source, destination):
    """Backup a file from source to destination."""
    try:
        shutil.copy(source, destination)
        logging.info(f"Copied: {source} -> {destination}")
    except PermissionError:
        log_message("Error: Permission denied while copying files.")
    except Exception as e:
        log_message(f"Unexpected error during copying: {e}")

def save_parquet_csv(filtered, csv_path):
    """
    Save the filtered parquet data to a CSV file.
    Args:
        filtered (list): List of dictionaries containing parquet data.
        csv_path (str): Path to the output CSV file.
    Returns:
        None
    """
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'x1', 'y1', 'x2', 'y2', 
            'x3', 'y3', 'x4', 'y4',
            'avg_r', 'avg_g', 'avg_b',
            'on_the_edge',
            'orientation',
            'priority',
            'tl_r', 'tl_g', 'tl_b',
            'tr_r', 'tr_g', 'tr_b',
            'bl_r', 'bl_g', 'bl_b',
            'br_r', 'br_g', 'br_b'
        ])
        writer.writeheader()
        for p in filtered:
            coords = p["coordinates"]
            writer.writerow({
                'x1': float(coords[0][0]),  # Convert to float
                'y1': float(coords[0][1]),
                'x2': float(coords[1][0]),
                'y2': float(coords[1][1]),
                'x3': float(coords[2][0]),
                'y3': float(coords[2][1]),
                'x4': float(coords[3][0]),
                'y4': float(coords[3][1]),
                'avg_r': p["average_color"][0],
                'avg_g': p["average_color"][1],
                'avg_b': p["average_color"][2],
                'on_the_edge': p["on_the_edge"],
                'orientation': p["orientation"],
                'priority': p["priority"],
                'tl_r': p["top_left_color"][0],
                'tl_g': p["top_left_color"][1],
                'tl_b': p["top_left_color"][2],
                'tr_r': p["top_right_color"][0],
                'tr_g': p["top_right_color"][1],
                'tr_b': p["top_right_color"][2],
                'bl_r': p["bottom_left_color"][0],
                'bl_g': p["bottom_left_color"][1],
                'bl_b': p["bottom_left_color"][2],
                'br_r': p["bottom_right_color"][0],
                'br_g': p["bottom_right_color"][1],
                'br_b': p["bottom_right_color"][2]
            })


###from step4.py reading parquet information, where coordinates are floats
### this same applies to step5.py
def read_csv_with_coordinates(csv_path, coordinate_fields, color_fields, other_fields):
    """Read CSV with float coordinates"""
    items = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = {
                    "coordinates": [
                        (float(row[coordinate_fields[0]]), float(row[coordinate_fields[1]])),
                        (float(row[coordinate_fields[2]]), float(row[coordinate_fields[3]])),
                        (float(row[coordinate_fields[4]]), float(row[coordinate_fields[5]])),
                        (float(row[coordinate_fields[6]]), float(row[coordinate_fields[7]]))
                    ],
                    "average_color": (
                        int(row[color_fields["avg"][0]]),
                        int(row[color_fields["avg"][1]]),
                        int(row[color_fields["avg"][2]]))
                }
                # Add corner colors
                for corner in ["top_left", "top_right", "bottom_left", "bottom_right"]:
                    item[f"{corner}_color"] = (
                        int(row[color_fields[corner][0]]),
                        int(row[color_fields[corner][1]]),
                        int(row[color_fields[corner][2]])
                    )
                # Add other fields
                for field_name, field_type in other_fields.items():
                    item[field_name] = field_type(row[field_name])
                items.append(item)
        print(f"Successfully read {len(items)} items from {csv_path}")
        return items
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        return None

def read_parquets_csv(csv_path):
    """Read parquets CSV with float coordinates"""
    coordinate_fields = ['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4']
    color_fields = {
        "avg": ['avg_r', 'avg_g', 'avg_b'],
        "top_left": ['tl_r', 'tl_g', 'tl_b'],
        "top_right": ['tr_r', 'tr_g', 'tr_b'],
        "bottom_left": ['bl_r', 'bl_g', 'bl_b'],
        "bottom_right": ['br_r', 'br_g', 'br_b']
    }
    other_fields = {
        "on_the_edge": int,
        "orientation": str,
        "priority": int
    }
    return read_csv_with_coordinates(csv_path, coordinate_fields, color_fields, other_fields)

### from step4




####from step6 this is different from step4  #### coordinates type cast from float to int
def read_parquets_csv_stepiv(csv_path):
    """Read parquets CSV and calculate dimensions with tuple parsing"""
    coordinate_fields = ['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4']
    color_fields = {
        "avg": ['avg_r', 'avg_g', 'avg_b'],
        "top_left": ['tl_r', 'tl_g', 'tl_b'],
        "top_right": ['tr_r', 'tr_g', 'tr_b'],
        "bottom_left": ['bl_r', 'bl_g', 'bl_b'],
        "bottom_right": ['br_r', 'br_g', 'br_b']
    }
    other_fields = {
        "on_the_edge": int,
        "orientation": str,
        "priority": int
    }
    parquets = read_csv_with_coordinates(csv_path, coordinate_fields, color_fields, other_fields)
    
    valid_parquets = []
    for pq in parquets:
        # Flatten coordinate tuples
        coords = []
        for coord_pair in pq['coordinates']:
            if isinstance(coord_pair, (tuple, list)) and len(coord_pair) == 2:
                coords.extend([int(coord_pair[0]), int(coord_pair[1])])
            else:
                print(f"Invalid coordinate format: {coord_pair}")
                break
        else:
            if len(coords) == 8:
                # Calculate dimensions
                x1, y1, x2, y2, x3, y3, x4, y4 = coords
                pq['width'] = abs(x3 - x1)
                pq['height'] = abs(y3 - y1)
                valid_parquets.append(pq)
            else:
                print(f"Skipping parquet with incomplete coordinates: {pq['coordinates']}")    
    return valid_parquets

####from step6 this is different ffrom step4


###from step6
def export_candidates_to_csv(candidates, output_path):
    """Export the candidates list to a CSV file with all required fields."""
    fieldnames = [
        'x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4',
        'on_the_edge', 'orientation',
        # Parquet colors
        'parquet_avg_r', 'parquet_avg_g', 'parquet_avg_b',
        'parquet_tl_r', 'parquet_tl_g', 'parquet_tl_b',
        'parquet_tr_r', 'parquet_tr_g', 'parquet_tr_b',
        'parquet_bl_r', 'parquet_bl_g', 'parquet_bl_b',
        'parquet_br_r', 'parquet_br_g', 'parquet_br_b',
        # Tessera colors
        'tessera_avg_r', 'tessera_avg_g', 'tessera_avg_b',
        'tessera_tl_r', 'tessera_tl_g', 'tessera_tl_b',
        'tessera_tr_r', 'tessera_tr_g', 'tessera_tr_b',
        'tessera_bl_r', 'tessera_bl_g', 'tessera_bl_b',
        'tessera_br_r', 'tessera_br_g', 'tessera_br_b',
        # Candidate info
        'candidate_path', 'candidate_score'
    ]
    
    try:
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for candidate in candidates:
                coords = candidate["coordinates"]
                row = {
                    'x1': coords[0][0], 'y1': coords[0][1],
                    'x2': coords[1][0], 'y2': coords[1][1],
                    'x3': coords[2][0], 'y3': coords[2][1],
                    'x4': coords[3][0], 'y4': coords[3][1],
                    'on_the_edge': candidate["on_the_edge"],
                    'orientation': candidate["orientation"],
                    # Candidate info
                    'candidate_path': candidate["candidate"]["image_path"],
                    'candidate_score': candidate["candidate"]["score"]
                }
                
                # Add parquet colors
                pc = candidate["parquet_colors"]
                row.update({
                    'parquet_avg_r': pc["average"][0],
                    'parquet_avg_g': pc["average"][1],
                    'parquet_avg_b': pc["average"][2],
                    'parquet_tl_r': pc["top_left"][0],
                    'parquet_tl_g': pc["top_left"][1],
                    'parquet_tl_b': pc["top_left"][2],
                    'parquet_tr_r': pc["top_right"][0],
                    'parquet_tr_g': pc["top_right"][1],
                    'parquet_tr_b': pc["top_right"][2],
                    'parquet_bl_r': pc["bottom_left"][0],
                    'parquet_bl_g': pc["bottom_left"][1],
                    'parquet_bl_b': pc["bottom_left"][2],
                    'parquet_br_r': pc["bottom_right"][0],
                    'parquet_br_g': pc["bottom_right"][1],
                    'parquet_br_b': pc["bottom_right"][2]
                })
                
                # Add tessera colors
                tc = candidate["candidate"]["tessera_colors"]
                row.update({
                    'tessera_avg_r': tc["average"][0],
                    'tessera_avg_g': tc["average"][1],
                    'tessera_avg_b': tc["average"][2],
                    'tessera_tl_r': tc["top_left"][0],
                    'tessera_tl_g': tc["top_left"][1],
                    'tessera_tl_b': tc["top_left"][2],
                    'tessera_tr_r': tc["top_right"][0],
                    'tessera_tr_g': tc["top_right"][1],
                    'tessera_tr_b': tc["top_right"][2],
                    'tessera_bl_r': tc["bottom_left"][0],
                    'tessera_bl_g': tc["bottom_left"][1],
                    'tessera_bl_b': tc["bottom_left"][2],
                    'tessera_br_r': tc["bottom_right"][0],
                    'tessera_br_g': tc["bottom_right"][1],
                    'tessera_br_b': tc["bottom_right"][2]
                })
                
                writer.writerow(row)

        print(f"Candidates index saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving candidates index: {str(e)}")
        return False

###from step6


###from step7 a generic csv reader for step7.py
def read_csv_file(csv_path, row_processor):
    """Generic CSV reader that processes each row with the given function."""
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            return [row_processor(row) for row in reader]
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        return None

def process_candidate_row(row):
    """Process a single row from candidates.csv"""
    def to_int_color(color_str):
        try: return int(float(color_str))
        except (ValueError, TypeError): return 0
    
    return {
        'coords': [(int(row['x1']), int(row['y1'])), (int(row['x2']), int(row['y2'])),
                 (int(row['x3']), int(row['y3'])), (int(row['x4']), int(row['y4']))],
        'on_edge': int(row['on_the_edge']),
        'orientation': row['orientation'],
        'parquet_colors': {
            'average': (to_int_color(row['parquet_avg_r']), to_int_color(row['parquet_avg_g']), to_int_color(row['parquet_avg_b'])),
            'top_left': (to_int_color(row['parquet_tl_r']), to_int_color(row['parquet_tl_g']), to_int_color(row['parquet_tl_b'])),
            'top_right': (to_int_color(row['parquet_tr_r']), to_int_color(row['parquet_tr_g']), to_int_color(row['parquet_tr_b'])),
            'bottom_left': (to_int_color(row['parquet_bl_r']), to_int_color(row['parquet_bl_g']), to_int_color(row['parquet_bl_b'])),
            'bottom_right': (to_int_color(row['parquet_br_r']), to_int_color(row['parquet_br_g']), to_int_color(row['parquet_br_b']))
        },
        'candidate': {
            'image_path': row['candidate_path'],
            'score': float(row['candidate_score']),
            'tessera_colors': {
                'average': (to_int_color(row['tessera_avg_r']), to_int_color(row['tessera_avg_g']), to_int_color(row['tessera_avg_b'])),
                'top_left': (to_int_color(row['tessera_tl_r']), to_int_color(row['tessera_tl_g']), to_int_color(row['tessera_tl_b'])),
                'top_right': (to_int_color(row['tessera_tr_r']), to_int_color(row['tessera_tr_g']), to_int_color(row['tessera_tr_b'])),
                'bottom_left': (to_int_color(row['tessera_bl_r']), to_int_color(row['tessera_bl_g']), to_int_color(row['tessera_bl_b'])),
                'bottom_right': (to_int_color(row['tessera_br_r']), to_int_color(row['tessera_br_g']), to_int_color(row['tessera_br_b']))
            }
        }
    }

def read_candidates_csv(csv_path):   #called in step7.py
    """Read candidates.csv using generic CSV reader"""
    candidates = read_csv_file(csv_path, process_candidate_row)
    if candidates: print(f"Successfully read {len(candidates)} candidates from {csv_path}")
    return candidates

#########################spared
def process_tessera_row(row):
    """Process a single row from tesserae_index.csv"""
    return {
        'image_path': row['Image Path'],
        'average_color': tuple(float(x) for x in row['Average Color'].strip('()').split(',')),
        'original_dimensions': tuple(map(int, row['Original Dimensions'].strip('()').split(','))),
        'orientation': row['Orientation'],
        'top_left_color': tuple(float(x) for x in row['Top-Left Color'].strip('()').split(',')),
        'top_right_color': tuple(float(x) for x in row['Top-Right Color'].strip('()').split(',')),
        'bottom_left_color': tuple(float(x) for x in row['Bottom-Left Color'].strip('()').split(',')),
        'bottom_right_color': tuple(float(x) for x in row['Bottom-Right Color'].strip('()').split(',')),
        'priority': int(row['Priority']),
        'cropable': int(row['Cropable'])
    }


def process_parquet_row(row):
    """Process a single row from parquets.csv"""
    return {
        "coordinates": [
            (int(row['x1']), int(row['y1'])),
            (int(row['x2']), int(row['y2'])),
            (int(row['x3']), int(row['y3'])),
            (int(row['x4']), int(row['y4']))
        ],
        "average_color": (int(row['avg_r']), int(row['avg_g']), int(row['avg_b'])),
        "on_the_edge": int(row["on_the_edge"]),
        "orientation": row["orientation"],
        "priority": int(row["priority"]),
        "top_left_color": (int(row['tl_r']), int(row['tl_g']), int(row['tl_b'])),
        "top_right_color": (int(row['tr_r']), int(row['tr_g']), int(row['tr_b'])),
        "bottom_left_color": (int(row['bl_r']), int(row['bl_g']), int(row['bl_b'])),
        "bottom_right_color": (int(row['br_r']), int(row['br_g']), int(row['br_b']))
    }

def read_parquets_csv_stepvii(csv_path): #never called
    """Read parquets.csv using generic CSV reader"""
    parquets = read_csv_file(csv_path, process_parquet_row)
    if parquets: print(f"Successfully read {len(parquets)} parquets from {csv_path}")
    return parquets



#####from step7




#####the following functions could be removed later#######
#####the following functions could be removed later#######
#####the following functions could be removed later#######
#####the following functions could be removed later#######

#####the following functions could be removed later#######
#####the following functions could be removed later#######
#####the following functions could be removed later#######
#####the following functions could be removed later#######



