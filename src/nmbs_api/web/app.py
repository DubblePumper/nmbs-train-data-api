"""
Main module for the NMBS Train Data API web server
"""
import os
import logging
import ssl
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from .middleware import setup_middleware
from .routes import api_routes
from .cache import CacheManager
from .security import setup_security, run_security_audit
from .monitoring import setup_request_monitoring, register_metrics_endpoint
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
    
    # Set up CORS - Toegang voor alle oorsprong toestaan
    CORS(app, resources={
        r"/*": {
            "origins": "*",  # Voor open API toegang
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })
    logger.info("CORS configuratie toegepast: open toegang voor alle oorsprong")
    
    # Configure JSON pretty printing in a compatible way
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
    
    # Handle compatibility with different Flask versions
    if hasattr(app, 'json'):
        # Flask 2.x style
        app.json.compact = False
        app.json.sort_keys = False
        app.json.ensure_ascii = False
    else:
        # Older Flask style
        app.config['RESTFUL_JSON'] = {
            'indent': 4,
            'sort_keys': False,
            'ensure_ascii': False
        }
    
    # Set up middleware
    setup_middleware(app)
    
    # Set up security features
    setup_security(app)
    
    # Register the API routes blueprint with a prefix
    app.register_blueprint(api_routes, url_prefix='/api')
    
    # Set up monitoring and metrics
    setup_request_monitoring(app)
    register_metrics_endpoint(app)
    logger.info("Monitoring systeem en /metrics endpoint ingeschakeld")
    
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
    
    # Set up SSL context if not provided but SSL cert and key are configured
    if not ssl_context:
        cert_path = os.getenv('SSL_CERT_PATH')
        key_path = os.getenv('SSL_KEY_PATH')
        
        if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
            try:
                ssl_context = (cert_path, key_path)
                logger.info(f"Using SSL certificate from environment variables: {cert_path}")
            except Exception as e:
                logger.error(f"Failed to load SSL certificate: {str(e)}")
        elif os.getenv('ENABLE_SSL', 'false').lower() == 'true':
            # Use self-signed certificate for development
            try:
                ssl_context = 'adhoc'
                logger.info("Using auto-generated self-signed SSL certificate")
            except Exception as e:
                logger.error(f"Failed to create self-signed certificate: {str(e)}")
    
    # Start the Flask app
    logger.info(f"Starting NMBS web API on {host}:{port}...")
    if ssl_context:
        logger.info("SSL enabled. Running with HTTPS.")
    else:
        logger.warning("Running without SSL/HTTPS. This is not recommended for production.")
    
    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)