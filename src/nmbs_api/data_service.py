import os
import json
import time
import logging
import threading
import schedule
import cloudscraper
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nmbs_data_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NMBSDataService:
    """
    Service to efficiently manage NMBS data retrieval
    
    This service:
    1. Scrapes the NMBS website infrequently to get data URLs
    2. Downloads the actual data files frequently
    3. Maintains a cache of the latest data
    4. Provides an API to access the data
    """
    
    def __init__(self, cache_dir='data'):
        self.cache_dir = cache_dir
        self.realtime_dir = os.path.join(cache_dir, 'Real-time_gegevens')
        self.urls_file = os.path.join(self.realtime_dir, 'data_urls.json')
        self.last_updated_file = os.path.join(self.realtime_dir, 'last_updated.json')
        self.urls = {}
        self.cookies_file = os.getenv('COOKIES_FILE', 'data/cookies.json')
        self.nmbs_url = os.getenv('NMBS_DATA_URL')
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        
        # Create directories if they don't exist
        os.makedirs(self.realtime_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
        
        # Load existing URLs if available
        self._load_urls()
        
        # Create scraper
        self.scraper = self._create_scraper()
    
    def _create_scraper(self):
        """Create a CloudScraper instance with cookies if available"""
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=5
        )
        
        # Load cookies if available
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    logger.info("Cookies geladen uit bestand")
                    
                    # Use cookies for the scraper
                    for cookie in cookies:
                        scraper.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            except Exception as e:
                logger.warning(f"Fout bij laden van cookies: {str(e)}")
        
        return scraper
    
    def _load_urls(self):
        """Load cached URLs from file"""
        if os.path.exists(self.urls_file):
            try:
                with open(self.urls_file, 'r') as f:
                    self.urls = json.load(f)
                    logger.info(f"Geladen URLs: {len(self.urls)} gevonden")
            except Exception as e:
                logger.error(f"Fout bij laden van URLs: {str(e)}")
                self.urls = {}
    
    def _save_urls(self):
        """Save URLs to cache file"""
        try:
            with open(self.urls_file, 'w') as f:
                json.dump(self.urls, f, indent=2)
            logger.info(f"URLs opgeslagen: {len(self.urls)}")
        except Exception as e:
            logger.error(f"Fout bij opslaan van URLs: {str(e)}")
    
    def _save_cookies(self):
        """Save cookies to file"""
        try:
            cookies_dict = [{'name': c.name, 'value': c.value, 'domain': c.domain} for c in self.scraper.cookies]
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies_dict, f)
            logger.info("Cookies opgeslagen")
        except Exception as e:
            logger.error(f"Fout bij opslaan van cookies: {str(e)}")
    
    def scrape_website(self):
        """
        Scrape the NMBS website to get data URLs
        This should be done infrequently (e.g., once a day)
        """
        if not self.nmbs_url:
            logger.error("NMBS_DATA_URL is niet geconfigureerd in .env file")
            return False
        
        logger.info(f"Webscraping van {self.nmbs_url}...")
        
        try:
            response = self.scraper.get(self.nmbs_url)
            self._save_cookies()
            
            if response.status_code != 200:
                logger.error(f"Fout bij ophalen van NMBS website: HTTP status {response.status_code}")
                return False
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the real-time data links
            new_urls = {}
            for link in soup.find_all('a', class_='link flex-items-center marg-bottom-sm-10'):
                span_text = link.find('span')
                if span_text and 'real-time gegevens' in span_text.text:
                    url = link.get('href')
                    name = span_text.text.strip()
                    filename = f"{name.replace(' ', '_')}.bin"
                    new_urls[name] = {
                        'url': url,
                        'filename': filename,
                        'last_checked': datetime.now().isoformat()
                    }
            
            if not new_urls:
                logger.warning("Geen real-time data links gevonden. Mogelijk is de website structuur veranderd.")
                return False
            
            # Update URLs and save
            self.urls = new_urls
            self._save_urls()
            logger.info(f"Website scraping succesvol: {len(self.urls)} URLs gevonden")
            return True
            
        except Exception as e:
            logger.error(f"Fout bij webscraping: {str(e)}")
            return False
    
    def download_data(self):
        """
        Download the latest data files using cached URLs
        This can be done frequently (e.g., every minute)
        """
        if not self.urls:
            logger.warning("Geen URLs beschikbaar voor data download. Run scrape_website eerst.")
            return False
        
        successful_downloads = 0
        update_info = {}
        
        for name, info in self.urls.items():
            url = info['url']
            filename = info['filename']
            output_path = os.path.join(self.realtime_dir, filename)
            
            logger.info(f"Downloading {filename} van {url}...")
            try:
                data_response = self.scraper.get(url)
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
                        'last_downloaded': datetime.now().isoformat(),
                        'bin_file': output_path,
                        'json_file': json_file
                    }
                else:
                    logger.error(f"Fout bij downloaden: HTTP status {data_response.status_code}")
            except Exception as e:
                logger.error(f"Fout bij downloaden van {filename}: {str(e)}")
        
        # Save last updated info
        try:
            with open(self.last_updated_file, 'w') as f:
                json.dump(update_info, f, indent=2)
        except Exception as e:
            logger.error(f"Fout bij opslaan van update info: {str(e)}")
        
        return successful_downloads > 0
    
    def get_latest_data(self, include_track_changes=True):
        """
        API method to get the latest data
        
        Args:
            include_track_changes: Whether to get data with track change info
            
        Returns:
            dict: The latest GTFS real-time data as a dictionary
        """
        # Load last updated info
        if not os.path.exists(self.last_updated_file):
            logger.warning("Geen update info beschikbaar. Run download_data eerst.")
            return None
        
        try:
            with open(self.last_updated_file, 'r') as f:
                update_info = json.load(f)
            
            # Find the appropriate file based on track changes preference
            target_key = None
            for name in update_info.keys():
                if include_track_changes and 'met info over spoorveranderingen' in name:
                    target_key = name
                    break
                elif not include_track_changes and 'zonder info over spoorveranderingen' in name:
                    target_key = name
                    break
            
            if not target_key:
                logger.warning(f"Geen data gevonden {'met' if include_track_changes else 'zonder'} spoorveranderingen.")
                # Fall back to any available data
                if update_info:
                    target_key = list(update_info.keys())[0]
                else:
                    return None
            
            # Load the JSON file
            json_file = update_info[target_key]['json_file']
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"JSON bestand niet gevonden: {json_file}")
                return None
                
        except Exception as e:
            logger.error(f"Fout bij ophalen van laatste data: {str(e)}")
            return None
    
    def run_as_service(self):
        """
        Run the service with scheduled tasks
        """
        # Schedule website scraping (once per day)
        schedule.every().day.at("03:00").do(self.scrape_website)
        
        # Schedule data download (every minute)
        schedule.every(1).minutes.do(self.download_data)
        
        # Initial run to ensure we have data right away
        if not self.urls:
            logger.info("Initiële webscraping...")
            self.scrape_website()
        
        logger.info("Initiële data download...")
        self.download_data()
        
        logger.info("NMBS Data Service is gestart. Druk Ctrl+C om te stoppen.")
        
        # Run the scheduler in a loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Service wordt gestopt...")
        
    def start_background_service(self):
        """
        Start the service in a background thread
        """
        thread = threading.Thread(target=self.run_as_service, daemon=True)
        thread.start()
        return thread