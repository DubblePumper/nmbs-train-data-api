import os
import json
from .data_service import NMBSDataService

# Singleton instance of the data service
_data_service = None

def get_data_service():
    """
    Get or create the NMBSDataService singleton
    """
    global _data_service
    if _data_service is None:
        _data_service = NMBSDataService()
    return _data_service

def start_data_service():
    """
    Start the NMBS data service in the background
    
    This will:
    1. Do an initial scrape of the website if needed (once only)
    2. Download the latest data files
    3. Keep running in the background to update the data regularly
    
    Returns:
        threading.Thread: The background thread running the service
    """
    service = get_data_service()
    return service.start_background_service()

def get_realtime_data(include_track_changes=True):
    """
    Get the latest real-time NMBS data
    
    Args:
        include_track_changes (bool): Whether to include track change information
        
    Returns:
        dict: The GTFS real-time data as a dictionary
    """
    service = get_data_service()
    return service.get_latest_data(include_track_changes)

def force_update():
    """
    Force an immediate update of the data
    
    Returns:
        bool: True if successful
    """
    service = get_data_service()
    return service.download_data()