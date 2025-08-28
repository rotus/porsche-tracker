import logging
from datetime import datetime, timedelta
from typing import List, Dict
from app import db
from app.models import Listing, PriceHistory
from app.scrapers import CarGurusScraper
from app.monitoring.notification_service import NotificationService
import statistics

logger = logging.getLogger(__name__)

class PriceTracker:
    """Track price changes for watched listings"""
    
    def __init__(self, config):
        self.config = config
        self.scraper = CarGurusScraper(config)
        self.notification_service = NotificationService(config)
    
    def track_watched_listings(self):
        """Track price changes for all watched listings"""
        logger.info("Starting price tracking cycle...")
        
        try:
            # Get all watched listings
            watched_listings = Listing.query.filter_by(is_watched=True, is_active=True).all()
            logger.info(f"Found {len(watched_listings)} watched listings")
            
            updates_count = 0
            price_changes_count = 0
            
            for listing in watched_listings:
                try:
                    updated, price_changed = self._check_listing_for_updates(listing)
                    if updated:
                        updates_count += 1
                    if price_changed:
                        price_changes_count += 1
                        
                except Exception as e:
                    logger.error(f"Error checking listing {listing.id}: {str(e)}")
            
            logger.info(f"Price tracking completed: {updates_count} listings updated, {price_changes_count} price changes detected")
            
        except Exception as e:
            logger.error(f"Error in price tracking cycle: {str(e)}")
    
    def _check_listing_for_updates(self, listing: Listing) -> tuple:
        """Check a single listing for updates and price changes"""
        try:
            if not listing.url:
                logger.warning(f"No URL available for listing {listing.id}")
                return False, False
            
            # Get current data from CarGurus
            current_data = self.scraper.get_detailed_listing(listing.url)
            
            # Check if listing is still active
            if not current_data:
                logger.info(f"Listing {listing.id} appears to be inactive")
                listing.is_active = False
                db.session.commit()
                return True, False
            
            # Extract current price from the scraped data
            # This would need to be implemented based on CarGurus' detailed page structure
            current_price = self._extract_current_price(current_data)
            
            if not current_price:
                logger.warning(f"Could not extract current price for listing {listing.id}")
                return False, False
            
            # Check for price change
            price_changed = False
            if current_price != listing.price:
                old_price = listing.price
                
                # Record price change
                price_record = PriceHistory.create_price_record(listing, old_price)
                db.session.add(price_record)
                
                # Update listing
                listing.price = current_price
                listing.last_updated = datetime.utcnow()
                
                db.session.commit()
                
                logger.info(f"Price change detected for listing {listing.id}: ${old_price} -> ${current_price}")
                
                # Send notification
                self._send_price_change_notification(listing, old_price, current_price)
                
                price_changed = True
            
            return True, price_changed
            
        except Exception as e:
            logger.error(f"Error checking listing {listing.id} for updates: {str(e)}")
            db.session.rollback()
            return False, False
    
    def _extract_current_price(self, scraped_data: Dict) -> int:
        """Extract current price from scraped data"""
        # This is a placeholder - would need to be implemented based on 
        # the actual structure returned by the scraper
        return scraped_data.get('price')
    
    def _send_price_change_notification(self, listing: Listing, old_price: int, new_price: int):
        """Send price change notification"""
        try:
            # For watched listings, we need to find matching criteria for notification settings
            from app.models import WatchCriteria
            
            active_criteria = WatchCriteria.query.filter_by(is_active=True).all()
            
            for criteria in active_criteria:
                if criteria.matches_listing(listing):
                    self.notification_service.send_price_change_alert(listing, old_price, new_price, criteria)
                    break
                    
        except Exception as e:
            logger.error(f"Error sending price change notification for listing {listing.id}: {str(e)}")
    
    def get_price_history_analytics(self, listing_id: int) -> Dict:
        """Get price history analytics for a listing"""
        try:
            listing = Listing.query.get(listing_id)
            if not listing:
                return {}
            
            price_history = PriceHistory.query.filter_by(listing_id=listing_id).order_by(PriceHistory.recorded_at).all()
            
            if not price_history:
                return {'error': 'No price history available'}
            
            # Calculate analytics
            prices = [ph.price for ph in price_history]
            price_changes = [ph.price_change for ph in price_history if ph.price_change is not None]
            
            analytics = {
                'current_price': listing.price,
                'original_price': prices[0] if prices else None,
                'lowest_price': min(prices) if prices else None,
                'highest_price': max(prices) if prices else None,
                'price_changes_count': len(price_changes),
                'total_price_change': sum(price_changes) if price_changes else 0,
                'average_price': statistics.mean(prices) if prices else None,
                'days_tracked': (datetime.utcnow() - listing.first_seen).days if listing.first_seen else 0,
                'price_volatility': statistics.stdev(prices) if len(prices) > 1 else 0,
                'trend': self._calculate_price_trend(price_history)
            }
            
            # Calculate if it's a good time to buy (price trend analysis)
            analytics['recommendation'] = self._get_buying_recommendation(analytics, price_history)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating price analytics for listing {listing_id}: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_price_trend(self, price_history: List[PriceHistory]) -> str:
        """Calculate overall price trend"""
        if len(price_history) < 2:
            return 'stable'
        
        prices = [ph.price for ph in price_history]
        recent_prices = prices[-5:]  # Last 5 price points
        
        if len(recent_prices) < 2:
            return 'stable'
        
        # Calculate trend using simple linear approximation
        trend_sum = 0
        for i in range(1, len(recent_prices)):
            if recent_prices[i] > recent_prices[i-1]:
                trend_sum += 1
            elif recent_prices[i] < recent_prices[i-1]:
                trend_sum -= 1
        
        if trend_sum > 0:
            return 'increasing'
        elif trend_sum < 0:
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_buying_recommendation(self, analytics: Dict, price_history: List[PriceHistory]) -> Dict:
        """Generate buying recommendation based on price analytics"""
        try:
            recommendation = {
                'action': 'hold',
                'confidence': 'low',
                'reason': 'Insufficient data',
                'score': 50  # 0-100 scale
            }
            
            if analytics['days_tracked'] < 7:
                return recommendation
            
            current_price = analytics['current_price']
            lowest_price = analytics['lowest_price']
            highest_price = analytics['highest_price']
            trend = analytics['trend']
            
            score = 50  # Start neutral
            
            # Factor 1: Current price vs historical range
            if lowest_price and highest_price:
                price_position = (current_price - lowest_price) / (highest_price - lowest_price)
                if price_position < 0.3:  # In bottom 30% of price range
                    score += 25
                elif price_position > 0.7:  # In top 30% of price range
                    score -= 25
            
            # Factor 2: Recent trend
            if trend == 'decreasing':
                score += 15
                reason = "Price is trending downward"
            elif trend == 'increasing':
                score -= 15
                reason = "Price is trending upward"
            else:
                reason = "Price has been stable"
            
            # Factor 3: Time on market
            days_tracked = analytics['days_tracked']
            if days_tracked > 60:  # Long time on market
                score += 10
                reason += " and listing has been on market for a while"
            elif days_tracked < 14:  # New listing
                score -= 5
                reason += " but listing is relatively new"
            
            # Factor 4: Price volatility
            volatility = analytics.get('price_volatility', 0)
            if volatility > 5000:  # High volatility
                score -= 10
                reason += " with high price volatility"
            
            # Determine recommendation
            if score >= 70:
                recommendation.update({
                    'action': 'buy',
                    'confidence': 'high' if score >= 80 else 'medium',
                    'reason': f"Good buying opportunity: {reason}",
                    'score': score
                })
            elif score <= 30:
                recommendation.update({
                    'action': 'wait',
                    'confidence': 'high' if score <= 20 else 'medium',
                    'reason': f"Consider waiting: {reason}",
                    'score': score
                })
            else:
                recommendation.update({
                    'action': 'hold',
                    'confidence': 'medium',
                    'reason': f"Neutral position: {reason}",
                    'score': score
                })
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating buying recommendation: {str(e)}")
            return {
                'action': 'hold',
                'confidence': 'low',
                'reason': f'Error calculating recommendation: {str(e)}',
                'score': 50
            }
    
    def get_market_analysis(self, model: str = None, year_range: tuple = None) -> Dict:
        """Get market analysis for Porsche listings"""
        try:
            query = Listing.query.filter_by(is_active=True, make='Porsche')
            
            if model:
                query = query.filter_by(model=model)
            
            if year_range:
                query = query.filter(Listing.year >= year_range[0], Listing.year <= year_range[1])
            
            listings = query.all()
            
            if not listings:
                return {'error': 'No listings found for analysis'}
            
            prices = [listing.price for listing in listings if listing.price]
            mileages = [listing.mileage for listing in listings if listing.mileage]
            
            analysis = {
                'total_listings': len(listings),
                'price_analysis': {
                    'average_price': int(statistics.mean(prices)) if prices else None,
                    'median_price': int(statistics.median(prices)) if prices else None,
                    'min_price': min(prices) if prices else None,
                    'max_price': max(prices) if prices else None,
                    'price_std_dev': int(statistics.stdev(prices)) if len(prices) > 1 else 0
                },
                'mileage_analysis': {
                    'average_mileage': int(statistics.mean(mileages)) if mileages else None,
                    'median_mileage': int(statistics.median(mileages)) if mileages else None,
                    'min_mileage': min(mileages) if mileages else None,
                    'max_mileage': max(mileages) if mileages else None
                },
                'model_breakdown': self._get_model_breakdown(listings),
                'year_breakdown': self._get_year_breakdown(listings),
                'condition_breakdown': self._get_condition_breakdown(listings),
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating market analysis: {str(e)}")
            return {'error': str(e)}
    
    def _get_model_breakdown(self, listings: List[Listing]) -> Dict:
        """Get breakdown by model"""
        model_counts = {}
        for listing in listings:
            if listing.model:
                model_counts[listing.model] = model_counts.get(listing.model, 0) + 1
        return model_counts
    
    def _get_year_breakdown(self, listings: List[Listing]) -> Dict:
        """Get breakdown by year"""
        year_counts = {}
        for listing in listings:
            if listing.year:
                year_counts[str(listing.year)] = year_counts.get(str(listing.year), 0) + 1
        return year_counts
    
    def _get_condition_breakdown(self, listings: List[Listing]) -> Dict:
        """Get breakdown by condition"""
        condition_counts = {}
        for listing in listings:
            if listing.condition:
                condition_counts[listing.condition] = condition_counts.get(listing.condition, 0) + 1
        return condition_counts
