from datetime import datetime
from app import db

class Listing(db.Model):
    """Car listing model"""
    __tablename__ = 'listings'
    
    id = db.Column(db.Integer, primary_key=True)
    cargurus_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Basic car information
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    trim = db.Column(db.String(100))
    
    # Pricing and condition
    price = db.Column(db.Integer, nullable=False)  # Price in dollars
    mileage = db.Column(db.Integer)
    condition = db.Column(db.String(50))  # New, Used, CPO
    
    # Vehicle details
    exterior_color = db.Column(db.String(50))
    interior_color = db.Column(db.String(50))
    vin = db.Column(db.String(17), index=True)
    transmission = db.Column(db.String(50))
    drivetrain = db.Column(db.String(50))
    fuel_type = db.Column(db.String(30))
    
    # Location information
    dealer_name = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zip_code = db.Column(db.String(10))
    distance_from_user = db.Column(db.Float)  # Miles
    
    # Listing metadata
    url = db.Column(db.String(500), nullable=False)
    image_urls = db.Column(db.Text)  # JSON array of image URLs
    description = db.Column(db.Text)
    
    # Tracking information
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_watched = db.Column(db.Boolean, default=False)
    
    # Relationships
    price_history = db.relationship('PriceHistory', backref='listing', lazy=True, cascade='all, delete-orphan')
    vin_data = db.relationship('VinData', backref='listing', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Listing {self.year} {self.make} {self.model} - ${self.price}>'
    
    def to_dict(self):
        """Convert listing to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'cargurus_id': self.cargurus_id,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'trim': self.trim,
            'price': self.price,
            'mileage': self.mileage,
            'condition': self.condition,
            'exterior_color': self.exterior_color,
            'interior_color': self.interior_color,
            'vin': self.vin,
            'transmission': self.transmission,
            'drivetrain': self.drivetrain,
            'fuel_type': self.fuel_type,
            'dealer_name': self.dealer_name,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'distance_from_user': self.distance_from_user,
            'url': self.url,
            'description': self.description,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active,
            'is_watched': self.is_watched,
            'current_price': self.price,
            'price_changes': len(self.price_history) if self.price_history else 0
        }
    
    def get_price_change_percentage(self):
        """Calculate price change from first recorded price"""
        if not self.price_history:
            return 0
        
        first_price = min(ph.price for ph in self.price_history)
        if first_price == 0:
            return 0
        
        return ((self.price - first_price) / first_price) * 100
