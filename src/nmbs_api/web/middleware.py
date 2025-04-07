"""
Middleware components for the NMBS Train Data API
"""
import logging
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logger = logging.getLogger(__name__)

# List of allowed domains
ALLOWED_DOMAINS = ['nmbsapi.sanderzijntestjes.be', 'localhost', '127.0.0.1']

def setup_middleware(app):
    """
    Set up all middleware for the Flask app
    
    Args:
        app (Flask): The Flask application instance
    """
    # Add CORS support
    CORS(app)
    
    # Add support for proxy headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Register the domain validation middleware
    @app.before_request
    def validate_domain():
        """Ensure that the API is only accessed through the proper domain name"""
        host = request.host.split(':')[0]  # Remove port if present
        
        # Log the host for debugging
        logger.debug(f"Request received from host: {host}")
        
        # Allow access if the host is in the allowed domains
        if host in ALLOWED_DOMAINS:
            return None
        
        # For direct IP access, block it
        logger.warning(f"Unauthorized access attempt from host: {host}")
        return jsonify({
            "error": "Access denied",
            "message": "This API is only accessible via https://nmbsapi.sanderzijntestjes.be/",
            "redirect": "https://nmbsapi.sanderzijntestjes.be/"
        }), 403  # Forbidden