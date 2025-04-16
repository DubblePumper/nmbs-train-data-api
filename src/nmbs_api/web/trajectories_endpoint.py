"""
Trajectories API Endpoint for NMBS Train Data API
This module provides direct file access to generate train trajectory data
with combined information from multiple data sources.
"""

import json
import logging
import os
import csv
import datetime
from pathlib import Path

# Import pagination settings
from .config import get_pagination_settings

# Configure logging
logger = logging.getLogger(__name__)

# Define directory paths using absolute paths to avoid issues
# Start with the project base directory
BASE_DIR = Path(os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)))

# Define the paths to all needed data directories
CACHE_DIR = BASE_DIR / 'data' / 'cache'
EXTRACTED_DIR = BASE_DIR / 'data' / 'Planning_gegevens' / 'extracted'
REALTIME_DIR = BASE_DIR / 'data' / 'Real-time_gegevens'

logger.info(f"Base directory: {BASE_DIR}")
logger.info(f"Cache directory: {CACHE_DIR}")
logger.info(f"Extracted directory: {EXTRACTED_DIR}")
logger.info(f"Realtime directory: {REALTIME_DIR}")

def format_timestamp(timestamp):
    """Convert Unix timestamp to human-readable format"""
    if timestamp and str(timestamp).isdigit():
        dt = datetime.datetime.fromtimestamp(int(timestamp))
        return dt.strftime("%Y-%m-%d %H:%M:%S (%A)")
    return "Not available"

def load_cache_file(filename):
    """Load a cache file directly from the filesystem"""
    try:
        file_path = CACHE_DIR / filename
        logger.info(f"Looking for cache file at: {file_path}")
        
        if file_path.exists():
            logger.info(f"Found cache file: {filename}")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"Cache file not found: {filename}")
            return None
    except Exception as e:
        logger.error(f"Error loading cache file {filename}: {e}")
        return None

def load_csv_data(filename):
    """Load data from a CSV file in the extracted directory"""
    try:
        file_path = EXTRACTED_DIR / filename
        logger.info(f"Looking for data file at: {file_path}")
        
        if not file_path.exists():
            logger.error(f"Data file not found: {filename}")
            return None
        
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        
        logger.info(f"Successfully loaded {len(data)} records from {filename}")
        return data
    except Exception as e:
        logger.error(f"Error loading data file {filename}: {e}")
        return None

