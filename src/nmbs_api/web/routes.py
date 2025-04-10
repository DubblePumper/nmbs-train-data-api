"""
Route definitions for the NMBS Train Data API
"""
import logging
import traceback
import json
import os
import datetime
from flask import Blueprint, jsonify, request, redirect, Response
from .utils import extract_request_params
from .security import limiter, run_security_audit
from ..api import (
    get_realtime_data, 
    get_planning_files_list,
    get_planning_file,
    force_update
)
from .cache import CacheManager
from ..tests.test_api import test_api

# Configure logging
logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Register test API routes
api_bp.register_blueprint(test_api, url_prefix='/tests')

# Apply rate limit directly to endpoints that are defined in the api_bp
@api_bp.route('/health', methods=['GET'])
@limiter.limit("60 per minute")
def health():
    """Check if the API is healthy"""
    return jsonify({'status': 'healthy'})

# Create a blueprint for routes
api_routes = Blueprint('api', __name__)

@api_routes.route('/', methods=['GET'])
def root():
    """Root endpoint that redirects to the health check"""
    return redirect('/api/health')

@api_routes.route('/health', methods=['GET'])
@limiter.limit("60 per minute")
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
@api_routes.route('/realtime/data', methods=['GET'])
@limiter.limit("30 per minute")
def get_realtime_data_endpoint():
    """
    Get the latest real-time train data with track changes
    """
    try:
        # Get the data
        data = get_realtime_data()
        
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "No realtime data available"}), 404
    except Exception as e:
        logger.error(f"Error getting realtime data: {str(e)}")
        return jsonify({"error": "Error processing request", "message": str(e)}), 500

# Planning data endpoints
@api_routes.route('/planningdata/files', methods=['GET'])
@limiter.limit("60 per minute")
def get_planning_files_endpoint():
    """
    Get a list of all available planning data files
    """
    try:
        files = get_planning_files_list()
        
        if files:
            return jsonify({"files": files})
        else:
            return jsonify({"error": "No planning data files available"}), 404
    except Exception as e:
        logger.error(f"Error getting planning files: {str(e)}")
        return jsonify({"error": "Error processing request", "message": str(e)}), 500

@api_routes.route('/planningdata/data', methods=['GET'])
@limiter.limit("60 per minute")
def get_all_planning_data():
    """
    Get a combined response with references to all planning data endpoints
    """
    try:
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
    except Exception as e:
        logger.error(f"Error getting all planning data: {str(e)}")
        return jsonify({"error": "Error processing request", "message": str(e)}), 500

@api_routes.route('/planningdata/<filename>', methods=['GET'])
@limiter.limit("45 per minute")
def get_specific_planning_file(filename):
    """
    Get content from a specific planning data file
    
    Args:
        filename: The name of the file to fetch (with or without extension)
        
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Field to search in
        <search> (str): Value to filter by for the specified search field
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    try:
        # Extract request parameters using our improved utility
        params = extract_request_params()
        
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

# Direct endpoints for common GTFS files with auto-filling filename extensions

@api_routes.route('/planningdata/stops', methods=['GET'])
@limiter.limit("45 per minute")
def get_stops_data():
    """
    Get the stops.txt data with station information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Field to search in (e.g., 'stop_name')
        <search> (str): Value to filter by for the specified search field
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    try:
        # Extract request parameters
        params = extract_request_params()
        
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

@api_routes.route('/planningdata/routes', methods=['GET'])
@limiter.limit("45 per minute")
def get_routes_data():
    """
    Get the routes.txt data with route information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Field to search in (e.g., 'route_long_name')
        <search> (str): Value to filter by for the specified search field
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    try:
        # Extract request parameters
        params = extract_request_params()
        
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

@api_routes.route('/planningdata/calendar', methods=['GET'])
@limiter.limit("45 per minute")
def get_calendar_data():
    """
    Get the calendar.txt data with service calendar information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Field to search in (e.g., 'service_id', 'monday', etc.)
        <search> (str): Value to filter by for the specified search field
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    try:
        # Extract request parameters
        params = extract_request_params()
        
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

