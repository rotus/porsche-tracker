from datetime import datetime
from app import db

class WatchCriteria(db.Model):
    """User-defined criteria for monitoring new listings"""
    __tablename__ = 'watch_criteria'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # User-friendly name for this criteria
    
    # Car criteria
    make = db.Column(db.String(50), default='Porsche')
    models = db.Column(db.Text)  # JSON array of models to watch
    min_year = db.Column(db.Integer)
    max_year = db.Column(db.Integer)
    
    # Price criteria
    min_price = db.Column(db.Integer)
    max_price = db.Column(db.Integer)
    
    # Condition criteria
    conditions = db.Column(db.Text)  # JSON array: ['New', 'Used', 'CPO']
    
    # Mileage criteria
    max_mileage = db.Column(db.Integer)
    
    # Location criteria
    max_distance = db.Column(db.Float)  # Miles from user location
    user_zip_code = db.Column(db.String(10))
    
    # Color criteria
    exterior_colors = db.Column(db.Text)  # JSON array of preferred colors
    interior_colors = db.Column(db.Text)  # JSON array of preferred colors
    
    # Transmission/drivetrain preferences
    transmissions = db.Column(db.Text)  # JSON array
    drivetrains = db.Column(db.Text)  # JSON array
    
    # Notification settings
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    notification_email = db.Column(db.String(255))
    notification_phone = db.Column(db.String(20))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<WatchCriteria {self.name}>'
    
    def to_dict(self):
        """Convert criteria to dictionary"""
        import json
        
        return {
            'id': self.id,
            'name': self.name,
            'make': self.make,
            'models': json.loads(self.models) if self.models else [],
            'min_year': self.min_year,
            'max_year': self.max_year,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'conditions': json.loads(self.conditions) if self.conditions else [],
            'max_mileage': self.max_mileage,
            'max_distance': self.max_distance,
            'user_zip_code': self.user_zip_code,
            'exterior_colors': json.loads(self.exterior_colors) if self.exterior_colors else [],
            'interior_colors': json.loads(self.interior_colors) if self.interior_colors else [],
            'transmissions': json.loads(self.transmissions) if self.transmissions else [],
            'drivetrains': json.loads(self.drivetrains) if self.drivetrains else [],
            'email_notifications': self.email_notifications,
            'sms_notifications': self.sms_notifications,
            'notification_email': self.notification_email,
            'notification_phone': self.notification_phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None
        }
    
    def matches_listing(self, listing):
        """Check if a listing matches this criteria"""
        import json
        
        # Check make
        if self.make and listing.make.lower() != self.make.lower():
            return False
        
        # Check models
        if self.models:
            models_list = json.loads(self.models)
            if listing.model not in models_list:
                return False
        
        # Check year range
        if self.min_year and listing.year < self.min_year:
            return False
        if self.max_year and listing.year > self.max_year:
            return False
        
        # Check price range
        if self.min_price and listing.price < self.min_price:
            return False
        if self.max_price and listing.price > self.max_price:
            return False
        
        # Check mileage
        if self.max_mileage and listing.mileage and listing.mileage > self.max_mileage:
            return False
        
        # Check distance
        if self.max_distance and listing.distance_from_user and listing.distance_from_user > self.max_distance:
            return False
        
        # Check condition
        if self.conditions:
            conditions_list = json.loads(self.conditions)
            if listing.condition not in conditions_list:
                return False
        
        # Check exterior color
        if self.exterior_colors:
            colors_list = json.loads(self.exterior_colors)
            if listing.exterior_color and listing.exterior_color not in colors_list:
                return False
        
        # Check interior color
        if self.interior_colors:
            colors_list = json.loads(self.interior_colors)
            if listing.interior_color and listing.interior_color not in colors_list:
                return False
        
        # Check transmission
        if self.transmissions:
            transmissions_list = json.loads(self.transmissions)
            if listing.transmission and listing.transmission not in transmissions_list:
                return False
        
        # Check drivetrain
        if self.drivetrains:
            drivetrains_list = json.loads(self.drivetrains)
            if listing.drivetrain and listing.drivetrain not in drivetrains_list:
                return False
        
        return True
