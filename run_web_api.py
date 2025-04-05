#!/usr/bin/env python3
"""
Run the NMBS Train Data API web server
"""
import os
import argparse
from dotenv import load_dotenv
from src.nmbs_api.web_api import start_web_server

# Load environment variables from .env file
load_dotenv()

def main():
    """Run the NMBS Web API server"""
    parser = argparse.ArgumentParser(description='Run the NMBS Web API server')
    parser.add_argument('--host', type=str, help='Host to run on', default=os.getenv('API_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, help='Port to run on', default=int(os.getenv('API_PORT', 25580)))
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    print(f"Starting NMBS API on {args.host}:{args.port}")
    print(f"The API will only be accessible through your Nginx proxy.")
    print(f"Access your API at: https://nmbsapi.sanderzijntestjes.be/api/health")
    
    start_web_server(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()