@api_routes.route('/planningdata/trips', methods=['GET'])
@limiter.limit("45 per minute")
def get_trips_data():
    """
    Get the trips.txt data with trip information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Field to search in (e.g., 'route_id', 'trip_id', etc.)
        <search> (str): Value to filter by for the specified search field
        sort_by (str): Field to sort by
        sort_direction (str): Sort direction (asc or desc)
    """
    try:
        # Extract request parameters
        params = extract_request_params()
        
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

@api_routes.route('/planningdata/stop_times', methods=['GET'])
@limiter.limit("30 per minute")
def get_stop_times_data():
    """
    Get the stop_times.txt data with stop time information
    
    Query Parameters:
        page (int): Page number starting from 0 (default: 0)
        limit (int): Number of records per page (default: 1000, max: 5000)
        search (str): Field to search in (e.g., 'stop_id', 'trip_id', etc.)
        <search> (str): Value to filter by for the specified search field
        sort_by (str): Field to sort by (e.g., 'arrival_time')
        sort_direction (str): Sort direction (asc or desc)
    """
    try:
        # Extract request parameters
        params = extract_request_params()
        
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

# Add more standard GTFS file endpoints
@api_routes.route('/planningdata/calendar_dates', methods=['GET'])
@limiter.limit("45 per minute")
def get_calendar_dates_data():
    """Get the calendar_dates.txt data with exception dates"""
    return get_specific_planning_file('calendar_dates')

@api_routes.route('/planningdata/agency', methods=['GET'])
@limiter.limit("45 per minute")
def get_agency_data():
    """Get the agency.txt data with carrier information"""
    return get_specific_planning_file('agency')

@api_routes.route('/planningdata/translations', methods=['GET'])
@limiter.limit("45 per minute")
def get_translations_data():
    """Get the translations.txt data with translation information"""
    return get_specific_planning_file('translations')

# Cache endpoints
@api_routes.route('/cache/<data_type>', methods=['GET'])
@limiter.limit("60 per minute")
def get_cached_data(data_type):
    """
    Get cached data (first 25 records) for faster access
    
    Args:
        data_type: The type of data to retrieve (e.g., 'stops', 'routes', 'realtime')
    """
    try:
        # Check if the cache file exists
        cache_file = os.path.join('data', f"{data_type}_cache.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            logger.info(f"Returned cached data for {data_type}")
            return jsonify(cached_data)
        else:
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

@api_routes.route('/cache', methods=['GET'])
@limiter.limit("90 per minute")
def get_available_cache():
    """
    Get a list of available cached data types
    """
    try:
        cache_files = [f.replace('_cache.json', '') for f in os.listdir('data') if f.endswith('_cache.json')]
        
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
@api_routes.route('/data', methods=['GET'])
def get_data():
    """
    [DEPRECATED] This endpoint is no longer available.
    Users should migrate to the new endpoints.
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

@api_routes.route('/update', methods=['POST'])
@limiter.limit("5 per minute")
def update_data_endpoint():
    """Force an immediate update of the data"""
    try:
        success = force_update()
        
        if success:
            return jsonify({"status": "success", "message": "Data updated successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to update data"}), 500
    except Exception as e:
        logger.error(f"Error updating data: {str(e)}")
        return jsonify({"error": "Error updating data", "message": str(e)}), 500

@api_routes.route('/security/audit', methods=['GET'])
@limiter.limit("10 per minute")
def security_audit_endpoint():
    """
    Run a security audit and return the results
    
    This endpoint provides information about the security configuration
    of the API including rate limits, input validation, and security headers.
    """
    try:
        # Run the security audit
        audit_results = run_security_audit()
        
        # Return the results as JSON
        return jsonify(audit_results)
    except Exception as e:
        logger.error(f"Error running security audit: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Error running security audit",
            "message": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 500