def load_realtime_data():
    """Load realtime data from the JSON file"""
    try:
        # Try different possible filenames for realtime data
        possible_files = [
            'NMBS_realtime_met_spoorveranderingen.json',
            'realtime.json',
            'gtfs_realtime.json'
        ]
        
        for filename in possible_files:
            file_path = REALTIME_DIR / filename
            logger.info(f"Looking for realtime data at: {file_path}")
            
            if file_path.exists():
                logger.info(f"Found realtime data file: {filename}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        logger.error("No realtime data file found after checking all possible names")
        return None
    except Exception as e:
        logger.error(f"Error loading realtime data: {e}")
        return None

def get_trajectories(page=0, page_size=None):
    """
    Get train trajectories data directly from data files
    
    Args:
        page (int): Page number (0-based)
        page_size (int): Number of records per page
        
    Returns:
        dict: Trajectories data with metadata
    """
    try:
        # Get pagination settings from config
        pagination_settings = get_pagination_settings('trajectories')
        default_size = pagination_settings['default_size']
        max_size = pagination_settings['max_size']
        
        # Apply pagination settings if page_size is not provided
        if page_size is None:
            page_size = default_size
        
        # Limit page_size to max_size
        page_size = min(page_size, max_size)
        
        logger.info(f"Generating trajectories data (page={page}, page_size={page_size})")
        logger.info(f"CACHE_DIR exists: {CACHE_DIR.exists()}")
        logger.info(f"EXTRACTED_DIR exists: {EXTRACTED_DIR.exists()}")
        logger.info(f"REALTIME_DIR exists: {REALTIME_DIR.exists()}")
        
        # List all files in the cache directory to help diagnose issues
        if CACHE_DIR.exists():
            cache_files = list(CACHE_DIR.glob("*_cache.json"))
            logger.info(f"Cache directory contains {len(cache_files)} cache files: {[f.name for f in cache_files]}")
        
        # First try to load from cache files
        realtime_data = load_cache_file('realtime_cache.json')
        stops_data = load_cache_file('stops_cache.json')
        trips_data = load_cache_file('trips_cache.json')
        routes_data = load_cache_file('routes_cache.json')
        translations_data = load_cache_file('translations_cache.json')
        
        # If cache files not found, load directly from data files
        if not realtime_data:
            logger.info("Cache files not found, loading directly from data files")
            realtime_data = load_realtime_data()
            stops_data = load_csv_data('stops.txt')
            trips_data = load_csv_data('trips.txt')
            routes_data = load_csv_data('routes.txt')
            translations_data = load_csv_data('translations.txt')
        
        # Check if required data is available
        if not realtime_data:
            logger.error("Realtime data not available")
            return {"error": "Realtime data not available"}, 500
            
        if not stops_data:
            logger.error("Stops data not available")
            return {"error": "Stops data not available"}, 500
            
        if not trips_data:
            logger.error("Trips data not available")
            return {"error": "Trips data not available"}, 500
            
        if not routes_data:
            logger.error("Routes data not available")
            return {"error": "Routes data not available"}, 500
        
        # Process the data to create trajectories
        combined_data = []
        
        # Create a lookup dictionary for faster access
        stops_lookup = {stop.get('stop_id'): stop for stop in stops_data}
        trips_lookup = {trip.get('trip_id'): trip for trip in trips_data}
        routes_lookup = {route.get('route_id'): route for route in routes_data}
        
        # Create translations lookup
        translations_lookup = {}
        if translations_data:
            for item in translations_data:
                if item.get('table_name') == 'stops' and item.get('field_name') == 'stop_name':
                    field_value = item.get('field_value')
                    language = item.get('language')
                    translation = item.get('translation')
                    
                    if field_value and language and translation:
                        if field_value not in translations_lookup:
                            translations_lookup[field_value] = {}
                        translations_lookup[field_value][language] = translation
        
        # Process each entity in the realtime data
        if 'entity' in realtime_data:
            for entity in realtime_data['entity']:
                entity_id = entity.get('id', 'unknown')
                
                # Skip entities without trip updates
                if 'tripUpdate' not in entity or 'trip' not in entity['tripUpdate']:
                    continue
                    
                trip_id = entity['tripUpdate']['trip'].get('tripId')
                if not trip_id:
                    continue
                    
                # Get associated trip and route data
                trip_data = trips_lookup.get(trip_id)
                route_id = trip_data.get('route_id') if trip_data else None
                route_data = routes_lookup.get(route_id) if route_id else None
                
                # Create trajectory object
                trajectory = {
                    "entity_id": entity_id,
                    "trip_id": trip_id,
                    "route": {
                        "route_id": route_id,
                        "route_type": route_data.get("route_short_name") if route_data else None,
                        "route_name": route_data.get("route_long_name") if route_data else "Unknown Route",
                        "agency_id": route_data.get("agency_id") if route_data else None
                    },
                    "trip": {
                        "trip_number": trip_data.get("trip_short_name") if trip_data else None,
                        "trip_headsign": trip_data.get("trip_headsign") if trip_data else None,
                        "service_id": trip_data.get("service_id") if trip_data else None
                    },
                    "stops": []
                }
                
                # Add stops information
                if 'tripUpdate' in entity and 'stopTimeUpdate' in entity['tripUpdate']:
                    for stop_update in entity['tripUpdate']['stopTimeUpdate']:
                        if 'stopId' not in stop_update:
                            continue
                            
                        stop_id = stop_update['stopId']
                        base_stop_id = stop_id.split('_')[0]  # Remove platform number
                        
                        # Get station data
                        station_data = stops_lookup.get(base_stop_id)
                        
                        # Get translations
                        translations = {}
                        if station_data and 'stop_name' in station_data:
                            stop_name = station_data['stop_name']
                            translations = translations_lookup.get(stop_name, {})
                        
                        # Process arrival and departure information
                        arrival = stop_update.get('arrival', {})
                        departure = stop_update.get('departure', {})
                        
                        arrival_time = arrival.get('time') if arrival else None
                        arrival_delay = int(arrival.get('delay', 0)) if arrival else 0
                        arrival_delay_min = arrival_delay // 60 if arrival_delay else 0
                        
                        departure_time = departure.get('time') if departure else None
                        departure_delay = int(departure.get('delay', 0)) if departure else 0
                        departure_delay_min = departure_delay // 60 if departure_delay else 0
                        
                        # Format stop information
                        stop_info = {
                            "stop_id": stop_id,
                            "station": {
                                "name": station_data.get("stop_name") if station_data else "Unknown Station",
                                "location": {
                                    "latitude": station_data.get("stop_lat") if station_data else None,
                                    "longitude": station_data.get("stop_lon") if station_data else None
                                },
                                "translations": translations
                            },
                            "arrival": {
                                "timestamp": arrival_time,
                                "datetime": format_timestamp(arrival_time),
                                "delay_seconds": arrival_delay,
                                "delay_minutes": arrival_delay_min,
                                "status": "on time" if arrival_delay_min == 0 else 
                                         f"delayed by {arrival_delay_min} min" if arrival_delay_min > 0 else
                                         f"early by {abs(arrival_delay_min)} min"
                            } if arrival_time else None,
                            "departure": {
                                "timestamp": departure_time,
                                "datetime": format_timestamp(departure_time),
                                "delay_seconds": departure_delay,
                                "delay_minutes": departure_delay_min,
                                "status": "on time" if departure_delay_min == 0 else 
                                        f"delayed by {departure_delay_min} min" if departure_delay_min > 0 else
                                        f"early by {abs(departure_delay_min)} min"
                            } if departure_time else None
                        }
                        
                        trajectory["stops"].append(stop_info)
                
                # Only add trajectories with stops
                if trajectory["stops"]:
                    combined_data.append(trajectory)
        
        # Apply pagination
        total_records = len(combined_data)
        total_pages = (total_records + page_size - 1) // page_size if page_size > 0 else 1
        
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, total_records)
        
        paginated_data = combined_data[start_idx:end_idx]
        
        # Create response with metadata
        response = {
            "metadata": {
                "api_name": "NMBS Train Data API",
                "version": "1.0.0",
                "endpoint": "/api/trajectories",
                "data_type": "trajectories",
                "generated_at": datetime.datetime.now().isoformat(),
                "record_count": len(paginated_data),
                "total_records": total_records,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            },
            "data": paginated_data
        }
        
        logger.info(f"Generated trajectories response with {len(paginated_data)} records")
        return response
        
    except Exception as e:
        logger.error(f"Error generating trajectories: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}, 500