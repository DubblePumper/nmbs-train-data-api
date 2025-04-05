#!/usr/bin/env python
"""
Run the NMBS Train Data API web server
"""
import argparse
import os
from dotenv import load_dotenv
from src.nmbs_api.web_api import start_web_server

# Load environment variables from .env file
load_dotenv()

def main():
    """Main entry point for the console script"""
    parser = argparse.ArgumentParser(description="NMBS Train Data API Web Server")
    parser.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"), 
                        help=f"Host to bind to (default: {os.getenv('API_HOST', '0.0.0.0')})")
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "5000")), 
                        help=f"Port to bind to (default: {os.getenv('API_PORT', '5000')})")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    print(f"Starting NMBS Train Data API on {args.host}:{args.port}")
    start_web_server(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()