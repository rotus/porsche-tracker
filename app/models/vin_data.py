from datetime import datetime
from app import db

class VinData(db.Model):
    """Enriched VIN data from third-party APIs"""
    __tablename__ = 'vin_data'
    
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False, unique=True, index=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    
    # Vehicle specifications from VIN decode
    engine = db.Column(db.String(200))
    engine_size = db.Column(db.String(50))
    engine_cylinders = db.Column(db.Integer)
    horsepower = db.Column(db.Integer)
    torque = db.Column(db.String(50))
    
    # Build information
    plant_country = db.Column(db.String(50))
    plant_city = db.Column(db.String(100))
    plant_company_name = db.Column(db.String(100))
    
    # Options and features
    optional_equipment = db.Column(db.Text)  # JSON array of options
    standard_equipment = db.Column(db.Text)  # JSON array of standard features
    
    # Market data
    msrp = db.Column(db.Integer)  # Original MSRP
    market_value_estimate = db.Column(db.Integer)  # Current estimated market value
    market_value_source = db.Column(db.String(50))
    depreciation_rate = db.Column(db.Float)  # Annual depreciation percentage
    
    # History data
    accident_history = db.Column(db.Boolean)
    service_records_count = db.Column(db.Integer)
    previous_owners_count = db.Column(db.Integer)
    title_issues = db.Column(db.Text)  # JSON array of title issues
    
    # Recall information
    recall_count = db.Column(db.Integer, default=0)
    open_recalls = db.Column(db.Text)  # JSON array of open recalls
    completed_recalls = db.Column(db.Text)  # JSON array of completed recalls
    
    # API metadata
    data_source = db.Column(db.String(50))  # API source (e.g., 'vehicle_database', 'autocheck')
    api_response_raw = db.Column(db.Text)  # Raw API response for debugging
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Quality scores
    data_quality_score = db.Column(db.Float)  # 0-1 score based on completeness
    confidence_score = db.Column(db.Float)  # 0-1 confidence in the data
    
    def __repr__(self):
        return f'<VinData {self.vin} for Listing:{self.listing_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        import json
        
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'vin': self.vin,
            'engine': self.engine,
            'engine_size': self.engine_size,
            'engine_cylinders': self.engine_cylinders,
            'horsepower': self.horsepower,
            'torque': self.torque,
            'plant_country': self.plant_country,
            'plant_city': self.plant_city,
            'plant_company_name': self.plant_company_name,
            'optional_equipment': json.loads(self.optional_equipment) if self.optional_equipment else [],
            'standard_equipment': json.loads(self.standard_equipment) if self.standard_equipment else [],
            'msrp': self.msrp,
            'market_value_estimate': self.market_value_estimate,
            'market_value_source': self.market_value_source,
            'depreciation_rate': self.depreciation_rate,
            'accident_history': self.accident_history,
            'service_records_count': self.service_records_count,
            'previous_owners_count': self.previous_owners_count,
            'title_issues': json.loads(self.title_issues) if self.title_issues else [],
            'recall_count': self.recall_count,
            'open_recalls': json.loads(self.open_recalls) if self.open_recalls else [],
            'completed_recalls': json.loads(self.completed_recalls) if self.completed_recalls else [],
            'data_source': self.data_source,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'data_quality_score': self.data_quality_score,
            'confidence_score': self.confidence_score
        }
    
    def calculate_value_analysis(self, listing_price):
        """Analyze if the listing is a good value based on VIN data"""
        if not self.market_value_estimate:
            return None
        
        value_difference = listing_price - self.market_value_estimate
        value_percentage = (value_difference / self.market_value_estimate) * 100
        
        analysis = {
            'market_value': self.market_value_estimate,
            'listing_price': listing_price,
            'value_difference': value_difference,
            'value_percentage': value_percentage,
            'is_good_deal': value_difference < 0,
            'deal_quality': self._get_deal_quality(value_percentage)
        }
        
        return analysis
    
    def _get_deal_quality(self, value_percentage):
        """Determine deal quality based on percentage difference"""
        if value_percentage <= -15:
            return 'excellent'
        elif value_percentage <= -10:
            return 'very_good'
        elif value_percentage <= -5:
            return 'good'
        elif value_percentage <= 5:
            return 'fair'
        elif value_percentage <= 15:
            return 'poor'
        else:
            return 'overpriced'
