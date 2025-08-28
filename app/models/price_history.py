from datetime import datetime
from app import db

class PriceHistory(db.Model):
    """Track price changes for listings"""
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False, index=True)
    
    # Price information
    price = db.Column(db.Integer, nullable=False)  # Price in dollars
    price_change = db.Column(db.Integer)  # Change from previous price
    price_change_percentage = db.Column(db.Float)  # Percentage change
    
    # Metadata
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    source = db.Column(db.String(50), default='cargurus')  # Source of the price update
    
    # Additional context
    mileage = db.Column(db.Integer)  # Mileage at time of price record
    days_on_market = db.Column(db.Integer)  # Days since first seen
    
    def __repr__(self):
        return f'<PriceHistory Listing:{self.listing_id} ${self.price} on {self.recorded_at}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'price': self.price,
            'price_change': self.price_change,
            'price_change_percentage': self.price_change_percentage,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'source': self.source,
            'mileage': self.mileage,
            'days_on_market': self.days_on_market
        }
    
    @staticmethod
    def create_price_record(listing, previous_price=None):
        """Create a new price history record for a listing"""
        price_change = None
        price_change_percentage = None
        
        if previous_price is not None:
            price_change = listing.price - previous_price
            if previous_price > 0:
                price_change_percentage = (price_change / previous_price) * 100
        
        # Calculate days on market
        days_on_market = None
        if listing.first_seen:
            days_on_market = (datetime.utcnow() - listing.first_seen).days
        
        return PriceHistory(
            listing_id=listing.id,
            price=listing.price,
            price_change=price_change,
            price_change_percentage=price_change_percentage,
            mileage=listing.mileage,
            days_on_market=days_on_market
        )
