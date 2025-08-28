import logging
from datetime import datetime
from typing import List, Dict
from app import db
from app.models import Listing, WatchCriteria, PriceHistory, VinData
from app.scrapers import CarGurusScraper, VinEnricher
from app.monitoring.notification_service import NotificationService
import json

logger = logging.getLogger(__name__)

class ListingMonitor:
    """Monitor for new Porsche listings based on user criteria"""
    
    def __init__(self, config):
        self.config = config
        self.scraper = CarGurusScraper(config)
        self.vin_enricher = VinEnricher(config)
        self.notification_service = NotificationService(config)
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle for all active watch criteria"""
        logger.info("Starting monitoring cycle...")
        
        try:
            # Get all active watch criteria
            active_criteria = WatchCriteria.query.filter_by(is_active=True).all()
            logger.info(f"Found {len(active_criteria)} active watch criteria")
            
            for criteria in active_criteria:
                logger.info(f"Processing criteria: {criteria.name}")
                self._process_criteria(criteria)
                
                # Update last checked timestamp
                criteria.last_checked = datetime.utcnow()
                db.session.commit()
            
            logger.info("Monitoring cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {str(e)}")
            db.session.rollback()
    
    def _process_criteria(self, criteria: WatchCriteria):
        """Process a single watch criteria"""
        try:
            # Build search parameters from criteria
            search_params = self._criteria_to_search_params(criteria)
            
            # Build search URL
            search_url = self.scraper.build_search_url(**search_params)
            logger.info(f"Searching with URL: {search_url}")
            
            # Scrape listings
            scraped_listings = self.scraper.scrape_listings_page(search_url, max_pages=3)
            logger.info(f"Found {len(scraped_listings)} listings for criteria: {criteria.name}")
            
            new_listings = []
            
            for scraped_data in scraped_listings:
                # Check if listing already exists
                existing_listing = Listing.query.filter_by(
                    cargurus_id=scraped_data['cargurus_id']
                ).first()
                
                if existing_listing:
                    # Update existing listing
                    self._update_existing_listing(existing_listing, scraped_data)
                else:
                    # Create new listing
                    new_listing = self._create_new_listing(scraped_data, criteria)
                    if new_listing and criteria.matches_listing(new_listing):
                        new_listings.append(new_listing)
            
            # Send notifications for new matching listings
            if new_listings:
                self._send_new_listing_notifications(new_listings, criteria)
            
        except Exception as e:
            logger.error(f"Error processing criteria {criteria.name}: {str(e)}")
    
    def _criteria_to_search_params(self, criteria: WatchCriteria) -> Dict:
        """Convert WatchCriteria to search parameters"""
        params = {}
        
        if criteria.models:
            models_list = json.loads(criteria.models)
            params['models'] = models_list
        
        if criteria.min_year:
            params['min_year'] = criteria.min_year
        if criteria.max_year:
            params['max_year'] = criteria.max_year
        
        if criteria.min_price:
            params['min_price'] = criteria.min_price
        if criteria.max_price:
            params['max_price'] = criteria.max_price
        
        if criteria.max_mileage:
            params['max_mileage'] = criteria.max_mileage
        
        if criteria.user_zip_code:
            params['zip_code'] = criteria.user_zip_code
        if criteria.max_distance:
            params['max_distance'] = criteria.max_distance
        
        return params
    
    def _update_existing_listing(self, listing: Listing, scraped_data: Dict):
        """Update an existing listing with new data"""
        try:
            # Check for price changes
            old_price = listing.price
            new_price = scraped_data.get('price')
            
            if new_price and new_price != old_price:
                # Record price change
                price_record = PriceHistory.create_price_record(listing, old_price)
                db.session.add(price_record)
                
                # Update listing price
                listing.price = new_price
                listing.last_updated = datetime.utcnow()
                
                logger.info(f"Price change detected for listing {listing.id}: ${old_price} -> ${new_price}")
                
                # Send price change notification if listing is watched
                if listing.is_watched:
                    self._send_price_change_notification(listing, old_price, new_price)
            
            # Update other fields that might have changed
            for field in ['mileage', 'dealer_name', 'city', 'state', 'distance_from_user']:
                if scraped_data.get(field) is not None:
                    setattr(listing, field, scraped_data[field])
            
            listing.last_updated = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating listing {listing.id}: {str(e)}")
            db.session.rollback()
    
    def _create_new_listing(self, scraped_data: Dict, criteria: WatchCriteria) -> Listing:
        """Create a new listing from scraped data"""
        try:
            # Calculate distance if zip codes are available
            distance = None
            if criteria.user_zip_code and scraped_data.get('zip_code'):
                distance = self._calculate_distance(
                    criteria.user_zip_code, 
                    scraped_data['zip_code']
                )
                scraped_data['distance_from_user'] = distance
            
            # Create listing object
            listing = Listing(
                cargurus_id=scraped_data['cargurus_id'],
                make=scraped_data.get('make', 'Porsche'),
                model=scraped_data.get('model'),
                year=scraped_data.get('year'),
                trim=scraped_data.get('trim'),
                price=scraped_data.get('price'),
                mileage=scraped_data.get('mileage'),
                condition=scraped_data.get('condition', 'Used'),
                exterior_color=scraped_data.get('exterior_color'),
                interior_color=scraped_data.get('interior_color'),
                vin=scraped_data.get('vin'),
                transmission=scraped_data.get('transmission'),
                drivetrain=scraped_data.get('drivetrain'),
                fuel_type=scraped_data.get('fuel_type'),
                dealer_name=scraped_data.get('dealer_name'),
                city=scraped_data.get('city'),
                state=scraped_data.get('state'),
                zip_code=scraped_data.get('zip_code'),
                distance_from_user=distance,
                url=scraped_data.get('url'),
                description=scraped_data.get('description')
            )
            
            db.session.add(listing)
            db.session.flush()  # Get the ID
            
            # Create initial price history record
            price_record = PriceHistory.create_price_record(listing)
            db.session.add(price_record)
            
            # Get detailed listing data if URL is available
            if listing.url:
                detailed_data = self.scraper.get_detailed_listing(listing.url)
                if detailed_data:
                    # Update listing with detailed data
                    for field, value in detailed_data.items():
                        if hasattr(listing, field) and value:
                            setattr(listing, field, value)
            
            # Enrich with VIN data if VIN is available
            if listing.vin:
                self._enrich_listing_with_vin_data(listing)
            
            db.session.commit()
            
            logger.info(f"Created new listing: {listing.year} {listing.make} {listing.model} - ${listing.price}")
            
            return listing
            
        except Exception as e:
            logger.error(f"Error creating new listing: {str(e)}")
            db.session.rollback()
            return None
    
    def _enrich_listing_with_vin_data(self, listing: Listing):
        """Enrich listing with VIN data"""
        try:
            if not listing.vin:
                return
            
            # Check if VIN data already exists
            existing_vin_data = VinData.query.filter_by(listing_id=listing.id).first()
            if existing_vin_data:
                return
            
            logger.info(f"Enriching listing {listing.id} with VIN data: {listing.vin}")
            
            # Get enriched VIN data
            vin_data_dict = self.vin_enricher.enrich_vin_data(listing.vin)
            
            if vin_data_dict:
                # Create VinData record
                vin_data = VinData(
                    listing_id=listing.id,
                    vin=listing.vin,
                    engine=vin_data_dict.get('engine'),
                    engine_size=vin_data_dict.get('engine_size'),
                    engine_cylinders=vin_data_dict.get('engine_cylinders'),
                    horsepower=vin_data_dict.get('horsepower'),
                    torque=vin_data_dict.get('torque'),
                    plant_country=vin_data_dict.get('plant_country'),
                    plant_city=vin_data_dict.get('plant_city'),
                    plant_company_name=vin_data_dict.get('plant_company_name'),
                    optional_equipment=vin_data_dict.get('optional_equipment'),
                    standard_equipment=vin_data_dict.get('standard_equipment'),
                    msrp=vin_data_dict.get('msrp'),
                    market_value_estimate=vin_data_dict.get('market_value_estimate'),
                    market_value_source=vin_data_dict.get('market_value_source'),
                    depreciation_rate=vin_data_dict.get('depreciation_rate'),
                    accident_history=vin_data_dict.get('accident_history'),
                    service_records_count=vin_data_dict.get('service_records_count'),
                    previous_owners_count=vin_data_dict.get('previous_owners_count'),
                    title_issues=vin_data_dict.get('title_issues'),
                    recall_count=vin_data_dict.get('recall_count', 0),
                    open_recalls=vin_data_dict.get('open_recalls'),
                    completed_recalls=vin_data_dict.get('completed_recalls'),
                    data_source=vin_data_dict.get('data_source'),
                    api_response_raw=vin_data_dict.get('api_response_raw'),
                    data_quality_score=vin_data_dict.get('data_quality_score', 0.0),
                    confidence_score=vin_data_dict.get('confidence_score', 0.0)
                )
                
                db.session.add(vin_data)
                logger.info(f"Added VIN data for listing {listing.id}")
                
        except Exception as e:
            logger.error(f"Error enriching listing {listing.id} with VIN data: {str(e)}")
    
    def _send_new_listing_notifications(self, listings: List[Listing], criteria: WatchCriteria):
        """Send notifications for new matching listings"""
        try:
            if not criteria.email_notifications and not criteria.sms_notifications:
                return
            
            logger.info(f"Sending notifications for {len(listings)} new listings")
            
            self.notification_service.send_new_listing_alert(listings, criteria)
            
        except Exception as e:
            logger.error(f"Error sending new listing notifications: {str(e)}")
    
    def _send_price_change_notification(self, listing: Listing, old_price: int, new_price: int):
        """Send price change notification for a watched listing"""
        try:
            # Get criteria that would match this listing for notification settings
            matching_criteria = WatchCriteria.query.filter_by(is_active=True).all()
            
            for criteria in matching_criteria:
                if criteria.matches_listing(listing):
                    self.notification_service.send_price_change_alert(listing, old_price, new_price, criteria)
                    break
                    
        except Exception as e:
            logger.error(f"Error sending price change notification: {str(e)}")
    
    def _calculate_distance(self, zip1: str, zip2: str) -> float:
        """Calculate distance between two ZIP codes"""
        # This is a placeholder - you'd need to implement actual distance calculation
        # using a geocoding service or ZIP code database
        return 0.0
    
    def mark_listing_as_watched(self, listing_id: int):
        """Mark a listing as watched for price tracking"""
        try:
            listing = Listing.query.get(listing_id)
            if listing:
                listing.is_watched = True
                db.session.commit()
                logger.info(f"Marked listing {listing_id} as watched")
                return True
        except Exception as e:
            logger.error(f"Error marking listing as watched: {str(e)}")
            db.session.rollback()
        return False
    
    def unwatch_listing(self, listing_id: int):
        """Remove listing from watch list"""
        try:
            listing = Listing.query.get(listing_id)
            if listing:
                listing.is_watched = False
                db.session.commit()
                logger.info(f"Removed listing {listing_id} from watch list")
                return True
        except Exception as e:
            logger.error(f"Error removing listing from watch list: {str(e)}")
            db.session.rollback()
        return False
