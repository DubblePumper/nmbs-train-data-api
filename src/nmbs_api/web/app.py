"""
Main module for the NMBS Train Data API web server
"""
import os
import logging
from flask import Flask
from dotenv import load_dotenv
from .middleware import setup_middleware
from .routes import api_routes
from .cache import CacheManager
from ..api import start_data_service

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create cache manager instance
cache_manager = CacheManager(data_dir='data')

def create_app():
    """
    Create and configure the Flask application
    
    Returns:
        Flask: The configured Flask application
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Set up middleware
    setup_middleware(app)
    
    # Register the API routes blueprint with a prefix
    app.register_blueprint(api_routes, url_prefix='/api')
    
    # Start the data service in the background
    logger.info("Starting NMBS data service...")
    data_service_thread = start_data_service()
    
    # Start the cache update thread
    cache_thread = cache_manager.start_cache_thread()
    
    logger.info("NMBS Web API initialized successfully")
    return app

def start_web_server(host='0.0.0.0', port=5000, debug=False, ssl_context=None):
    """
    Start the Flask web server
    
    Args:
        host (str): Host to bind to
        port (int): Port to bind to
        debug (bool): Whether to run in debug mode
        ssl_context: SSL context for HTTPS support, tuple of (cert, key) paths or 'adhoc'
    """
    # Create the app
    app = create_app()
    
    # Use the port from .env if not specified
    if port == 5000:
        env_port = os.getenv('API_PORT')
        if env_port:
            try:
                port = int(env_port)
            except ValueError:
                pass
    
    # Use the host from .env if not specified
    if host == '0.0.0.0':
        env_host = os.getenv('API_HOST')
        if env_host:
            host = env_host
    
    # Start the Flask app
    logger.info(f"Starting NMBS web API on {host}:{port}...")
    if ssl_context:
        logger.info("SSL enabled. Running with HTTPS.")
    
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)