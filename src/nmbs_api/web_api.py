"""
NMBS Train Data API web server - Main entry point

This module has been refactored for better organization:
- utils.py: Utility functions for request parameter extraction
- middleware.py: Middleware components for CORS, domain validation etc.
- routes.py: All API endpoint definitions
- cache.py: Caching functionality
- app.py: Main application setup and server functionality

This file now serves as a compatibility layer to maintain backward compatibility.
"""
import logging
from .web import start_web_server

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

# Export the main function
__all__ = ['start_web_server']