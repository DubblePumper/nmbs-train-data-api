import os
import json
import time
import logging
import threading
import schedule
import cloudscraper
import zipfile
import io
import csv
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
import traceback

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
    2. Downloads the actual data files frequently (realtime and planning data)
    3. Maintains a cache of the latest data
    4. Provides an API to access the data
    """
    
    def __init__(self, cache_dir='data', use_proxy=False):
        self.cache_dir = cache_dir
        self.realtime_dir = os.path.join(cache_dir, 'Real-time_gegevens')
        self.planning_dir = os.path.join(cache_dir, 'Planning_gegevens')
        self.urls_file = os.path.join(self.realtime_dir, 'data_urls.json')
        self.planning_urls_file = os.path.join(self.planning_dir, 'planning_urls.json')
        self.last_updated_file = os.path.join(self.realtime_dir, 'last_updated.json')
        self.planning_updated_file = os.path.join(self.planning_dir, 'planning_updated.json')
        self.urls = {}
        self.planning_urls = {}
        self.cookies_file = os.getenv('COOKIES_FILE', 'data/cookies.json')
        self.nmbs_url = os.getenv('NMBS_DATA_URL')
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        
        # Proxy settings (disabled by default)
        self.use_proxy = use_proxy
        self.proxy_ip = os.getenv('PROXY_IP', '185.228.81.219')
        self.proxy_port = os.getenv('PROXY_PORT', '25580')
        
        # Create directories if they don't exist
        os.makedirs(self.realtime_dir, exist_ok=True)
        os.makedirs(self.planning_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
        
        # Create subdirectories for extracted planning data
        self.planning_extracted_dir = os.path.join(self.planning_dir, 'extracted')
        os.makedirs(self.planning_extracted_dir, exist_ok=True)
        
        # Load existing URLs if available
        self._load_urls()
        self._load_planning_urls()
        
        # Create scraper
        self.scraper = self._create_scraper()
    
    def _create_scraper(self):
        """Create a CloudScraper instance with cookies if available"""
        logger.info("Initialiseren van web scraper...")
        
        # Setup browser config
        browser_config = {
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
        logger.debug(f"Browser configuratie: {browser_config}")
        
        # Setup proxies if enabled
        proxies = None
        if self.use_proxy:
            proxy_url = f"http://{self.proxy_ip}:{self.proxy_port}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            logger.info(f"Using proxy: {proxy_url}")
        else:
            logger.info("Geen proxy geconfigureerd")
        
        # Create scraper with custom headers and proxy
        logger.info("CloudScraper instantie aanmaken...")
        try:
            scraper = cloudscraper.create_scraper(
                browser=browser_config,
                delay=5
            )
            logger.info("CloudScraper succesvol geïnitialiseerd")
        except Exception as e:
            logger.error(f"Fout bij aanmaken CloudScraper: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        
        # Set custom headers to exactly match the user's browser
        logger.debug("Headers instellen om exact overeen te komen met gebruikte browser...")
        headers = {
            'authority': 'sncb-opendata.hafas.de',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://www.belgiantrain.be/',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Opera GX";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'priority': 'u=0, i',
            'Connection': 'keep-alive',
            'DNT': '1'
        }
        logger.debug(f"Instellen van exacte headers: {headers}")
        scraper.headers.update(headers)
        
        # Apply proxies if enabled
        if proxies:
            logger.debug(f"Proxies toepassen: {proxies}")
            scraper.proxies = proxies
        
        # Load cookies if available
        logger.info(f"Cookies bestand controleren: {self.cookies_file}")
        if os.path.exists(self.cookies_file):
            try:
                logger.info(f"Cookies laden van: {self.cookies_file}")
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    logger.info(f"Cookies geladen uit bestand: {len(cookies)} cookies gevonden")
                    
                    # Use cookies for the scraper
                    for cookie in cookies:
                        logger.debug(f"Cookie toevoegen: {cookie['name']} voor domein {cookie['domain']}")
                        scraper.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            except Exception as e:
                logger.warning(f"Fout bij laden van cookies: {str(e)}")
                logger.warning(traceback.format_exc())
        else:
            logger.info("Geen cookies bestand gevonden, nieuwe sessie wordt gestart")
        
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
    
    def _load_planning_urls(self):
        """Load cached planning URLs from file"""
        if os.path.exists(self.planning_urls_file):
            try:
                with open(self.planning_urls_file, 'r') as f:
                    self.planning_urls = json.load(f)
                    logger.info(f"Geladen planning URLs: {len(self.planning_urls)} gevonden")
            except Exception as e:
                logger.error(f"Fout bij laden van planning URLs: {str(e)}")
                self.planning_urls = {}
    
    def _save_planning_urls(self):
        """Save planning URLs to cache file"""
        try:
            with open(self.planning_urls_file, 'w') as f:
                json.dump(self.planning_urls, f, indent=2)
            logger.info(f"Planning URLs opgeslagen: {len(self.planning_urls)}")
        except Exception as e:
            logger.error(f"Fout bij opslaan van planning URLs: {str(e)}")
    
    def scrape_website(self):
        """
        Scrape the NMBS website to get data URLs
        This method now retrieves both realtime and planning data URLs
        """
        if not self.nmbs_url:
            logger.error("NMBS_DATA_URL is niet geconfigureerd in .env file")
            return False
        
        logger.info(f"===== START WEBSCRAPING van {self.nmbs_url} =====")
        logger.info(f"Scraper configuratie: User-Agent: {self.scraper.headers.get('User-Agent')}")
        logger.info(f"Proxy ingeschakeld: {self.use_proxy}")
        if self.use_proxy:
            logger.info(f"Proxy details: {self.proxy_ip}:{self.proxy_port}")
        
        try:
            logger.info("HTTP verzoek verzenden naar NMBS website...")
            logger.debug(f"Volledige URL: {self.nmbs_url}")
            
            # Log all request headers for debugging
            logger.debug("===== REQUEST HEADERS =====")
            for header, value in self.scraper.headers.items():
                logger.debug(f"{header}: {value}")
            logger.debug("==========================")
            
            start_time = time.time()
            response = self.scraper.get(self.nmbs_url)
            elapsed_time = time.time() - start_time
            
            logger.info(f"Verzoek voltooid in {elapsed_time:.2f} seconden")
            logger.info(f"HTTP status code: {response.status_code}")
            
            # Save cookies after successful request
            logger.info("Cookies opslaan na succesvol verzoek...")
            self._save_cookies()
            
            if response.status_code != 200:
                logger.error(f"Fout bij ophalen van NMBS website: HTTP status {response.status_code}")
                logger.error(f"Response inhoud: {response.text[:500]}...")
                return False
            
            # Parse the HTML
            logger.info("HTML parsen met BeautifulSoup...")
            content_length = len(response.text)
            logger.info(f"Ontvangen HTML grootte: {content_length} bytes")
            
            # Save the raw HTML response for debugging
            try:
                debug_html_path = os.path.join(self.realtime_dir, 'debug_response.html')
                with open(debug_html_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.debug(f"Ruwe HTML respons opgeslagen naar {debug_html_path} voor debugging")
            except Exception as e:
                logger.warning(f"Kon ruwe HTML respons niet opslaan: {str(e)}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First get realtime data URL with track changes
            realtime_success = self._scrape_realtime_url(soup)
            
            # Then get planning data URL with platform info
            planning_success = self._scrape_planning_url(soup)
            
            logger.info(f"Website scraping resultaten: Realtime: {realtime_success}, Planning: {planning_success}")
            logger.info("===== EINDE WEBSCRAPING =====")
            
            return realtime_success or planning_success
            
        except Exception as e:
            logger.error(f"Fout bij webscraping: {str(e)}")
            logger.error(traceback.format_exc())
            logger.error("===== WEBSCRAPING MISLUKT =====")
            return False
    
    def _scrape_realtime_url(self, soup):
        """Extract realtime data URL with track changes from BeautifulSoup object"""
        # Init new URLs dict - we'll only keep track changes URL
        new_urls = {}
        track_changes_url = None
        
        # Find the real-time data links section
        logger.info("Zoeken naar real-time data links met spoorveranderingen in de HTML...")
        
        # Try different approaches to find the URL with track changes
        
        # Approach 1: Look for specific text in links
        logger.info("Methode 1: Zoeken naar links met tekst over spoorveranderingen...")
        all_links = soup.find_all('a')
        
        for link in all_links:
            span_element = link.find('span')
            link_text = span_element.text.strip() if span_element else link.text.strip()
            url = link.get('href', '')
            
            # Track changes link specific text
            if ("spoorveranderingen" in link_text.lower() or 
                "met info over spoor" in link_text.lower()):
                logger.info(f"Link met spoorveranderingen gevonden: '{link_text}'")
                logger.info(f"URL: {url}")
                track_changes_url = {
                    "text": link_text,
                    "url": url
                }
                break
        
        # Approach 2: Look for the specific URL pattern
        if not track_changes_url:
            logger.info("Methode 2: Zoeken naar specifiek URL patroon...")
            tc_pattern_links = soup.find_all('a', href=lambda href: href and "TC" in href)
            
            if tc_pattern_links and len(tc_pattern_links) > 0:
                url = tc_pattern_links[0].get('href')
                span_element = tc_pattern_links[0].find('span')
                text = span_element.text.strip() if span_element else "Real-time gegevens met spoorveranderingen"
                
                logger.info(f"Link met 'TC' patroon gevonden: '{text}'")
                logger.info(f"URL: {url}")
                track_changes_url = {
                    "text": text,
                    "url": url
                }
        
        # Approach 3: Direct URL matching for d22ad6759ee25bg84ddb6c818g4dc4de_TC
        if not track_changes_url:
            logger.info("Methode 3: Zoeken naar specifieke URL met d22ad6759ee25bg84ddb6c818g4dc4de_TC...")
            specific_url_links = soup.find_all('a', href=lambda href: href and "d22ad6759ee25bg84ddb6c818g4dc4de_TC" in href)
            
            if specific_url_links and len(specific_url_links) > 0:
                url = specific_url_links[0].get('href')
                span_element = specific_url_links[0].find('span')
                text = span_element.text.strip() if span_element else "Real-time gegevens met spoorveranderingen"
                
                logger.info(f"Link met specifiek ID patroon gevonden: '{text}'")
                logger.info(f"URL: {url}")
                track_changes_url = {
                    "text": text,
                    "url": url
                }
        
        # Fallback to hardcoded URL if nothing found
        if not track_changes_url:
            logger.warning("Geen link met spoorveranderingen gevonden, gebruik hardcoded URL...")
            track_changes_url = {
                "text": "real-time gegevens met info over spoorveranderingen",
                "url": "https://sncb-opendata.hafas.de/gtfs/realtime/d22ad6759ee25bg84ddb6c818g4dc4de_TC"
            }
        
        # Add the track changes URL to our results
        if track_changes_url:
            text = track_changes_url["text"]
            url = track_changes_url["url"]
            
            logger.info(f"Real-time data link met spoorveranderingen: '{text}'")
            logger.info(f"URL: {url}")
            
            filename = f"NMBS_realtime_met_spoorveranderingen.bin"
            logger.info(f"Wordt opgeslagen als: {filename}")
            
            new_urls[text] = {
                'url': url,
                'filename': filename,
                'last_checked': datetime.now().isoformat()
            }
        
            # Update URLs and save
            self.urls = new_urls
            logger.info(f"Realtime URLs bijwerken: {len(self.urls)} gevonden")
            self._save_urls()
            logger.info(f"Realtime data scraping succesvol: URL met spoorveranderingen opgeslagen")
            return True
        else:
            logger.error("Geen real-time data link met spoorveranderingen gevonden.")
            return False
    
    def _scrape_planning_url(self, soup):
        """Extract planning data URL with platform info from BeautifulSoup object"""
        # Init new planning URLs dict
        new_planning_urls = {}
        planning_url = None
        
        # Find the planning data links section
        logger.info("Zoeken naar planningsgegevens met perroninfo in de HTML...")
        
        # Try different approaches to find the URL with platform info
        
        # Approach 1: Look for specific text in links
        logger.info("Methode 1: Zoeken naar links met tekst over planningsgegevens met perroninfo...")
        all_links = soup.find_all('a')
        
        for link in all_links:
            span_element = link.find('span')
            link_text = span_element.text.strip() if span_element else link.text.strip()
            url = link.get('href', '')
            
            # Planning data with platform info text
            if ("planningsgegevens met perroninfo" in link_text.lower() or 
                "met perroninfo" in link_text.lower()):
                logger.info(f"Link met planningsgegevens met perroninfo gevonden: '{link_text}'")
                logger.info(f"URL: {url}")
                planning_url = {
                    "text": link_text,
                    "url": url
                }
                break
        
        # Approach 2: Look for the specific URL pattern
        if not planning_url:
            logger.info("Methode 2: Zoeken naar specifiek URL patroon voor planningsgegevens...")
            tc_pattern_links = soup.find_all('a', href=lambda href: href and "static" in href and "TC" in href)
            
            if tc_pattern_links and len(tc_pattern_links) > 0:
                url = tc_pattern_links[0].get('href')
                span_element = tc_pattern_links[0].find('span')
                text = span_element.text.strip() if span_element else "Planningsgegevens met perroninfo (GTFS)"
                
                logger.info(f"Link met 'static/TC' patroon gevonden: '{text}'")
                logger.info(f"URL: {url}")
                planning_url = {
                    "text": text,
                    "url": url
                }
        
        # Approach 3: Direct URL matching
        if not planning_url:
            logger.info("Methode 3: Zoeken naar specifieke URL met d22ad6759ee25bg84ddb6c818g4dc4de_TC in static...")
            specific_url_links = soup.find_all('a', href=lambda href: href and "static/d22ad6759ee25bg84ddb6c818g4dc4de_TC" in href)
            
            if specific_url_links and len(specific_url_links) > 0:
                url = specific_url_links[0].get('href')
                span_element = specific_url_links[0].find('span')
                text = span_element.text.strip() if span_element else "Planningsgegevens met perroninfo (GTFS)"
                
                logger.info(f"Link met specifiek ID patroon gevonden: '{text}'")
                logger.info(f"URL: {url}")
                planning_url = {
                    "text": text,
                    "url": url
                }
        
        # Fallback to hardcoded URL if nothing found
        if not planning_url:
            logger.warning("Geen link met planningsgegevens met perroninfo gevonden, gebruik hardcoded URL...")
            planning_url = {
                "text": "planningsgegevens met perroninfo (GTFS)",
                "url": "https://sncb-opendata.hafas.de/gtfs/static/d22ad6759ee25bg84ddb6c818g4dc4de_TC"
            }
        
        # Add the planning URL to our results
        if planning_url:
            text = planning_url["text"]
            url = planning_url["url"]
            
            logger.info(f"Planningsgegevens link met perroninfo: '{text}'")
            logger.info(f"URL: {url}")
            
            filename = f"NMBS_planning_met_perroninfo.zip"
            logger.info(f"Wordt opgeslagen als: {filename}")
            
            new_planning_urls[text] = {
                'url': url,
                'filename': filename,
                'last_checked': datetime.now().isoformat()
            }
        
            # Update URLs and save
            self.planning_urls = new_planning_urls
            logger.info(f"Planning URLs bijwerken: {len(self.planning_urls)} gevonden")
            self._save_planning_urls()
            logger.info(f"Planning data scraping succesvol: URL met perroninfo opgeslagen")
            return True
        else:
            logger.error("Geen planningsgegevens link met perroninfo gevonden.")
            return False
    
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
        if not self.urls:
            logger.warning("Geen realtime URLs beschikbaar voor data download. Run scrape_website eerst.")
            return False
        
        successful_downloads = 0
        update_info = {}
        
        for name, info in self.urls.items():
            url = info['url']
            filename = info['filename']
            output_path = os.path.join(self.realtime_dir, filename)
            
            logger.info(f"Downloading realtime data {filename} van {url}...")
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
        if not self.planning_urls:
            logger.warning("Geen planning URLs beschikbaar voor data download. Run scrape_website eerst.")
            return False
        
        successful_downloads = 0
        update_info = {}
        
        for name, info in self.planning_urls.items():
            url = info['url']
            filename = info['filename']
            output_path = os.path.join(self.planning_dir, filename)
            
            logger.info(f"Downloading planning data {filename} van {url}...")
            try:
                start_time = time.time()
                data_response = self.scraper.get(url)
                elapsed_time = time.time() - start_time
                logger.info(f"Download voltooid in {elapsed_time:.2f} seconden")
                
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
                            'last_downloaded': datetime.now().isoformat(),
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
    
    def get_latest_realtime_data(self):
        """
        API method to get the latest realtime data
        
        Returns:
            dict: The latest GTFS real-time data as a dictionary
        """
        # Load last updated info
        if not os.path.exists(self.last_updated_file):
            logger.warning("Geen realtime update info beschikbaar. Run download_data eerst.")
            return None
        
        try:
            with open(self.last_updated_file, 'r') as f:
                update_info = json.load(f)
            
            # Find the first available data
            if update_info:
                target_key = list(update_info.keys())[0]
                
                # Load the JSON file
                json_file = update_info[target_key]['json_file']
                if os.path.exists(json_file):
                    with open(json_file, 'r') as f:
                        return json.load(f)
                else:
                    logger.warning(f"Realtime JSON bestand niet gevonden: {json_file}")
                    return None
            else:
                logger.warning("Geen realtime data info gevonden")
                return None
                
        except Exception as e:
            logger.error(f"Fout bij ophalen van laatste realtime data: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def get_planning_data_list(self):
        """
        Get a list of available planning data files
        
        Returns:
            list: A list of the available planning data files
        """
        # Load planning updated info
        if not os.path.exists(self.planning_updated_file):
            logger.warning("Geen planning update info beschikbaar. Run download_data eerst.")
            return []
        
        try:
            with open(self.planning_updated_file, 'r') as f:
                update_info = json.load(f)
            
            # Get the list of files from the first available data
            if update_info:
                target_key = list(update_info.keys())[0]
                return update_info[target_key].get('extracted_files', [])
            else:
                logger.warning("Geen planning data info gevonden")
                return []
                
        except Exception as e:
            logger.error(f"Fout bij ophalen van planning bestandslijst: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def get_planning_data_file(self, filename):
        """
        Get a specific planning data file content
        
        Args:
            filename: The name of the file to get
            
        Returns:
            dict/list: The file content as JSON (for CSV/TXT files)
            str: The file content as string (for other files)
        """
        file_path = os.path.join(self.planning_extracted_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"Planning bestand niet gevonden: {file_path}")
            return None
        
        logger.info(f"Ophalen van planning bestand: {filename}")
        
        try:
            # Determine file type and parse accordingly
            ext = os.path.splitext(filename)[1].lower()
            
            # CSV files
            if ext == '.csv':
                return self._parse_csv_file(file_path)
            
            # TXT files (GTFS format)
            elif ext == '.txt':
                return self._parse_txt_file(file_path)
            
            # CFG files
            elif ext == '.cfg':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Other types, just return as string
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                
        except Exception as e:
            logger.error(f"Fout bij ophalen van planning bestand {filename}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _parse_csv_file(self, file_path):
        """Parse a CSV file and return as JSON"""
        try:
            df = pd.read_csv(file_path)
            return json.loads(df.to_json(orient='records'))
        except Exception as e:
            logger.error(f"Fout bij parsen van CSV bestand {file_path}: {str(e)}")
            
            # Try alternative parsing if pandas fails
            try:
                result = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        result.append(dict(row))
                return result
            except Exception as e2:
                logger.error(f"Alternatieve CSV parsing mislukt: {str(e2)}")
                return None
    
    def _parse_txt_file(self, file_path):
        """Parse a GTFS TXT file and return as JSON"""
        try:
            # Try to parse as a CSV (GTFS txt files are typically comma-separated)
            df = pd.read_csv(file_path)
            return json.loads(df.to_json(orient='records'))
        except Exception as e:
            logger.error(f"Fout bij parsen van TXT bestand {file_path}: {str(e)}")
            
            # Try alternative parsing if pandas fails
            try:
                result = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        result.append(dict(row))
                return result
            except Exception as e2:
                logger.error(f"Alternatieve TXT parsing mislukt: {str(e2)}")
                
                # Fall back to plain text
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except:
                    return None
    
    def get_latest_data(self, include_track_changes=True):
        """
        [DEPRECATED] Use get_latest_realtime_data() instead
        API method to get the latest realtime data
        
        Args:
            include_track_changes: Whether to get data with track change info
            
        Returns:
            dict: The latest GTFS real-time data as a dictionary
        """
        return self.get_latest_realtime_data()
    
    def run_as_service(self):
        """
        Run the service with scheduled tasks
        """
        # Schedule website scraping (once per day)
        schedule.every().day.at("03:00").do(self.scrape_website)
        
        # Schedule data download (every 30 seconds for both realtime and planning)
        schedule.every(30).seconds.do(self.download_data)
        
        # Initial run to ensure we have data right away
        if not self.urls or not self.planning_urls:
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