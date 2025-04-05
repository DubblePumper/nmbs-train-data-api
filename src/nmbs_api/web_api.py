from flask import Flask, jsonify, request, redirect, abort
from flask_cors import CORS
import logging
from .api import (
    get_realtime_data, 
    start_data_service, 
    force_update, 
    get_planning_files_list,
    get_planning_file
)

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

# Add support for proxy headers
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# List of allowed domains
ALLOWED_DOMAINS = ['nmbsapi.sanderzijntestjes.be', 'localhost', '127.0.0.1']

# Domain validation middleware
@app.before_request
def validate_domain():
    """Ensure that the API is only accessed through the proper domain name"""
    host = request.host.split(':')[0]  # Remove port if present
    
    # Log the host for debugging
    logger.debug(f"Request received from host: {host}")
    
    # Allow access if the host is in the allowed domains
    if host in ALLOWED_DOMAINS:
        return None
    
    # For direct IP access, we block it
    logger.warning(f"Unauthorized access attempt from host: {host}")
    return jsonify({
        "error": "Access denied",
        "message": "This API is only accessible via https://nmbsapi.sanderzijntestjes.be/",
        "redirect": "https://nmbsapi.sanderzijntestjes.be/"
    }), 403  # Forbidden

@app.route('/', methods=['GET'])
def root():
    """Root endpoint that redirects to the health check"""
    return redirect('/api/health')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    host = request.headers.get('Host', 'unknown')
    logger.info(f"Health check received from host: {host}")
    return jsonify({
        "status": "healthy", 
        "service": "NMBS Train Data API",
        "host": host
    })

# Realtime data endpoints
@app.route('/api/realtime/data', methods=['GET'])
def get_realtime_data_endpoint():
    """
    Get the latest real-time train data with track changes
    """
    # Get the data
    data = get_realtime_data()
    
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No realtime data available"}), 404

# Planning data endpoints
@app.route('/api/planningdata/files', methods=['GET'])
def get_planning_files():
    """
    Get a list of all available planning data files
    """
    files = get_planning_files_list()
    
    if files:
        return jsonify({"files": files})
    else:
        return jsonify({"error": "No planning data files available"}), 404

@app.route('/api/planningdata/data', methods=['GET'])
def get_all_planning_data():
    """
    Get a combined response with references to all planning data endpoints
    """
    files = get_planning_files_list()
    
    if not files:
        return jsonify({"error": "No planning data available"}), 404
    
    # Create a response with URLs to each file endpoint
    base_url = request.host_url.rstrip('/')
    file_urls = {}
    
    for file in files:
        file_name = file.split('.')[0]  # Remove extension
        file_urls[file_name] = f"{base_url}/api/planningdata/{file_name}"
    
    return jsonify({
        "message": "Planning data available at the following endpoints",
        "files": files,
        "endpoints": file_urls
    })

@app.route('/api/planningdata/<filename>', methods=['GET'])
def get_specific_planning_file(filename):
    """
    Get content from a specific planning data file
    
    Args:
        filename: The name of the file to fetch (with or without extension)
    """
    # Check if filename already has an extension
    if '.' not in filename:
        # Check for various extensions
        possible_extensions = ['.txt', '.csv', '.cfg']
        found_file = None
        
        for ext in possible_extensions:
            file_with_ext = f"{filename}{ext}"
            files = get_planning_files_list()
            
            if file_with_ext in files:
                found_file = file_with_ext
                break
            
            # Special case for transfers.txt which might be named stops.txt_transfers.txt
            if filename == 'transfers':
                special_name = 'stops.txt_transfers.txt'
                if special_name in files:
                    found_file = special_name
                    break
        
        if not found_file:
            return jsonify({"error": f"Planning file '{filename}' not found"}), 404
        
        filename = found_file
    
    # Get the file content
    data = get_planning_file(filename)
    
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": f"Could not parse planning file '{filename}'"}), 404

# Direct endpoints for common GTFS files
@app.route('/api/planningdata/stops', methods=['GET'])
def get_stops_data():
    """Get the stops.txt data with station information"""
    data = get_planning_file('stops.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No stops data available"}), 404

@app.route('/api/planningdata/routes', methods=['GET'])
def get_routes_data():
    """Get the routes.txt data with route information"""
    data = get_planning_file('routes.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No routes data available"}), 404

@app.route('/api/planningdata/calendar', methods=['GET'])
def get_calendar_data():
    """Get the calendar.txt data with service calendar information"""
    data = get_planning_file('calendar.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No calendar data available"}), 404

@app.route('/api/planningdata/trips', methods=['GET'])
def get_trips_data():
    """Get the trips.txt data with trip information"""
    data = get_planning_file('trips.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No trips data available"}), 404

@app.route('/api/planningdata/stop_times', methods=['GET'])
def get_stop_times_data():
    """Get the stop_times.txt data with stop time information"""
    data = get_planning_file('stop_times.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No stop times data available"}), 404

@app.route('/api/planningdata/calendar_dates', methods=['GET'])
def get_calendar_dates_data():
    """Get the calendar_dates.txt data with exception dates"""
    data = get_planning_file('calendar_dates.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No calendar dates data available"}), 404

@app.route('/api/planningdata/agency', methods=['GET'])
def get_agency_data():
    """Get the agency.txt data with agency information"""
    data = get_planning_file('agency.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No agency data available"}), 404

@app.route('/api/planningdata/translations', methods=['GET'])
def get_translations_data():
    """Get the translations.txt data with translation information"""
    data = get_planning_file('translations.txt')
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No translations data available"}), 404

# Compatibility with old endpoint - now redirects to new endpoint with deprecation message
@app.route('/api/data', methods=['GET'])
def get_data():
    """
    [DEPRECATED] This endpoint is no longer available.
    Users should migrate to the new endpoints:
    - /api/realtime/data for real-time train data
    - /api/planningdata/data for planning data
    """
    logger.warning("Deprecated endpoint '/api/data' used. This endpoint is no longer supported.")
    
    # Return a clear error message with redirection information
    return jsonify({
        "error": "Endpoint deprecated",
        "message": "The /api/data endpoint is no longer available. Please use the new endpoints:",
        "new_endpoints": {
            "realtime_data": request.host_url.rstrip('/') + "/api/realtime/data",
            "planning_data": request.host_url.rstrip('/') + "/api/planningdata/data"
        }
    }), 410  # 410 Gone status code

@app.route('/api/update', methods=['POST'])
def update_data():
    """Force an immediate update of the data"""
    success = force_update()
    
    if success:
        return jsonify({"status": "success", "message": "Data updated successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to update data"}), 500

def start_web_server(host='0.0.0.0', port=5000, debug=False, ssl_context=None):
    """
    Start the Flask web server
    
    Args:
        host (str): Host to bind to
        port (int): Port to bind to
        debug (bool): Whether to run in debug mode
        ssl_context: SSL context for HTTPS support, tuple of (cert, key) paths or 'adhoc'
    """
    global data_service_thread
    
    # Start the data service if not already started
    if data_service_thread is None:
        logger.info("Starting NMBS data service...")
        data_service_thread = start_data_service()
    
    # Start the Flask app
    logger.info(f"Starting NMBS web API on {host}:{port}...")
    if ssl_context:
        logger.info("SSL enabled. Running with HTTPS.")
    
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)

if __name__ == '__main__':
    start_web_server()