"""
Utility functions for the NMBS Train Data API web server
"""
import logging
from flask import request

# Configure logging
logger = logging.getLogger(__name__)

# Common GTFS field mappings - this makes it easy to add new fields
GTFS_FIELD_MAPPINGS = {
    # Stop-related fields
    'stop_id': str,
    'stop_name': str,
    'stop_code': str,
    'location_type': str,
    'parent_station': str,
    'platform_code': str,
    
    # Trip and route fields
    'trip_id': str,
    'route_id': str,
    'route_short_name': str,
    'route_long_name': str,
    'route_type': str,
    'service_id': str,
    'direction_id': str,
    
    # Time fields
    'arrival_time': str,
    'departure_time': str,
    'stop_sequence': str,
    'pickup_type': str,
    'drop_off_type': str,
    
    # Calendar fields
    'monday': str,
    'tuesday': str,
    'wednesday': str,
    'thursday': str,
    'friday': str,
    'saturday': str,
    'sunday': str,
    'start_date': str,
    'end_date': str,
    
    # Agency fields
    'agency_id': str,
    'agency_name': str,
    'agency_url': str,
    'agency_timezone': str,
    
    # Translation fields
    'trans_id': str,
    'lang': str,
    'translation': str
}

def extract_request_params():
    """
    Extract and validate request parameters for data endpoints
    using a dynamic approach that reduces code duplication.
    
    Returns:
        dict: A dictionary with validated parameters
    """
    # Get pagination parameters with validation
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
    
    # Get all query parameters as a dictionary
    all_params = request.args.to_dict()
    
    # Extract search parameters dynamically
    search_query = all_params.get('search')
    search_field = all_params.get('field')
    
    # Handle the search=field_name&field_name=value pattern
    if search_query and not search_field:
        search_field = search_query
        # Check if the field exists in the request and use its value as the search query
        if search_field in all_params:
            search_query = all_params.get(search_field)
            logger.debug(f"Using search format: search={search_field}&{search_field}={search_query}")
    
    # Extract all filter parameters dynamically based on GTFS field mappings
    filters = {}
    for field, field_type in GTFS_FIELD_MAPPINGS.items():
        if field in all_params:
            filters[field] = all_params.get(field)
    
    # Sort parameters
    sort_by = all_params.get('sort_by')
    sort_direction = all_params.get('sort_direction', 'asc').lower()
    if sort_direction not in ['asc', 'desc']:
        sort_direction = 'asc'
    
    # Log search parameters for debugging
    if search_query or filters:
        logger.debug(f"Search parameters: query={search_query}, field={search_field}, filters={filters}")
    
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