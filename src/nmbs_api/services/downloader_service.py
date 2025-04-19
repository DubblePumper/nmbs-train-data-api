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
            
            # First try using the known working exact headers from a browser session
            # Reset the user agent index to use the exact browser headers
            self.scraper.last_agent_idx = -1
            self.scraper._rotate_user_agent()  # This will set it to index 0
            headers = self.scraper._get_headers_for_current_agent()
            self.scraper.scraper.headers.update(headers)
            
            logger.info(f"Trying with exact browser headers first...")
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
                            'extracted_files': extracted_files,
                            'successful_user_agent': headers.get('user-agent', headers.get('User-Agent', 'unknown'))
                        }
                        
                        # Save last updated info immediately in case we crash later
                        try:
                            with open(self.planning_updated_file, 'w') as f:
                                json.dump(update_info, f, indent=2)
                        except Exception as e:
                            logger.error(f"Fout bij opslaan van planning update info: {str(e)}")
                        
                        return successful_downloads > 0
                else:
                    logger.error(f"Fout bij downloaden met exact headers: HTTP status {data_response.status_code}")
            except Exception as e:
                logger.error(f"Fout bij downloaden met exact headers: {str(e)}")
                logger.error(traceback.format_exc())
            
            # If first attempt failed, try a comprehensive set of alternative URLs
            alternative_urls = [
                # Common GTFS paths with the base URL
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/latest"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/gtfs"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/NMBS_GTFS"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/latest_TC"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/current"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/current_TC"),
                url.replace("static/d22ad6759ee25bg84ddb6c818g4dc4de_TC", "static/feed"),
                
                # Try explicit NMBS-related paths
                "https://sncb-opendata.hafas.de/gtfs/static/nmbs",
                "https://sncb-opendata.hafas.de/gtfs/static/nmbs_gtfs",
                "https://sncb-opendata.hafas.de/gtfs/static/sncb",
                "https://sncb-opendata.hafas.de/gtfs/static/sncb_gtfs",
                
                # Modified base URLs
                "https://gtfs.irail.be/nmbs/gtfs/latest.zip",
                "https://opendata.belgianrail.be/gtfs/static/latest",
                "https://opendata.belgiantrain.be/gtfs/static/latest",
                
                # Fall back to GTFS at Belgium.transport
                "https://gtfs.irail.be/nmbs/gtfs/nmbs-latest.zip",
                "https://data.transportdata.be/NMBS/GTFS/NMBS_GTFS.zip"
            ]
            
            logger.info(f"Trying comprehensive set of {len(alternative_urls)} alternative URLs...")
            
            for alt_idx, alt_url in enumerate(alternative_urls):
                # Rotate between different user agents for each alternative URL
                self.scraper._rotate_user_agent()
                headers = self.scraper._get_headers_for_current_agent()
                self.scraper.scraper.headers.update(headers)
                
                # Get user agent in a case-insensitive way (handle both 'user-agent' and 'User-Agent')
                user_agent = headers.get('user-agent', headers.get('User-Agent', 'unknown'))
                
                logger.info(f"Trying alternative URL #{alt_idx+1}: {alt_url}")
                logger.info(f"Using User-Agent: {user_agent[:50]}...")
                
                try:
                    alt_response = self.scraper.scraper.get(alt_url)
                    
                    if alt_response.status_code == 200:
                        logger.info(f"SUCCESS with alternative URL #{alt_idx+1}: {alt_url}")
                        
                        # Check content type to make sure it's a ZIP file
                        content_type = alt_response.headers.get('Content-Type', '')
                        content_length = alt_response.headers.get('Content-Length', '0')
                        
                        logger.info(f"Content-Type: {content_type}, Content-Length: {content_length}")
                        
                        # Save even if not explicitly ZIP - sometimes content types are wrong
                        with open(output_path, 'wb') as f:
                            f.write(alt_response.content)
                        
                        logger.info(f"Downloaded file from alternative URL: {output_path}")
                        
                        try:
                            # Try to extract - this will fail if not a valid ZIP
                            extract_success = self._extract_planning_zip(output_path)
                            
                            if extract_success:
                                logger.info(f"Succesvol gedownload en uitgepakt van alternatieve URL: {alt_url}")
                                successful_downloads += 1
                                
                                # Update the stored URL to use this working one in future
                                info['url'] = alt_url
                                self.scraper.planning_urls[name]['url'] = alt_url
                                self.scraper._save_planning_urls()
                                logger.info(f"Planning URL bijgewerkt naar werkende alternatief: {alt_url}")
                                
                                extracted_files = os.listdir(self.planning_extracted_dir)
                                update_info[name] = {
                                    'last_downloaded': self.get_timestamp(),
                                    'zip_file': output_path,
                                    'extracted_dir': self.planning_extracted_dir,
                                    'extracted_files': extracted_files,
                                    'successful_user_agent': user_agent,
                                    'successful_alt_url': alt_url,
                                    'content_type': content_type,
                                    'content_length': content_length
                                }
                                
                                # Save success info immediately
                                try:
                                    with open(self.planning_updated_file, 'w') as f:
                                        json.dump(update_info, f, indent=2)
                                except Exception as e:
                                    logger.error(f"Fout bij opslaan van planning update info: {str(e)}")
                                
                                return successful_downloads > 0
                        except Exception as e:
                            logger.error(f"Downloaded file is not a valid ZIP: {str(e)}")
                            # Continue to the next alternative URL
                    else:
                        logger.error(f"Alternative URL #{alt_idx+1} failed: HTTP status {alt_response.status_code}")
                except Exception as e:
                    logger.error(f"Error trying alternative URL #{alt_idx+1}: {str(e)}")
            
            logger.error(f"All alternative URLs failed. Trying to find any existing GTFS data...")
            
            # If we have an existing ZIP file that we previously downloaded, try to use that
            if os.path.exists(output_path):
                logger.info(f"Found existing ZIP file: {output_path}. Trying to extract it...")
                try:
                    extract_success = self._extract_planning_zip(output_path)
                    if extract_success:
                        logger.info(f"Successfully extracted previously downloaded ZIP file")
                        successful_downloads += 1
                        
                        extracted_files = os.listdir(self.planning_extracted_dir)
                        update_info[name] = {
                            'last_downloaded': self.get_timestamp(),
                            'zip_file': output_path,
                            'extracted_dir': self.planning_extracted_dir,
                            'extracted_files': extracted_files,
                            'note': 'Used previously downloaded ZIP file'
                        }
                        
                        # Save info about reusing existing file
                        try:
                            with open(self.planning_updated_file, 'w') as f:
                                json.dump(update_info, f, indent=2)
                        except Exception as e:
                            logger.error(f"Fout bij opslaan van planning update info: {str(e)}")
                        
                        return successful_downloads > 0
                except Exception as e:
                    logger.error(f"Failed to extract existing ZIP file: {str(e)}")
        
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
            # First verify the ZIP file integrity
            try:
                with open(zip_path, 'rb') as f:
                    file_size = os.path.getsize(zip_path)
                    logger.info(f"ZIP bestand grootte: {file_size} bytes")
                    
                    # Check if file is too small to be a valid ZIP
                    if file_size < 100:
                        logger.error(f"ZIP bestand is te klein ({file_size} bytes), waarschijnlijk ongeldig")
                        return False
            except Exception as e:
                logger.error(f"Fout bij controleren van ZIP bestand grootte: {str(e)}")
                return False
                
            # Clear the extracted directory first to avoid old files
            for file in os.listdir(self.planning_extracted_dir):
                file_path = os.path.join(self.planning_extracted_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            # Try to extract with safeguards for corrupted files
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Get file names and log them
                    try:
                        file_names = zip_ref.namelist()
                        logger.info(f"Bestanden in ZIP: {file_names}")
                        
                        if not file_names:
                            logger.error("ZIP bestand bevat geen bestanden")
                            return False
                    except Exception as e:
                        logger.error(f"Kon bestandslijst niet lezen uit ZIP: {str(e)}")
                        return False
                    
                    # Extract files one by one with error handling
                    for file_name in file_names:
                        try:
                            logger.debug(f"Uitpakken van bestand: {file_name}")
                            zip_ref.extract(file_name, path=self.planning_extracted_dir)
                        except Exception as e:
                            logger.error(f"Fout bij uitpakken van bestand {file_name}: {str(e)}")
                            # Continue with other files
            except zipfile.BadZipFile:
                logger.error(f"Ongeldig ZIP bestandsformaat: {zip_path}")
                return False
            except EOFError:
                logger.error(f"ZIP bestand is mogelijk beschadigd: {zip_path}")
                
                # Special handling for iRail GTFS data - try direct download of individual files
                if "irail.be" in zip_path:
                    logger.info("Proberen om iRail GTFS bestanden direct te downloaden...")
                    return self._download_irail_gtfs_files()
                return False
            
            # Verify the extracted files to confirm success
            extracted_files = os.listdir(self.planning_extracted_dir)
            required_files = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
            
            for req_file in required_files:
                if req_file not in extracted_files:
                    logger.warning(f"Vereist bestand ontbreekt na uitpakken: {req_file}")
            
            if not extracted_files:
                logger.error(f"Geen bestanden uitgepakt naar: {self.planning_extracted_dir}")
                return False
                
            logger.info(f"ZIP bestand succesvol uitgepakt naar: {self.planning_extracted_dir}")
            return True
        except Exception as e:
            logger.error(f"Fout bij uitpakken van ZIP bestand: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def _download_irail_gtfs_files(self):
        """Download individual GTFS files directly from iRail"""
        logger.info("Directe download van iRail GTFS bestanden...")
        
        # Base URL for individual GTFS files
        base_url = "https://gtfs.irail.be/nmbs/gtfs/"
        
        # Essential GTFS files to download
        essential_files = [
            "agency.txt",
            "stops.txt",
            "routes.txt",
            "trips.txt",
            "stop_times.txt",
            "calendar.txt",
            "calendar_dates.txt"
        ]
        
        # Optional files to try
        optional_files = [
            "translations.txt",
            "transfers.txt",
            "stop_time_overrides.txt"
        ]
        
        success_count = 0
        
        # Download essential files
        for filename in essential_files:
            file_url = f"{base_url}{filename}"
            output_path = os.path.join(self.planning_extracted_dir, filename)
            
            try:
                logger.info(f"Downloading {filename} from iRail...")
                response = self.scraper.scraper.get(file_url)
                
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Succesvol gedownload: {filename}")
                    success_count += 1
                else:
                    logger.error(f"Kon {filename} niet downloaden: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"Fout bij downloaden van {filename}: {str(e)}")
        
        # Try optional files but don't count failures
        for filename in optional_files:
            file_url = f"{base_url}{filename}"
            output_path = os.path.join(self.planning_extracted_dir, filename)
            
            try:
                logger.info(f"Proberen optioneel bestand te downloaden: {filename}")
                response = self.scraper.scraper.get(file_url)
                
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Succesvol gedownload: {filename}")
                else:
                    logger.info(f"Optioneel bestand niet beschikbaar: {filename}")
            except Exception as e:
                logger.info(f"Kon optioneel bestand niet downloaden: {filename}")
        
        # Success if we got all essential files
        if success_count == len(essential_files):
            logger.info("Alle essentiële GTFS bestanden succesvol direct gedownload")
            return True
        else:
            logger.error(f"Slechts {success_count}/{len(essential_files)} essentiële bestanden gedownload")
            return False