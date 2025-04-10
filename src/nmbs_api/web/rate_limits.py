"""
Rate limiting configuration for the NMBS Train Data API routes
This module applies specific rate limits to different API endpoints based on their
resource usage and typical access patterns.
"""
import logging
from flask import Blueprint
from .security import limiter

# Configure logging
logger = logging.getLogger(__name__)

def apply_rate_limits(blueprint: Blueprint) -> None:
    """
    Apply rate limits to API routes based on their function and resource usage
    
    Args:
        blueprint: The Flask Blueprint containing the routes
    """
    # Basic health endpoint - allow frequent access
    limiter.limit("60 per minute")(blueprint.route('/health', methods=['GET']))
    
    # Realtime data - moderate rate limiting
    limiter.limit("30 per minute")(blueprint.route('/realtime/data', methods=['GET']))
    
    # File listings and metadata - more permissive
    limiter.limit("60 per minute")(blueprint.route('/planningdata/files', methods=['GET']))
    limiter.limit("60 per minute")(blueprint.route('/planningdata/data', methods=['GET']))
    
    # Individual GTFS data endpoints - moderate limiting
    limiter.limit("45 per minute")(blueprint.route('/planningdata/<filename>', methods=['GET']))
    limiter.limit("45 per minute")(blueprint.route('/planningdata/stops', methods=['GET']))
    limiter.limit("45 per minute")(blueprint.route('/planningdata/routes', methods=['GET']))
    limiter.limit("45 per minute")(blueprint.route('/planningdata/calendar', methods=['GET']))
    limiter.limit("45 per minute")(blueprint.route('/planningdata/trips', methods=['GET']))
    
    # Resource-intensive endpoints - stricter limiting
    limiter.limit("30 per minute")(blueprint.route('/planningdata/stop_times', methods=['GET']))
    
    # Cache endpoints - permissive since they're optimized
    limiter.limit("90 per minute")(blueprint.route('/cache', methods=['GET']))
    limiter.limit("60 per minute")(blueprint.route('/cache/<data_type>', methods=['GET']))
    
    # Administrative endpoints - strict limiting
    limiter.limit("5 per minute")(blueprint.route('/update', methods=['POST']))
    
    logger.info("Rate limits applied to API endpoints")
    
    return blueprint