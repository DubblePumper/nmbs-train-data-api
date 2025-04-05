#!/usr/bin/env python
"""
Run the NMBS Train Data API web server
"""
import argparse
from src.nmbs_api.web_api import start_web_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NMBS Train Data API Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    print(f"Starting NMBS Train Data API on {args.host}:{args.port}")
    start_web_server(host=args.host, port=args.port, debug=args.debug)