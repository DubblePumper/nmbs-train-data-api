import time
import os
import json
import logging
import traceback
import cloudscraper
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from .base_service import BaseService

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ScraperService(BaseService):
    """Service to scrape the NMBS website and extract data URLs"""
    
    def __init__(self, cache_dir='data', use_proxy=False):
        super().__init__(cache_dir)
        self.nmbs_url = os.getenv('NMBS_DATA_URL')
        
        # Expanded set of modern user agents to rotate
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
            # Opera GX
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
            # iPhone Safari
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            # Android Chrome
            'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
        ]
        self.user_agent = self.user_agents[0]  # Default to first one
        self.last_agent_idx = 0
        
        # Proxy settings (disabled by default)
        self.use_proxy = use_proxy
        self.proxy_ip = os.getenv('PROXY_IP', '185.228.81.219')
        self.proxy_port = os.getenv('PROXY_PORT', '25580')
        
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
        
        # Select a user agent
        self._rotate_user_agent()
        
        # Set custom headers to exactly match the user's browser
        logger.debug("Headers instellen om exact overeen te komen met gebruikte browser...")
        headers = self._get_headers_for_current_agent()
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
    
    def _rotate_user_agent(self):
        """Rotate to the next user agent in the list"""
        self.last_agent_idx = (self.last_agent_idx + 1) % len(self.user_agents)
        self.user_agent = self.user_agents[self.last_agent_idx]
        logger.info(f"Rotated to user agent: {self.user_agent}")
        return self.user_agent
        
    def _get_headers_for_current_agent(self):
        """Get appropriate headers for the current user agent"""
        # Use the exact headers from a working browser session as the primary option
        if self.last_agent_idx == 0:  # For the first attempt, use known working headers
            headers = {
                'authority': 'www.belgiantrain.be',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.0',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Opera GX";v="117"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'priority': 'u=0, i',
                'referer': 'https://www.belgiantrain.be/'
            }
            logger.info("Using exact headers from known working browser session")
            return headers
                
        # Base headers that work for most browsers (for subsequent attempts)
        headers = {
            'authority': 'sncb-opendata.hafas.de',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://www.belgiantrain.be/',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }
        
        # Add browser-specific headers based on the current user agent
        if 'OPR/' in self.user_agent:
            headers['sec-ch-ua'] = '"Not A(Brand";v="8", "Chromium";v="132", "Opera GX";v="117"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = '"Windows"'
        elif 'Chrome/' in self.user_agent and 'Edg/' in self.user_agent:
            headers['sec-ch-ua'] = '"Microsoft Edge";v="122", "Chromium";v="122", "Not A(Brand";v="24"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = '"Windows"'
        elif 'Chrome/' in self.user_agent:
            headers['sec-ch-ua'] = '"Chromium";v="122", "Google Chrome";v="122", "Not(A:Brand";v="24"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = '"Windows"' if 'Windows' in self.user_agent else ('"macOS"' if 'Mac' in self.user_agent else '"Android"')
        elif 'Firefox/' in self.user_agent:
            # Firefox doesn't use the sec-ch-ua headers
            pass
        elif 'iPhone' in self.user_agent or 'iPad' in self.user_agent:
            headers['sec-ch-ua-mobile'] = '?1'
            headers['sec-ch-ua-platform'] = '"iOS"'
        
        return headers
    
    def save_cookies(self):
        """Save the current cookies from the scraper"""
        cookies_dict = [{'name': c.name, 'value': c.value, 'domain': c.domain} for c in self.scraper.cookies]
        self._save_cookies(cookies_dict)
    
    def scrape_website(self):
        """
        Scrape the NMBS website to get data URLs
        This method retrieves both realtime and planning data URLs
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
            self.save_cookies()
            
            if response.status_code == 200:
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
            else:
                logger.error(f"Fout bij ophalen van NMBS website: HTTP status {response.status_code}")
                logger.error(f"Response inhoud: {response.text[:500]}...")
                
                # If we get a Cloudflare 403 error, use hardcoded fallback URLs
                if response.status_code == 403 and "cloudflare" in response.text.lower():
                    logger.warning("Cloudflare bescherming gedetecteerd, gebruik hardcoded fallback URLs")
                    return self._use_fallback_urls()
                    
                return False
                
        except Exception as e:
            logger.error(f"Fout bij webscraping: {str(e)}")
            logger.error(traceback.format_exc())
            logger.error("===== WEBSCRAPING MISLUKT =====")
            
            # Use fallback URLs if scraping fails
            logger.info("Webscraping mislukt, gebruik hardcoded fallback URLs")
            return self._use_fallback_urls()
    
    def _use_fallback_urls(self):
        """Use hardcoded fallback URLs when scraping fails"""
        logger.info("Toepassen van hardcoded fallback URLs")
        
        # Use existing hardcoded URLs first
        if not self.urls:
            self._load_urls()
        if not self.planning_urls:
            self._load_planning_urls()
            
        success = False
            
        # If we still don't have URLs, use predefined hardcoded fallbacks
        if not self.urls:
            logger.info("Gebruik van hardcoded realtime URL")
            realtime_url = {
                "real-time gegevens met info over spoorveranderingen": {
                    'url': "https://sncb-opendata.hafas.de/gtfs/realtime/d22ad6759ee25bg84ddb6c818g4dc4de_TC",
                    'filename': "NMBS_realtime_met_spoorveranderingen.bin",
                    'last_checked': self.get_timestamp()
                }
            }
            self.urls = realtime_url
            self._save_urls()
            success = True
            
        # Try alternative planning data URLs
        if not self.planning_urls:
            logger.info("Gebruik van hardcoded planning URL")
            planning_url = {
                "planningsgegevens met perroninfo (GTFS)": {
                    'url': "https://gtfs.irail.be/nmbs/gtfs/latest.zip",
                    'filename': "NMBS_planning_met_perroninfo.zip",
                    'last_checked': self.get_timestamp()
                }
            }
            self.planning_urls = planning_url
            self._save_planning_urls()
            success = True
            
        # Also try to update with alternative URLs if we already have them
        if self.urls:
            for name in self.urls:
                current_url = self.urls[name]['url']
                if "d22ad6759ee25bg84ddb6c818g4dc4de_TC" in current_url:
                    logger.info("URL bevat verouderde token, probeer alternatieve URL")
                    self.urls[name]['url'] = "https://sncb-opendata.hafas.de/gtfs/realtime/d22ad6759ee25bg84ddb6c818g4dc4de_TC"
                    self.urls[name]['last_checked'] = self.get_timestamp()
                    self._save_urls()
                    success = True
        
        if self.planning_urls:
            for name in self.planning_urls:
                current_url = self.planning_urls[name]['url']
                # If original URL, try iRail alternative
                if "d22ad6759ee25bg84ddb6c818g4dc4de_TC" in current_url:
                    logger.info("Planning URL bevat verouderde token, probeer iRail alternatief")
                    self.planning_urls[name]['url'] = "https://gtfs.irail.be/nmbs/gtfs/latest.zip"
                    self.planning_urls[name]['last_checked'] = self.get_timestamp()
                    self._save_planning_urls()
                    success = True
        
        logger.info(f"Fallback URLs toepassen: {success}")
        return success
    
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
                'last_checked': self.get_timestamp()
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
                'last_checked': self.get_timestamp()
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
            
    def get_realtime_url(self):
        """Get the URL for realtime data"""
        if not self.urls:
            self._load_urls()
            if not self.urls:
                return None
        
        for name, info in self.urls.items():
            return info.get('url')
        
        return None
    
    def get_planning_url(self):
        """Get the URL for planning data"""
        if not self.planning_urls:
            self._load_planning_urls()
            if not self.planning_urls:
                return None
        
        for name, info in self.planning_urls.items():
            return info.get('url')
        
        return None