import subprocess
import json
import os
import nbformat
from flask import Flask, render_template, request, jsonify
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#app = Flask(__name__)
app = Flask(__name__, template_folder='templates')

def get_config():
    """Load and validate configuration with dynamic path resolution"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("Configuration file not found. Creating default config.")
        return create_default_config()
    
    # Resolve paths using user's home directory
    base_path = os.path.expanduser(config['base_path'])
    base_path = os.path.normpath(base_path)  # Normalize path
    
    # Update configuration paths
    config['base_path'] = base_path
    config['tile_folder'] = os.path.join(base_path, 'tiles')
    config['tesserae_folder'] = os.path.join(base_path, 'tesserae')
    config['index_folder'] = os.path.join(base_path, 'index-n-log')
    config['image_path'] = os.path.join(base_path, 'motif', 'input.jpg')
    config['output_path'] = os.path.join(base_path, 'mosaics')
    config['parquets_csv_path'] = os.path.normpath(os.path.join(base_path, config['parquets_csv_path']))
    config['tesserae_index_path'] = os.path.normpath(os.path.join(base_path, config['tesserae_index_path']))
    config['candidates_output_path'] = os.path.normpath(os.path.join(base_path, config['candidates_output_path']))
    
    # Validate required keys
    required = [
        'imode', 'parquet_size_factor', 'randomness_percentage', 'parquet_unit_width',
        'force_refresh', 'base_path', 'parquets_csv_path',
        'tesserae_index_path', 'candidates_output_path', "merge_diff", 
        "split_diff", "optional_tesserae", "mosaic_anime",
        "tessera_width", "tessera_height"
    ]
    
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config: {key}")
    
    return config

def create_default_config():
    """Create default configuration file if missing"""
    home = str(Path.home())
    default_config = {
        "imode": 0,
        "parquet_size_factor": 25,
        "randomness_percentage": 87,
        "parquet_unit_width": 6,
        "force_refresh": False,
        "base_path": "~/mosaicsmith",
        "parquets_csv_path": "index-n-log/parquets.csv",
        "tesserae_index_path": "index-n-log/tesserae_index.csv",
        "candidates_output_path": "index-n-log/candidates_index.csv",
        "merge_diff": 32,
        "split_diff": 16,
        "optional_tesserae": False,
        "mosaic_anime": False,
        "tessera_width": 240,
        "tessera_height": 160
    }
    
    # Resolve paths before saving
    default_config['base_path'] = os.path.expanduser(default_config['base_path'])
    os.makedirs(default_config['base_path'], exist_ok=True)
    
    with open('config.json', 'w') as f:
        json.dump(default_config, f, indent=2)
        
    return default_config

@app.route('/')
def index():
    config = get_config()
    return render_template('index.html', config=config)  # Ensure 'index.html' is in templates/


@app.route('/update_config', methods=['POST'])
def update_config():
    new_config = request.json
    try:
        # Load current configuration
        with open('config.json', 'r') as f:
            current_config = json.load(f)
        
        # Define allowed keys and their expected types
        allowed_keys = [
            'imode', 'parquet_size_factor', 'randomness_percentage', 
            'parquet_unit_width', 'force_refresh',  # Add force_refresh
            'merge_diff', 'split_diff', 'optional_tesserae',
            'mosaic_anime', 'tessera_width', 'tessera_height'  # Add tessera_width/height
        ]
        type_validations = {
            'imode': int,
            'parquet_size_factor': int,
            'randomness_percentage': int,  # New parameter
            'parquet_unit_width': int,
            'merge_diff': int,
            'split_diff': int,
            'optional_tesserae': bool,
            'mosaic_anime': bool,
            'tessera_width': int,
            'tessera_height': int,
            'force_refresh': bool
        }
        
        # Validate and update keys
        for key, value in new_config.items():
            if key not in allowed_keys:
                return jsonify({'status': 'error', 'message': f"Disallowed key: {key}"})
            if not isinstance(value, type_validations[key]):
                return jsonify({'status': 'error', 'message': f"Invalid type for {key}. Expected {type_validations[key].__name__}."})

            current_config[key] = value
        
        # Save updated configuration
        with open('config.json', 'w') as f:
            json.dump(current_config, f, indent=2)
        
        return jsonify(success=True)
    
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'Configuration file not found.'})
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Invalid JSON format in configuration file.'})
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/run_step/<int:step>', methods=['POST'])
def run_step(step):
    try:
        # Get the force_refresh parameter from the request
        data = request.get_json()
        force_refresh = data.get('force_refresh', False)

        # Map step numbers to their respective Python scripts
        script_map = {
            1: 'step1.py',
            2: 'step2.py',
            3: 'step3.py',
            4: 'step4.py',
            5: 'step5.py',
            6: 'step6.py',
            7: 'step7.py',
            8: 'undo.py',  # Example for undo functionality
            9: 'backup.py'  # Example for backup functionality
        }

        # Check if the requested step exists in the map
        if step not in script_map:
            return jsonify({'status': 'error', 'message': f'Step {step} not found.'}), 404

        # Execute the corresponding Python script
        script_path = script_map[step]
        command = ['python', script_path]

        # Add force_refresh as an argument if needed
        if force_refresh:
            command.append('--force_refresh')

        # Run the script and capture the output
        result = subprocess.run(command, capture_output=True, text=True)

        # Check if the script executed successfully
        if result.returncode == 0:
            outputs = result.stdout.splitlines()
            return jsonify({'status': 'success', 'outputs': outputs})
        else:
            error_message = result.stderr.strip() or 'Unknown error occurred.'
            return jsonify({'status': 'error', 'message': error_message}), 500

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/test', methods=['POST'])
def test():
    """Test endpoint to confirm frontend-backend communication"""
    try:
        data = request.get_json()
        logger.info(f"Test endpoint received: {data}")
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # Ensure config exists
    if not os.path.exists('config.json'):
        create_default_config()
    
    app.run(debug=True, port=5000, use_reloader=False)