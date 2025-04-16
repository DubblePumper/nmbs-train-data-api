"""
API Configuration Settings

This module contains configuration settings for the NMBS Train Data API,
including pagination defaults and limits.
"""

# Default API settings
API_NAME = "NMBS Train Data API"
API_VERSION = "1.0.0"

# Pagination settings per endpoint
# Format: {endpoint_name: {'default': default_size, 'max': maximum_size}}
PAGINATION_SETTINGS = {
    # Default for all endpoints if not specified
    'default': {
        'default_size': 1000,
        'max_size': 5000
    },
    # Real-time data endpoint
    'realtime_data': {
        'default_size': 1000,
        'max_size': 3000
    },
    # Planning data endpoints
    'stops': {
        'default_size': 1000,
        'max_size': 5000
    },
    'routes': {
        'default_size': 1000,
        'max_size': 5000
    },
    'calendar': {
        'default_size': 1000,
        'max_size': 5000
    },
    'trips': {
        'default_size': 1000,
        'max_size': 5000
    },
    'stop_times': {
        'default_size': 500,   # Smaller default for large dataset
        'max_size': 2000
    },
    'calendar_dates': {
        'default_size': 1000,
        'max_size': 5000
    },
    'agency': {
        'default_size': 1000,
        'max_size': 5000
    },
    'translations': {
        'default_size': 1000,
        'max_size': 5000
    },
    # Trajectories endpoint (combined data)
    'trajectories': {
        'default_size': 1000,   # Changed from 20 to 1000
        'max_size': 1000        # Changed from 100 to 1000
    }
}

# Get pagination settings for a specific endpoint
def get_pagination_settings(endpoint_name):
    """
    Get the pagination settings for a specific endpoint
    
    Args:
        endpoint_name: The name of the endpoint to get settings for
        
    Returns:
        dict: A dictionary containing default_size and max_size
    """
    if endpoint_name in PAGINATION_SETTINGS:
        return PAGINATION_SETTINGS[endpoint_name]
    else:
        return PAGINATION_SETTINGS['default']