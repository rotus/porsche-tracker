import requests
import time
import re
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin, urlparse, parse_qs
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CarGurusScraper:
    """Scraper for CarGurus.com Porsche listings"""
    
    def __init__(self, config):
        self.config = config
        self.base_url = "https://www.cargurus.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Setup Chrome driver options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument(f'--user-agent={config.USER_AGENT}')
    
    def build_search_url(self, **kwargs) -> str:
        """Build CarGurus search URL with filters"""
        base_search = f"{self.base_url}/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action"
        
        params = {
            'sourceContext': 'carGurusHomePageModel',
            'entitySelectingHelper.selectedEntity': 'c23449',  # Porsche make ID
            'sortDir': 'ASC',
            'sortType': 'DEAL_SCORE'
        }
        
        # Add filters based on criteria
        if kwargs.get('models'):
            # Map model names to CarGurus model IDs (you'll need to research these)
            model_mapping = {
                '911': 'm30',
                'Cayenne': 'm31',
                'Macan': 'm32',
                'Panamera': 'm33',
                'Taycan': 'm34',
                'Boxster': 'm35',
                'Cayman': 'm36'
            }
            models = kwargs['models'] if isinstance(kwargs['models'], list) else [kwargs['models']]
            for model in models:
                if model in model_mapping:
                    params[f'entitySelectingHelper.selectedEntity2'] = model_mapping[model]
        
        if kwargs.get('min_year'):
            params['minYear'] = kwargs['min_year']
        if kwargs.get('max_year'):
            params['maxYear'] = kwargs['max_year']
        
        if kwargs.get('min_price'):
            params['minPrice'] = kwargs['min_price']
        if kwargs.get('max_price'):
            params['maxPrice'] = kwargs['max_price']
        
        if kwargs.get('max_mileage'):
            params['maxMileage'] = kwargs['max_mileage']
        
        if kwargs.get('zip_code'):
            params['zip'] = kwargs['zip_code']
        if kwargs.get('max_distance'):
            params['distance'] = kwargs['max_distance']
        
        # Build URL with parameters
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_search}?{param_string}"
    
    def scrape_listings_page(self, search_url: str, max_pages: int = 5) -> List[Dict]:
        """Scrape listings from CarGurus search results"""
        all_listings = []
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(search_url)
            
            page_count = 0
            while page_count < max_pages:
                logger.info(f"Scraping page {page_count + 1}")
                
                # Wait for listings to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "cg-dealFinder-result-wrap"))
                    )
                except TimeoutException:
                    logger.warning("Timeout waiting for listings to load")
                    break
                
                # Parse current page
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                listings = self._parse_listings_from_soup(soup)
                all_listings.extend(listings)
                
                logger.info(f"Found {len(listings)} listings on page {page_count + 1}")
                
                # Try to navigate to next page
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next page']")
                    if next_button.is_enabled():
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(self.config.REQUEST_DELAY)
                        page_count += 1
                    else:
                        break
                except NoSuchElementException:
                    logger.info("No more pages available")
                    break
                
        except Exception as e:
            logger.error(f"Error scraping listings: {str(e)}")
        finally:
            if 'driver' in locals():
                driver.quit()
        
        return all_listings
    
    def _parse_listings_from_soup(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse individual listings from BeautifulSoup object"""
        listings = []
        listing_elements = soup.find_all('div', class_='cg-dealFinder-result-wrap')
        
        for element in listing_elements:
            try:
                listing = self._extract_listing_data(element)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.error(f"Error parsing listing: {str(e)}")
                continue
        
        return listings
    
    def _extract_listing_data(self, element) -> Optional[Dict]:
        """Extract data from a single listing element"""
        try:
            # Extract CarGurus ID from the element
            cargurus_id = None
            link_element = element.find('a', {'data-cg-ft': 'car-blade-link'})
            if link_element and link_element.get('href'):
                url_path = link_element['href']
                # Extract ID from URL
                match = re.search(r'/(\d+)', url_path)
                if match:
                    cargurus_id = match.group(1)
            
            if not cargurus_id:
                return None
            
            # Extract basic info
            title_element = element.find('h4', class_='cg-dealFinder-result-model')
            title_text = title_element.get_text(strip=True) if title_element else ""
            
            # Parse year, make, model from title
            year, make, model, trim = self._parse_title(title_text)
            
            # Extract price
            price_element = element.find('span', class_='cg-dealFinder-result-price')
            price = self._extract_price(price_element.get_text() if price_element else "")
            
            # Extract mileage
            mileage_element = element.find('div', class_='cg-dealFinder-result-mileage')
            mileage = self._extract_mileage(mileage_element.get_text() if mileage_element else "")
            
            # Extract location
            location_element = element.find('div', class_='cg-dealFinder-result-dealer')
            dealer_name, city, state, distance = self._parse_location(location_element.get_text() if location_element else "")
            
            # Build full URL
            full_url = urljoin(self.base_url, url_path) if link_element and link_element.get('href') else None
            
            listing_data = {
                'cargurus_id': cargurus_id,
                'make': make or 'Porsche',
                'model': model,
                'year': year,
                'trim': trim,
                'price': price,
                'mileage': mileage,
                'dealer_name': dealer_name,
                'city': city,
                'state': state,
                'distance_from_user': distance,
                'url': full_url,
                'condition': self._extract_condition(element),
                'exterior_color': self._extract_color(element, 'exterior'),
                'interior_color': self._extract_color(element, 'interior')
            }
            
            return listing_data
            
        except Exception as e:
            logger.error(f"Error extracting listing data: {str(e)}")
            return None
    
    def get_detailed_listing(self, listing_url: str) -> Dict:
        """Get detailed information for a specific listing"""
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(listing_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "cargurus-listing-title"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            details = {
                'vin': self._extract_vin(soup),
                'transmission': self._extract_transmission(soup),
                'drivetrain': self._extract_drivetrain(soup),
                'fuel_type': self._extract_fuel_type(soup),
                'description': self._extract_description(soup),
                'image_urls': self._extract_image_urls(soup),
                'dealer_details': self._extract_dealer_details(soup)
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting detailed listing: {str(e)}")
            return {}
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def _parse_title(self, title: str) -> tuple:
        """Parse year, make, model, trim from title string"""
        # Example: "2020 Porsche 911 Carrera S"
        parts = title.split()
        year = None
        make = "Porsche"
        model = None
        trim = None
        
        try:
            # First part should be year
            if parts and parts[0].isdigit():
                year = int(parts[0])
                remaining_parts = parts[1:]
            else:
                remaining_parts = parts
            
            # Skip make if present
            if remaining_parts and remaining_parts[0].lower() == 'porsche':
                remaining_parts = remaining_parts[1:]
            
            # Next part is model
            if remaining_parts:
                model = remaining_parts[0]
                # Rest is trim
                if len(remaining_parts) > 1:
                    trim = ' '.join(remaining_parts[1:])
        
        except (ValueError, IndexError):
            pass
        
        return year, make, model, trim
    
    def _extract_price(self, price_text: str) -> Optional[int]:
        """Extract numeric price from price text"""
        if not price_text:
            return None
        
        # Remove currency symbols and commas
        price_clean = re.sub(r'[^\d]', '', price_text)
        try:
            return int(price_clean)
        except ValueError:
            return None
    
    def _extract_mileage(self, mileage_text: str) -> Optional[int]:
        """Extract numeric mileage from mileage text"""
        if not mileage_text:
            return None
        
        # Look for numbers in the mileage text
        match = re.search(r'([\d,]+)', mileage_text)
        if match:
            mileage_clean = re.sub(r'[^\d]', '', match.group(1))
            try:
                return int(mileage_clean)
            except ValueError:
                pass
        
        return None
    
    def _parse_location(self, location_text: str) -> tuple:
        """Parse dealer name, city, state, distance from location text"""
        dealer_name = None
        city = None
        state = None
        distance = None
        
        # This would need to be customized based on CarGurus' actual format
        # For now, return placeholders
        return dealer_name, city, state, distance
    
    def _extract_condition(self, element) -> str:
        """Extract vehicle condition (New, Used, CPO)"""
        # Look for condition indicators in the element
        condition_element = element.find(text=re.compile(r'(New|Used|Certified|CPO)', re.I))
        if condition_element:
            text = condition_element.strip().lower()
            if 'new' in text:
                return 'New'
            elif 'certified' in text or 'cpo' in text:
                return 'CPO'
            else:
                return 'Used'
        return 'Used'  # Default assumption
    
    def _extract_color(self, element, color_type: str) -> Optional[str]:
        """Extract exterior or interior color"""
        # This would need to be implemented based on CarGurus' HTML structure
        return None
    
    def _extract_vin(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract VIN from detailed listing page"""
        vin_element = soup.find(text=re.compile(r'VIN:?\s*([A-HJ-NPR-Z0-9]{17})', re.I))
        if vin_element:
            match = re.search(r'([A-HJ-NPR-Z0-9]{17})', vin_element)
            if match:
                return match.group(1)
        return None
    
    def _extract_transmission(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract transmission type from detailed listing"""
        # Look for transmission information in the specs
        return None
    
    def _extract_drivetrain(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract drivetrain information"""
        return None
    
    def _extract_fuel_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract fuel type"""
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract listing description"""
        return None
    
    def _extract_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs from listing"""
        return []
    
    def _extract_dealer_details(self, soup: BeautifulSoup) -> Dict:
        """Extract dealer contact information"""
        return {}
