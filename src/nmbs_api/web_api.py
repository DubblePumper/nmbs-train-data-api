from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from .api import get_realtime_data, start_data_service, force_update

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nmbs_web_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Start the background data service
data_service_thread = None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "service": "NMBS Train Data API"})

@app.route('/api/data', methods=['GET'])
def get_data():
    """
    Get the latest train data
    
    Query parameters:
    - track_changes: Whether to include track change information (default: true)
    """
    track_changes = request.args.get('track_changes', 'true').lower() != 'false'
    
    # Get the data
    data = get_realtime_data(include_track_changes=track_changes)
    
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No data available"}), 404

@app.route('/api/update', methods=['POST'])
def update_data():
    """Force an immediate update of the data"""
    success = force_update()
    
    if success:
        return jsonify({"status": "success", "message": "Data updated successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to update data"}), 500

def start_web_server(host='0.0.0.0', port=5000, debug=False):
    """
    Start the Flask web server
    
    Args:
        host (str): Host to bind to
        port (int): Port to bind to
        debug (bool): Whether to run in debug mode
    """
    global data_service_thread
    
    # Start the data service if not already started
    if data_service_thread is None:
        logger.info("Starting NMBS data service...")
        data_service_thread = start_data_service()
    
    # Start the Flask app
    logger.info(f"Starting NMBS web API on {host}:{port}...")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    start_web_server()