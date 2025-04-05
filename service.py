#!/usr/bin/env python
import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from nmbs_api.data_service import NMBSDataService

def main():
    parser = argparse.ArgumentParser(description='NMBS Data Collection Service')
    parser.add_argument('--interval', type=int, default=60, 
                      help='Interval in seconds between data downloads (default: 60)')
    parser.add_argument('--scrape-interval', type=int, default=86400,
                      help='Interval in seconds between website scraping (default: 86400 - once per day)')
    parser.add_argument('--log-file', type=str, default='nmbs_service.log',
                      help='Path to log file (default: nmbs_service.log)')
    parser.add_argument('--data-dir', type=str, default='data',
                      help='Directory to store data files (default: data)')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting NMBS Data Collection Service - {datetime.now().isoformat()}")
    logger.info(f"Data download interval: {args.interval} seconds")
    logger.info(f"Website scraping interval: {args.scrape_interval} seconds")
    logger.info(f"Data directory: {args.data_dir}")
    
    # Create the service
    service = NMBSDataService(cache_dir=args.data_dir)
    
    # Variables to track last scrape time
    last_scrape_time = 0
    
    try:
        # Initial run
        logger.info("Performing initial website scrape...")
        service.scrape_website()
        last_scrape_time = time.time()
        
        logger.info("Downloading initial data...")
        service.download_data()
        
        # Main loop
        logger.info("Service running. Press Ctrl+C to stop.")
        while True:
            # Check if we need to scrape the website again
            current_time = time.time()
            if current_time - last_scrape_time >= args.scrape_interval:
                logger.info("Scheduled website scrape...")
                service.scrape_website()
                last_scrape_time = current_time
            
            # Download data at the specified interval
            service.download_data()
            
            # Sleep until the next interval
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
    except Exception as e:
        logger.error(f"Service error: {str(e)}")
        raise
    finally:
        logger.info("Service shutting down.")

if __name__ == "__main__":
    main()