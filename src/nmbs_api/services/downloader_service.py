import os
import json
import logging
import traceback
import zipfile
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
from .base_service import BaseService
from .scraper_service import ScraperService

# Configure logging
logger = logging.getLogger(__name__)

class DownloaderService(BaseService):
    """Service to download NMBS data files using URLs from the scraper"""
    
    def __init__(self, cache_dir='data', scraper=None):
        super().__init__(cache_dir)
        self.scraper = scraper or ScraperService(cache_dir)
    
    def download_data(self):
        """
        Download the latest data files using cached URLs
        This can be done frequently (e.g., every minute)
        """
        # First download realtime data
        realtime_success = self._download_realtime_data()
        
        # Then download planning data
        planning_success = self._download_planning_data()
        
        return realtime_success or planning_success
    
    def _download_realtime_data(self):
        """Download realtime data with track changes"""
        # Make sure we have URLs
        if not self.scraper.urls:
            self.scraper._load_urls()
            if not self.scraper.urls:
                logger.warning("Geen realtime URLs beschikbaar voor data download. Run scrape_website eerst.")
                return False
        
        successful_downloads = 0
        update_info = {}
        
        for name, info in self.scraper.urls.items():
            url = info['url']
            filename = info['filename']
            output_path = os.path.join(self.realtime_dir, filename)
            
            logger.info(f"Downloading realtime data {filename} van {url}...")
            try:
                data_response = self.scraper.scraper.get(url)
                if data_response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(data_response.content)
                    
                    # Also save as JSON for easier access
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(data_response.content)
                    feed_dict = MessageToDict(feed)
                    
                    json_file = output_path.replace('.bin', '.json')
                    with open(json_file, 'w') as f:
                        json.dump(feed_dict, f, indent=2)
                    
                    logger.info(f"Succesvol gedownload en geconverteerd: {output_path}")
                    successful_downloads += 1
                    
                    # Record update time
                    update_info[name] = {
                        'last_downloaded': self.get_timestamp(),
                        'bin_file': output_path,
                        'json_file': json_file
                    }
                else:
                    logger.error(f"Fout bij downloaden: HTTP status {data_response.status_code}")
            except Exception as e:
                logger.error(f"Fout bij downloaden van {filename}: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Save last updated info
        try:
            with open(self.last_updated_file, 'w') as f:
                json.dump(update_info, f, indent=2)
        except Exception as e:
            logger.error(f"Fout bij opslaan van update info: {str(e)}")
        
        return successful_downloads > 0
    
    def _download_planning_data(self):
        """Download and extract planning data with platform info"""
        # Make sure we have URLs
        if not self.scraper.planning_urls:
            self.scraper._load_planning_urls()
            if not self.scraper.planning_urls:
                logger.warning("Geen planning URLs beschikbaar voor data download. Run scrape_website eerst.")
                return False
        
        successful_downloads = 0
        update_info = {}
        
        for name, info in self.scraper.planning_urls.items():
            url = info['url']
            filename = info['filename']
            output_path = os.path.join(self.planning_dir, filename)
            
            logger.info(f"Downloading planning data {filename} van {url}...")
            try:
                data_response = self.scraper.scraper.get(url)
                if data_response.status_code == 200:
                    # Save the ZIP file
                    with open(output_path, 'wb') as f:
                        f.write(data_response.content)
                    
                    logger.info(f"ZIP bestand opgeslagen: {output_path}")
                    
                    # Extract the ZIP file
                    extract_success = self._extract_planning_zip(output_path)
                    
                    if extract_success:
                        logger.info(f"Succesvol gedownload en uitgepakt: {output_path}")
                        successful_downloads += 1
                        
                        # Get details about extracted files
                        extracted_files = os.listdir(self.planning_extracted_dir)
                        
                        # Record update time and extracted files
                        update_info[name] = {
                            'last_downloaded': self.get_timestamp(),
                            'zip_file': output_path,
                            'extracted_dir': self.planning_extracted_dir,
                            'extracted_files': extracted_files
                        }
                    else:
                        logger.error(f"Kon ZIP bestand niet uitpakken: {output_path}")
                else:
                    logger.error(f"Fout bij downloaden: HTTP status {data_response.status_code}")
            except Exception as e:
                logger.error(f"Fout bij downloaden van {filename}: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Save last updated info
        try:
            with open(self.planning_updated_file, 'w') as f:
                json.dump(update_info, f, indent=2)
        except Exception as e:
            logger.error(f"Fout bij opslaan van planning update info: {str(e)}")
        
        return successful_downloads > 0
    
    def _extract_planning_zip(self, zip_path):
        """Extract the planning data ZIP file"""
        logger.info(f"Uitpakken van ZIP bestand: {zip_path}")
        
        try:
            # Clear the extracted directory first to avoid old files
            for file in os.listdir(self.planning_extracted_dir):
                file_path = os.path.join(self.planning_extracted_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            # Extract the ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get file names and log them
                file_names = zip_ref.namelist()
                logger.info(f"Bestanden in ZIP: {file_names}")
                
                # Extract all files
                zip_ref.extractall(self.planning_extracted_dir)
            
            logger.info(f"ZIP bestand succesvol uitgepakt naar: {self.planning_extracted_dir}")
            return True
        except Exception as e:
            logger.error(f"Fout bij uitpakken van ZIP bestand: {str(e)}")
            logger.error(traceback.format_exc())
            return False