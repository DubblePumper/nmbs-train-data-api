# Note: This is a hypothetical file as it wasn't provided. 
# You'll need to adapt this to your actual file structure.

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import logging
import pandas as pd
from dotenv import load_dotenv

# Import the new search functionality
from api_search import search_data, optimize_data_for_search

# Import your existing API functions
from nmbs_api import (
    get_realtime_data, 
    get_planning_files_list,
    get_planning_file, 
    force_update
)

# Import the trajectories endpoint functionality
# Update the import statement to use the correct path
from src.nmbs_api.web.trajectories_endpoint import get_trajectories

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute", "10000 per hour"],
    storage_uri="memory://",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache for optimized search data
data_cache = {}
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def init_cache():
    """Initialize the cache with frequently used data"""
    global data_cache
    try:
        # Pre-load and optimize common planning data files
        for filename in ['stops.txt', 'routes.txt', 'calendar.txt']:
            data = get_planning_file(filename)
            if isinstance(data, list):
                optimize_data_for_search(data)
                data_cache[filename] = data
        logger.info("Search cache initialized")
    except Exception as e:
        logger.error(f"Error initializing cache: {e}")

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "NMBS Train Data API"
    })

@app.route('/api/realtime/data')
@limiter.limit("60 per minute")
def realtime_data():
    try:
        data = get_realtime_data()
        
        # Apply search if requested
        if 'search' in request.args and request.args.get('search'):
            data = search_data(
                data=data,
                search_params=request.args.to_dict(),
                data_type='realtime',
                limit=int(request.args.get('limit', 1000))
            )
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in realtime_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/planningdata/<filename>')
def planning_data(filename):
    try:
        # Remove .txt extension if present
        if filename.endswith('.txt'):
            filename = filename[:-4]
        
        # Add .txt extension for file retrieval
        file_with_ext = f"{filename}.txt"
        
        # Get data
        data = get_planning_file(file_with_ext)
        
        # If data is not a list or dict, return it as-is
        if not isinstance(data, (list, dict)):
            return data
        
        # Apply search if requested
        if 'search' in request.args and request.args.get('search'):
            data = search_data(
                data=data,
                search_params=request.args.to_dict(),
                data_type='planning',
                limit=int(request.args.get('limit', 1000))
            )
            
            # Return search results without pagination
            return jsonify({"data": data})
        
        # Handle pagination for regular requests
        page = int(request.args.get('page', 0))
        page_size = min(int(request.args.get('limit', 1000)), 5000)
        
        if isinstance(data, list):
            total = len(data)
            start_idx = page * page_size
            end_idx = min(start_idx + page_size, total)
            
            paginated_data = data[start_idx:end_idx]
            
            return jsonify({
                "data": paginated_data,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "totalRecords": total,
                    "totalPages": (total + page_size - 1) // page_size,
                    "hasNextPage": end_idx < total,
                    "hasPrevPage": page > 0
                }
            })
        else:
            return jsonify(data)
            
    except Exception as e:
        logger.error(f"Error in planning_data: {e}")
        return jsonify({"error": str(e)}), 500

# Add specialized endpoints for common data files
@app.route('/api/planningdata/stops')
def stops_data():
    return planning_data('stops')

@app.route('/api/planningdata/routes')
def routes_data():
    return planning_data('routes')

@app.route('/api/planningdata/calendar')
def calendar_data():
    return planning_data('calendar')

@app.route('/api/planningdata/trips')
def trips_data():
    return planning_data('trips')

@app.route('/api/planningdata/stop_times')
def stop_times_data():
    return planning_data('stop_times')

@app.route('/api/planningdata/calendar_dates')
def calendar_dates_data():
    return planning_data('calendar_dates')

@app.route('/api/planningdata/agency')
def agency_data():
    return planning_data('agency')

@app.route('/api/planningdata/translations')
def translations_data():
    return planning_data('translations')

@app.route('/api/update', methods=['POST'])
@limiter.limit("10 per hour")
def update_data():
    try:
        success = force_update()
        if success:
            # Clear cached data as it's outdated
            data_cache.clear()
            # Re-initialize cache with fresh data
            init_cache()
            return jsonify({
                "status": "success",
                "message": "Data updated successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to update data"
            }), 500
    except Exception as e:
        logger.error(f"Error in update_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/trajectories')
@limiter.limit("60 per minute")
def trajectories_data():
    """Endpoint to get trajectories data (combined train routes with stops and status)"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 0))
        page_size = min(int(request.args.get('limit', 20)), 100)  # Limit page size to avoid overload
        
        # Get trajectories data directly from cache files (faster than using other API endpoints)
        response = get_trajectories(page=page, page_size=page_size)
        
        # If response is a tuple, it contains an error
        if isinstance(response, tuple):
            return jsonify(response[0]), response[1]
            
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in trajectories_data endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# Initialize cache on startup
init_cache()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='NMBS Train Data Web API')
    parser.add_argument('--host', type=str, default=os.getenv('API_HOST', '0.0.0.0'), help='Host to run the API on')
    parser.add_argument('--port', type=int, default=int(os.getenv('API_PORT', 25580)), help='Port to run the API on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    app.run(host=args.host, port=args.port, debug=args.debug)
