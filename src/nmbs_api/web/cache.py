"""
Cache functionality for the NMBS Train Data API
"""
import logging
import threading
import time
import json
import os
from ..api import get_realtime_data, get_planning_files_list, get_planning_file

# Configure logging
logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching of API data to improve performance"""
    
    def __init__(self, data_dir='data'):
        """
        Initialize the cache manager
        
        Args:
            data_dir (str): Directory to store cache files
        """
        self.data_dir = data_dir
        self.cache_data = {}
        self.cache_lock = threading.Lock()
        self.cache_thread = None
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
    
    def start_cache_thread(self):
        """Start the background thread that updates the cache"""
        if self.cache_thread is None or not self.cache_thread.is_alive():
            self.cache_thread = threading.Thread(target=self._update_cache_loop, daemon=True)
            self.cache_thread.start()
            logger.info("Started cache update thread")
        return self.cache_thread
    
    def _update_cache_loop(self):
        """Background thread function that updates the cache every 2 minutes"""
        logger.info("Cache update thread is running")
        while True:
            try:
                self.update_cache()
                # Wait for 2 minutes before updating again
                time.sleep(120)
            except Exception as e:
                logger.error(f"Error in cache update thread: {str(e)}")
                # Shorter delay if error occurred
                time.sleep(30)
    
    def update_cache(self):
        """Update the cache with the first 25 records of each endpoint"""
        logger.info("Updating API data cache...")
        try:
            # Get list of planning files
            files = get_planning_files_list()
            
            # Initialize combined cache data
            combined_cache = {
                "realtime": None,
                "planning_data": {}
            }
            
            # Get realtime data for cache
            realtime_data = get_realtime_data()
            if realtime_data:
                with self.cache_lock:
                    self.cache_data['realtime'] = realtime_data
                combined_cache["realtime"] = realtime_data
                logger.info("Added realtime data to combined cache")
            
            # Get first 25 records for each planning file
            for file in files:
                file_name = file.split('.')[0]  # Remove extension
                try:
                    # Get the data with pagination (first 25 records)
                    params = {
                        'page': 0,
                        'page_size': 25,
                        'search': {'query': None, 'field': None},
                        'filters': {},
                        'sort': {'field': None, 'direction': 'asc'}
                    }
                    
                    data = get_planning_file(file, page=0, page_size=25, search_params=params)
                    
                    if data:
                        with self.cache_lock:
                            self.cache_data[file_name] = data
                        combined_cache["planning_data"][file_name] = data
                        logger.info(f"Added {file_name} data to combined cache")
                except Exception as e:
                    logger.error(f"Error updating cache for {file_name}: {str(e)}")
            
            # Save combined data directly to the data folder
            with open(os.path.join(self.data_dir, "short-test-data.json"), 'w') as f:
                json.dump(combined_cache, f)
            logger.info("Updated short-test-data.json with all cached data")
            
            return True
        except Exception as e:
            logger.error(f"Failed to update cache: {str(e)}")
            return False
    
    def get_cached_data(self, data_type):
        """
        Get cached data for a specific data type
        
        Args:
            data_type (str): The type of data to retrieve (e.g., 'stops', 'routes', 'realtime')
            
        Returns:
            dict: The cached data or None if not in cache
        """
        with self.cache_lock:
            return self.cache_data.get(data_type)
    
    def get_available_cache_types(self):
        """
        Get a list of available cached data types
        
        Returns:
            list: List of available cache types
        """
        with self.cache_lock:
            return list(self.cache_data.keys())