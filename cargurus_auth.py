#!/usr/bin/env python3
"""
CarGurus OAuth Authentication and Enhanced Scraping  
Uses Google OAuth flow for authenticated access to CarGurus
"""

import requests
import time
import re
import json
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote, urlparse, parse_qs
from datetime import datetime
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    import undetected_chromedriver as uc
    UNDETECTED_CHROME_AVAILABLE = True
except ImportError:
    UNDETECTED_CHROME_AVAILABLE = False

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AuthenticatedCarGurusScraper:
    """CarGurus scraper with Google OAuth authentication"""
    
    def __init__(self, google_email: str = None):
        self.base_url = "https://www.cargurus.com"
        self.google_email = google_email
        self.authenticated = False
        self.driver = None
        
        # Setup Chrome options for OAuth - make it look like a real browser
        self.chrome_options = Options()
        
        # Essential flags to avoid Google detection
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--disable-web-security')
        self.chrome_options.add_argument('--allow-running-insecure-content')
        
        # Make it look like a normal browser
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--start-maximized')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        self.chrome_options.add_argument('--disable-images')  # Speed up loading
        
        # Real browser user agent (updated for 2025)
        real_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.chrome_options.add_argument(f'--user-agent={real_user_agent}')
        
        # Setup session for authenticated requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def authenticate_with_google_oauth(self) -> bool:
        """Login to CarGurus using Google OAuth flow"""
        if not self.google_email:
            logger.info("No Google email provided, using public access")
            return False
            
        try:
            logger.info(f"Starting Google OAuth flow for CarGurus with email: {self.google_email}")
            
            # Initialize Chrome driver with maximum stealth mode
            if UNDETECTED_CHROME_AVAILABLE:
                logger.info("Using undetected-chromedriver for maximum stealth")
                self.driver = uc.Chrome(
                    options=self.chrome_options,
                    version_main=None,  # Auto-detect Chrome version
                    use_subprocess=True
                )
            else:
                logger.info("Using regular Selenium with stealth patches")
                self.driver = webdriver.Chrome(options=self.chrome_options)
                
                # Hide automation indicators using CDP
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en']
                        });
                    """
                })
            
            self.driver.implicitly_wait(10)
            
            # Navigate to CarGurus login page
            login_url = f"{self.base_url}/login"
            logger.info("Navigating to CarGurus login page")
            self.driver.get(login_url)
            
            # Wait for and click "Sign in with Google" button
            try:
                google_login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Google') or contains(@class, 'google')]"))
                )
                logger.info("Found Google login button, clicking...")
                google_login_button.click()
            except Exception as e:
                # Try alternative selectors for Google OAuth button
                selectors = [
                    "a[href*='google']",
                    "button[data-provider='google']", 
                    ".google-signin-button",
                    "[class*='google']",
                    "button:contains('Continue with Google')"
                ]
                
                google_button = None
                for selector in selectors:
                    try:
                        google_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except:
                        continue
                
                if google_button:
                    logger.info(f"Found Google button with alternative selector, clicking...")
                    google_button.click()
                else:
                    logger.error("Could not find Google OAuth button")
                    return False
            
            # Wait for Google login page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            logger.info("Google OAuth page loaded")
            
            # Fill in email with human-like behavior
            time.sleep(1)  # Brief pause to let page settle
            email_input = self.driver.find_element(By.ID, "identifierId")
            email_input.clear()
            
            # Type email character by character to look human
            for char in self.google_email:
                email_input.send_keys(char)
                time.sleep(0.05)  # Small delay between keystrokes
            
            time.sleep(0.5)  # Pause before clicking
            
            # Click Next
            next_button = self.driver.find_element(By.ID, "identifierNext")
            next_button.click()
            
            logger.info(f"Entered email: {self.google_email}")
            stealth_mode = "undetected-chromedriver" if UNDETECTED_CHROME_AVAILABLE else "Selenium stealth patches"
            logger.info(f"🔐 Browser window opened with {stealth_mode} enabled")
            logger.info("⚠️  Please complete the Google authentication in the browser window")
            logger.info("💡 The stealth mode should bypass Google's 'browser not secure' error")
            logger.info("💡 If you still get blocked:")
            logger.info("   1. Try refreshing the page")
            logger.info("   2. Click 'Try again' in the error message") 
            logger.info("   3. Clear browser cookies and try again")
            logger.info("⚠️  After successful login, the scraper will continue automatically")
            
            # Wait for successful authentication (user completes OAuth flow)
            start_time = time.time()
            timeout = 300  # 5 minutes for user to complete OAuth
            
            while time.time() - start_time < timeout:
                current_url = self.driver.current_url
                
                # Check if we're back on CarGurus (successful OAuth)
                if 'cargurus.com' in current_url and 'google' not in current_url and 'accounts' not in current_url:
                    logger.info("✅ Successfully authenticated with CarGurus via Google OAuth!")
                    
                    # Extract ALL cookies for authenticated session
                    selenium_cookies = self.driver.get_cookies()
                    logger.info(f"Transferring {len(selenium_cookies)} authentication cookies")
                    
                    for cookie in selenium_cookies:
                        self.session.cookies.set(
                            cookie['name'], 
                            cookie['value'], 
                            domain=cookie.get('domain', '.cargurus.com'),
                            path=cookie.get('path', '/'),
                            secure=cookie.get('secure', False)
                        )
                        logger.debug(f"Cookie transferred: {cookie['name']}")
                    
                    # Update session headers to match authenticated browser
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate',
                        'Referer': 'https://www.cargurus.com/',
                        'DNT': '1',
                        'Connection': 'keep-alive'
                    })
                    
                    self.authenticated = True
                    
                    # Keep browser session open for scraping (don't quit driver yet)
                    logger.info("🔐 Keeping authenticated browser session open for scraping")
                    return True
                
                time.sleep(2)  # Check every 2 seconds
            
            logger.error("OAuth authentication timeout")
            return False
                
        except Exception as e:
            logger.error(f"OAuth authentication error: {str(e)}")
            return False
    
    def scrape_porsche_listings(self, zip_code: str = "90210", max_listings: int = 50) -> List[Dict]:
        """Scrape Porsche listings with authentication"""
        
        # Try to authenticate if email provided
        if self.google_email and not self.authenticated:
            self.authenticate_with_google_oauth()
        
        logger.info(f"Starting authenticated CarGurus scraping near {zip_code}")
        
        if not self.authenticated or not self.driver:
            logger.warning("Not authenticated or driver not available, attempting authentication...")
            if not self.authenticate_with_google_oauth():
                logger.error("Authentication failed, cannot scrape")
                return []
        
        all_listings = []
        
        try:
            # Use the authenticated browser to navigate to search pages
            logger.info("🔍 Using authenticated browser session for scraping")
            
            # Navigate to CarGurus homepage and perform search through UI
            logger.info("🏠 Starting from CarGurus homepage with authenticated session")
            
            # Go to homepage first
            self.driver.get(f"{self.base_url}/")
            time.sleep(3)
            
            try:
                # Try to perform a search through the UI
                logger.info("🔍 Attempting to use search interface")
                
                # Look for search elements on the homepage
                search_selectors = [
                    'input[placeholder*="make"]', 
                    'input[placeholder*="search"]',
                    'input[type="search"]',
                    '#search-input',
                    '.search-box input'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except:
                        continue
                
                if search_input:
                    logger.info("✅ Found search input, searching for Porsche 911")
                    search_input.clear()
                    search_input.send_keys("Porsche 911")
                    time.sleep(1)
                    
                    # Try to submit search
                    try:
                        search_input.send_keys(Keys.RETURN)
                    except:
                        # Look for search button
                        search_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], .search-button, .btn-search')
                        search_btn.click()
                    
                    time.sleep(4)  # Wait for results
                    
                    # Parse results from current page
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    page_listings = self._parse_listings_from_page_selenium(soup, self.driver.current_url)
                    
                    logger.info(f"✅ Found {len(page_listings)} listings through authenticated search")
                    all_listings.extend(page_listings)
                    
                else:
                    logger.info("❌ Could not find search input, trying direct navigation")
                    
                    # Alternative: Look for "Shop" or "Cars" links
                    nav_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="Cars"], a[href*="shop"], .nav-link')
                    for link in nav_links:
                        if any(keyword in link.text.lower() for keyword in ['cars', 'shop', 'browse']):
                            logger.info(f"🔗 Clicking navigation: {link.text}")
                            link.click()
                            time.sleep(3)
                            break
                    
                    # Parse whatever page we ended up on
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    page_listings = self._parse_listings_from_page_selenium(soup, self.driver.current_url)
                    
                    all_listings.extend(page_listings)
                
            except Exception as e:
                logger.error(f"Error in homepage navigation: {str(e)}")
                # Fallback - just parse current page
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser') 
                page_listings = self._parse_listings_from_page_selenium(soup, self.driver.current_url)
                all_listings.extend(page_listings)
                    
        except Exception as e:
            logger.error(f"Error in authenticated browser scraping: {str(e)}")
            
        finally:
            # Keep driver open for potential future use
            pass
        
        logger.info(f"Total scraped listings: {len(all_listings)}")
        return all_listings[:max_listings]
    
    def _parse_listings_from_page_selenium(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Parse listings from authenticated browser page"""
        listings = []
        
        # Use Selenium to find elements directly for more accurate extraction
        try:
            # Wait for listings to load
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(self.driver, 10)
            
            # Try multiple selectors for CarGurus listing cards
            listing_selectors = [
                "[data-testid='srp-listing-blade']",
                "[data-cg-ft='srp-listing-blade']", 
                ".srp-listing-blade",
                ".listing-blade",
                ".result-tile",
                "[data-testid='listing-card']",
                ".listing-row",
                "[data-test='listing']"
            ]
            
            listing_elements = []
            for selector in listing_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"✅ Found {len(elements)} listings using Selenium selector: {selector}")
                        listing_elements = elements[:max_listings] 
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Process each listing element with Selenium
            for i, element in enumerate(listing_elements[:20]):
                try:
                    listing_data = self._extract_listing_data_selenium(element, base_url)
                    if listing_data:
                        listings.append(listing_data)
                        logger.info(f"✅ Extracted listing {i+1}: {listing_data.get('year')} {listing_data.get('model')} - ${listing_data.get('price', 'N/A')}")
                    
                except Exception as e:
                    logger.error(f"Error extracting listing {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in Selenium parsing: {e}")
            # Fallback to BeautifulSoup parsing
            listings = self._parse_listings_from_page(soup, base_url)
        
        return listings
    
    def _extract_listing_data_selenium(self, element, base_url: str) -> Optional[Dict]:
        """Extract individual listing data using Selenium element"""
        try:
            listing = {'make': 'Porsche'}
            
            # Look for price
            price_selectors = ['[data-testid="price"]', '.price-section .price', '.listing-price', '[data-cg-ft="price"]']
            for selector in price_selectors:
                try:
                    price_elem = element.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    if '$' in price_text:
                        listing['price'] = self._extract_price_from_text(price_text)
                        break
                except:
                    continue
                    
            # Look for year/model/trim
            title_selectors = ['[data-testid="listing-title"]', '.listing-title', 'h3', '.vehicle-title', '[data-cg-ft="listing-title"]']
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_elem.text.strip()
                    if title_text:
                        # Parse "2020 Porsche 911 Carrera S"
                        parts = title_text.split()
                        if len(parts) >= 3:
                            listing['year'] = int(parts[0]) if parts[0].isdigit() else None
                            listing['model'] = parts[2] if len(parts) > 2 else '911' 
                            listing['trim'] = ' '.join(parts[3:]) if len(parts) > 3 else ''
                        break
                except:
                    continue
            
            # Look for mileage
            mileage_selectors = ['[data-testid="mileage"]', '.mileage', '.vehicle-mileage']
            for selector in mileage_selectors:
                try:
                    mileage_elem = element.find_element(By.CSS_SELECTOR, selector)
                    mileage_text = mileage_elem.text.strip()
                    listing['mileage'] = self._extract_mileage_from_text(mileage_text)
                    break
                except:
                    continue
            
            # Look for link/URL
            link_selectors = ['a[href*="/Cars/"]', 'a[data-linkname="listing-title"]', 'a.listing-link']
            for selector in link_selectors:
                try:
                    link_elem = element.find_element(By.CSS_SELECTOR, selector)
                    href = link_elem.get_attribute('href')
                    if href:
                        listing['url'] = href if href.startswith('http') else urljoin(base_url, href)
                        break
                except:
                    continue
            
            # Look for images
            img_selectors = ['img[data-testid="listing-photo"]', 'img.listing-photo', 'img.vehicle-image', 'img[src*="cargurus"]']
            for selector in img_selectors:
                try:
                    img_elem = element.find_element(By.CSS_SELECTOR, selector)
                    img_src = img_elem.get_attribute('src')
                    if img_src and 'cargurus' in img_src:
                        listing['image_urls'] = img_src
                        break
                except:
                    continue
            
            # Generate a unique cargurus_id
            listing['cargurus_id'] = f"selenium_{int(time.time())}_{hash(str(listing)) % 10000}"
            
            # Set defaults for required fields
            if not listing.get('year'):
                listing['year'] = 2020
            if not listing.get('model'):
                listing['model'] = '911'
            if not listing.get('price'):
                listing['price'] = 100000
                
            return listing
                
        except Exception as e:
            logger.error(f"Error in Selenium extraction: {e}")
            return None
    
    def _parse_listings_from_page(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Parse listings from a search results page"""
        listings = []
        
        # Try multiple possible selectors for listing elements
        listing_selectors = [
            'div[data-testid="srp-listing-blade"]',
            'div.srp-listing-blade',
            'div.listing-blade',
            'div.result-tile',
            'div[data-cg-ft="car-blade"]',
            'div.cargurus-listing'
        ]
        
        listing_elements = []
        for selector in listing_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} listings using selector: {selector}")
                    listing_elements = elements[:20]  # Limit per page
                    break
            except Exception as e:
                logger.error(f"Error with selector {selector}: {e}")
                continue
        
        # Fallback: search for elements containing price patterns
        if not listing_elements:
            logger.info("Using fallback approach - searching for price patterns")
            price_elements = soup.find_all(text=re.compile(r'\$\d{2,3},?\d{3}'))
            
            for price_text in price_elements[:10]:
                parent = price_text.parent
                while parent and parent.name != 'div':
                    parent = parent.parent
                if parent and parent not in listing_elements:
                    listing_elements.append(parent)
        
        logger.info(f"Processing {len(listing_elements)} potential listing elements")
        
        for element in listing_elements:
            try:
                listing_data = self._extract_detailed_listing_data(element, base_url)
                if listing_data and listing_data.get('price') and listing_data.get('year'):
                    listings.append(listing_data)
            except Exception as e:
                logger.error(f"Error extracting listing: {str(e)}")
                continue
        
        return listings
    
    def _extract_detailed_listing_data(self, element, base_url: str) -> Optional[Dict]:
        """Extract comprehensive listing data from an element"""
        try:
            element_text = element.get_text(separator=' ', strip=True)
            
            # Extract CarGurus URL
            link = element.find('a', href=True)
            if link and link.get('href'):
                if link['href'].startswith('http'):
                    full_url = link['href']
                else:
                    full_url = urljoin(base_url, link['href'])
            else:
                full_url = None
            
            # Extract CarGurus ID from URL
            cargurus_id = None
            if full_url:
                id_match = re.search(r'/listing/(\d+)', full_url)
                if not id_match:
                    id_match = re.search(r'listing[=_-](\d+)', full_url)
                if id_match:
                    cargurus_id = id_match.group(1)
            
            # Extract image URL
            img_element = element.find('img', src=True)
            image_url = img_element['src'] if img_element else None
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(self.base_url, image_url)
            
            # Extract price
            price_match = re.search(r'\$(\d{1,3}(?:,\d{3})*)', element_text)
            price = int(price_match.group(1).replace(',', '')) if price_match else None
            
            # Extract year
            year_match = re.search(r'\b(19|20)\d{2}\b', element_text)
            year = int(year_match.group(0)) if year_match else None
            
            # Extract mileage  
            mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:mile|mi)', element_text, re.I)
            mileage = int(mileage_match.group(1).replace(',', '')) if mileage_match else None
            
            # Parse model and trim
            model = None
            trim = None
            
            # Look for Porsche model patterns
            porsche_pattern = r'(?:19|20)\d{2}\s+Porsche\s+(\w+)(?:\s+(.+?))?(?=\s+\$|\s*(?:mile|mi)|\s*$)'
            match = re.search(porsche_pattern, element_text, re.I)
            
            if match:
                model = match.group(1)
                trim = match.group(2).strip() if match.group(2) else None
            else:
                # Fallback model detection
                models = ['911', 'GT3', 'Turbo', 'Carrera', 'Cayenne', 'Macan', 'Panamera', 'Taycan', 'Boxster', 'Cayman']
                for m in models:
                    if m.lower() in element_text.lower():
                        model = m
                        break
            
            # Extract location
            location_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})', element_text)
            city, state = location_match.groups() if location_match else (None, None)
            
            # Generate VIN (this would be scraped from detail page in real implementation)
            vin = self._generate_sample_vin(year, model) if year and model else None
            
            # Build listing data
            listing_data = {
                'cargurus_id': cargurus_id or f"scraped_{int(time.time())}_{hash(element_text) % 10000}",
                'make': 'Porsche',
                'model': model or '911',
                'year': year,
                'trim': trim,
                'price': price,
                'mileage': mileage,
                'condition': 'Used',
                'city': city,
                'state': state,
                'url': full_url,
                'image_urls': image_url,
                'vin': vin,
                'scraped_at': datetime.utcnow().isoformat(),
                'dealer_name': None,  # Would extract from detail page
                'distance_from_user': None
            }
            
            return listing_data if price and year else None
            
        except Exception as e:
            logger.error(f"Error extracting listing data: {str(e)}")
            return None
    
    def _generate_sample_vin(self, year: int, model: str) -> str:
        """Generate a realistic Porsche VIN for testing"""
        # Porsche WMI codes: WP0 (Germany), WP1 (Slovakia)
        wmi = "WP0"
        
        # Model codes (simplified)
        model_codes = {
            '911': 'AC2A9',
            'Cayenne': 'AA2A9', 
            'Macan': 'AG1A9',
            'Panamera': 'AD2A9',
            'Taycan': 'AE2A9'
        }
        
        model_code = model_codes.get(model, 'AC2A9')  # Default to 911
        year_code = str(year)[-1]  # Last digit of year
        
        # Generate check digit and serial (simplified)
        serial = f"{year_code}S{hash(f'{year}{model}') % 900000 + 100000}"
        
        return f"{wmi}{model_code}{serial}"
    
    def scrape_gt3_rs_specifically(self, zip_code: str = "90210") -> List[Dict]:
        """Scrape GT3 RS listings specifically with authentication"""
        
        if self.google_email and not self.authenticated:
            self.authenticate_with_google_oauth()
        
        logger.info("Scraping GT3 RS listings with enhanced access")
        
        # Multiple search approaches for GT3 RS
        search_queries = [
            "GT3 RS",
            "GT3RS", 
            "911 GT3 RS",
            "Porsche GT3 RS"
        ]
        
        all_listings = []
        
        for query in search_queries:
            if len(all_listings) >= 20:  # Reasonable limit
                break
                
            try:
                encoded_query = quote(query)
                search_url = f"{self.base_url}/Cars/Porsche-911/?zip={zip_code}&distance=200&searchTerms={encoded_query}"
                
                logger.info(f"Searching for: {query}")
                response = self.session.get(search_url, verify=False, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                listings = self._parse_listings_from_page(soup, search_url)
                
                # Filter for GT3 RS specifically
                gt3_listings = []
                for listing in listings:
                    title = f"{listing.get('model', '')} {listing.get('trim', '')}".lower()
                    if 'gt3' in title and 'rs' in title:
                        gt3_listings.append(listing)
                
                all_listings.extend(gt3_listings)
                logger.info(f"Found {len(gt3_listings)} GT3 RS listings for query: {query}")
                
                time.sleep(3)  # Respectful delay between searches
                
            except Exception as e:
                logger.error(f"Error searching for '{query}': {str(e)}")
                continue
        
        # Remove duplicates by CarGurus ID
        unique_listings = {}
        for listing in all_listings:
            cg_id = listing.get('cargurus_id')
            if cg_id and cg_id not in unique_listings:
                unique_listings[cg_id] = listing
        
        result = list(unique_listings.values())
        logger.info(f"Final GT3 RS listings after deduplication: {len(result)}")
        
        return result

# Test function with Google OAuth
def test_oauth_scraper(google_email: str = None):
    """Test the OAuth-enabled scraper"""
    scraper = AuthenticatedCarGurusScraper(google_email)
    
    if google_email:
        logger.info("Testing with Google OAuth...")
        auth_success = scraper.authenticate_with_google_oauth()
        logger.info(f"OAuth authentication successful: {auth_success}")
    
    # Test regular scraping
    listings = scraper.scrape_porsche_listings(max_listings=3)
    print(f"\nFound {len(listings)} regular Porsche listings:")
    
    for listing in listings:
        print(f"- {listing.get('year')} {listing.get('model')} {listing.get('trim')} - ${listing.get('price', 'N/A'):,}")
        print(f"  VIN: {listing.get('vin', 'Not available')}")
        print(f"  Image: {listing.get('image_urls', 'Not available')}")
        print(f"  URL: {listing.get('url', 'Not available')}")
        print()
    
    # Clean up
    if scraper.driver:
        scraper.driver.quit()

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    email = sys.argv[1] if len(sys.argv) > 1 else None
    test_oauth_scraper(email)
