from flask import Flask, jsonify, request, redirect, abort
from flask_cors import CORS
import logging
import traceback
import json
import os
import threading
import time
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

# Cache for endpoints data
data_dir = "data"
cache_data = {}
cache_lock = threading.Lock()

# Ensure data directory exists
os.makedirs(data_dir, exist_ok=True)

def update_cache():
    """
    Updates the cache for all endpoints with first 25 records every 2 minutes
    """
    logger.info("Starting cache update thread")
    while True:
        try:
            # Get list of planning files
            files = get_planning_files_list()
            
            # Initialize combined cache data
            combined_cache = {
                "realtime": None,
                "planning_data": {}
            }
            
            # Get realtime data for cache
            realtime_data = get_realtime_data()
            if realtime_data:
                with cache_lock:
                    cache_data['realtime'] = realtime_data
                combined_cache["realtime"] = realtime_data
                logger.info("Added realtime data to combined cache")
            
            # Get first 25 records for each planning file
            for file in files:
                file_name = file.split('.')[0]  # Remove extension
                try:
                    # Get the data with pagination (first 25 records)
                    params = {
                        'page': 0,
                        'page_size': 25,
                        'search': {'query': None, 'field': None},
                        'filters': {},
                        'sort': {'field': None, 'direction': 'asc'}
                    }
                    
                    data = get_planning_file(file, page=0, page_size=25, search_params=params)
                    
                    if data:
                        with cache_lock:
                            cache_data[file_name] = data
                        combined_cache["planning_data"][file_name] = data
                        logger.info(f"Added {file_name} data to combined cache")
                except Exception as e:
                    logger.error(f"Error updating cache for {file_name}: {str(e)}")
            
            # Save combined data directly to the data folder
            with open(os.path.join(data_dir, "short-test-data.json"), 'w') as f:
                json.dump(combined_cache, f)
            logger.info("Updated short-test-data.json with all cached data")
            
            # Wait for 2 minutes
            time.sleep(120)
        except Exception as e:
            logger.error(f"Error in cache update thread: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(30)  # Shorter delay if error occurred

# Start cache update thread
cache_thread = threading.Thread(target=update_cache, daemon=True)
cache_thread.start()

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

def _extract_request_params():
    """
    Extract and validate common request parameters for data endpoints
    
    Returns:
        dict: A dictionary with validated parameters
    """
    # Get pagination parameters
    try:
        page = int(request.args.get('page', 0))
        if page < 0:
            page = 0
    except ValueError:
        page = 0
        
    try:
        page_size = int(request.args.get('limit', 1000))
        # Limit page size to reasonable value (between 1 and 5000)
        if page_size < 1:
            page_size = 1
        elif page_size > 5000:
            page_size = 5000
    except ValueError:
        page_size = 1000
    
    # Search parameters
    search_query = request.args.get('search', None)
    search_field = request.args.get('field', None)
    
    # Specific filter parameters for common GTFS fields
    filters = {}
    
    # Stop-related filters
    if request.args.get('stop_id'):
        filters['stop_id'] = request.args.get('stop_id')
    if request.args.get('stop_name'):
        filters['stop_name'] = request.args.get('stop_name')
    
    # Trip and route filters
    if request.args.get('trip_id'):
        filters['trip_id'] = request.args.get('trip_id')
    if request.args.get('route_id'):
        filters['route_id'] = request.args.get('route_id')
    
    # Time filters for stop_times
    if request.args.get('arrival_time'):
        filters['arrival_time'] = request.args.get('arrival_time')
    if request.args.get('departure_time'):
        filters['departure_time'] = request.args.get('departure_time')
    
    # Sort parameters
    sort_by = request.args.get('sort_by', None)
    sort_direction = request.args.get('sort_direction', 'asc').lower()
    if sort_direction not in ['asc', 'desc']:
        sort_direction = 'asc'
    
    return {
        'page': page,
        'page_size': page_size,
        'search': {
            'query': search_query,
            'field': search_field
        },
        'filters': filters,
        'sort': {
            'field': sort_by,
            'direction': sort_direction
        }
    }

@app.route('/api/planningdata/<filename>', methods=['GET'])
def get_specific_planning_file(filename):
    """
    Get content from a specific planning data file
    
    Args:
        filename: The name of the file to fetch (with or without extension)
        
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter records
        field (str): Specific field to search in
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
        stop_id, trip_id, etc: Direct field filters
    """
    # Extract request parameters
    params = _extract_request_params()
    
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
    
    try:
        # Log request details
        logger.info(f"Fetching planning file: {filename}")
        logger.info(f"Pagination: page={params['page']}, limit={params['page_size']}")
        if params['search']['query']:
            logger.info(f"Search: {params['search']['query']} in field {params['search']['field']}")
        if params['filters']:
            logger.info(f"Filters: {params['filters']}")
        
        # Get the file content with pagination
        data = get_planning_file(
            filename, 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": f"Could not parse planning file '{filename}'"}), 404
    except Exception as e:
        logger.error(f"Error processing request for file {filename}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Error processing request", 
            "message": str(e)
        }), 500

# Direct endpoints for common GTFS files
@app.route('/api/planningdata/stops', methods=['GET'])
def get_stops_data():
    """
    Get the stops.txt data with station information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter stops by name or ID
        field (str): Specific field to search in (e.g., 'stop_name')
        sort_by (str): Field to sort by (e.g., 'stop_name')
        sort_direction (str): Sort direction (asc or desc)
        stop_id (str): Filter by specific stop_id
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'stops.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No stops data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching stops data: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/routes', methods=['GET'])
def get_routes_data():
    """
    Get the routes.txt data with route information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter routes
        field (str): Specific field to search in (e.g., 'route_long_name')
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
        route_id (str): Filter by specific route_id
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'routes.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No routes data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching routes data: {str(e)}")
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/calendar', methods=['GET'])
def get_calendar_data():
    """
    Get the calendar.txt data with service calendar information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter calendar entries
        field (str): Specific field to search in
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'calendar.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No calendar data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching calendar data: {str(e)}")
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/trips', methods=['GET'])
def get_trips_data():
    """
    Get the trips.txt data with trip information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter trips
        field (str): Specific field to search in
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
        route_id (str): Filter by specific route_id
        trip_id (str): Filter by specific trip_id
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'trips.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No trips data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching trips data: {str(e)}")
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/stop_times', methods=['GET'])
def get_stop_times_data():
    """
    Get the stop_times.txt data with stop time information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter stop times
        field (str): Specific field to search in (e.g., 'stop_id')
        sort_by (str): Field to sort by (e.g., 'arrival_time')
        sort_direction (str): Sort direction (asc or desc)
        stop_id (str): Filter by specific stop_id
        trip_id (str): Filter by specific trip_id
        arrival_time (str): Filter by specific arrival time (format: HH:MM:SS)
        departure_time (str): Filter by specific departure time (format: HH:MM:SS)
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Log the request details for stop_times due to its size
        logger.info(f"Stop Times request - page: {params['page']}, limit: {params['page_size']}")
        if params['filters']:
            logger.info(f"Stop Times filters: {params['filters']}")
        
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'stop_times.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No stop times data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching stop_times data: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/calendar_dates', methods=['GET'])
def get_calendar_dates_data():
    """
    Get the calendar_dates.txt data with exception dates
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter calendar dates
        field (str): Specific field to search in
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'calendar_dates.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No calendar dates data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching calendar_dates data: {str(e)}")
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/agency', methods=['GET'])
def get_agency_data():
    """
    Get the agency.txt data with agency information
    
    Query Parameters:
        search (str): Search text to filter agencies
        field (str): Specific field to search in
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'agency.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No agency data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching agency data: {str(e)}")
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/planningdata/translations', methods=['GET'])
def get_translations_data():
    """
    Get the translations.txt data with translation information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Search text to filter translations
        field (str): Specific field to search in
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    # Extract request parameters
    params = _extract_request_params()
    
    try:
        # Get the data with pagination and search parameters
        data = get_planning_file(
            'translations.txt', 
            page=params['page'], 
            page_size=params['page_size'],
            search_params=params
        )
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No translations data available"}), 404
    except Exception as e:
        logger.error(f"Error fetching translations data: {str(e)}")
        return jsonify({
            "error": "Error processing request", 
            "message": str(e)
        }), 500

@app.route('/api/cache/<data_type>', methods=['GET'])
def get_cached_data(data_type):
    """
    Get cached data (first 25 records) for faster access
    
    Args:
        data_type: The type of data to retrieve (e.g., stops, routes, realtime)
    """
    try:
        # Check if the cache file exists
        cache_file = os.path.join(data_dir, f"{data_type}_cache.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            logger.info(f"Returned cached data for {data_type}")
            return jsonify(cached_data)
        else:
            # Check if we have it in memory
            with cache_lock:
                if data_type in cache_data:
                    logger.info(f"Returned in-memory cached data for {data_type}")
                    return jsonify(cache_data[data_type])
            
            # If not in cache, return a message
            return jsonify({
                "error": f"No cached data available for {data_type}",
                "message": "The cache is updated every 2 minutes. Try again later or use the full data endpoint."
            }), 404
    except Exception as e:
        logger.error(f"Error retrieving cached data for {data_type}: {str(e)}")
        return jsonify({
            "error": "Error retrieving cached data",
            "message": str(e)
        }), 500

@app.route('/api/cache', methods=['GET'])
def get_available_cache():
    """
    Get a list of available cached data types
    """
    try:
        cache_files = [f.replace('_cache.json', '') for f in os.listdir(data_dir) if f.endswith('_cache.json')]
        
        # Create a response with URLs to each cache endpoint
        base_url = request.host_url.rstrip('/')
        cache_urls = {}
        
        for cache_type in cache_files:
            cache_urls[cache_type] = f"{base_url}/api/cache/{cache_type}"
        
        return jsonify({
            "message": "Cached data available (first 25 records of each type)",
            "cache_types": cache_files,
            "endpoints": cache_urls,
            "update_frequency": "Every 2 minutes"
        })
    except Exception as e:
        logger.error(f"Error retrieving available cache: {str(e)}")
        return jsonify({
            "error": "Error retrieving available cache",
            "message": str(e)
        }), 500

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