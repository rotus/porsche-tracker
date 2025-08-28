#!/usr/bin/env python3
"""
Simple SQLite database module for Porsche Tracker
Uses built-in sqlite3 module instead of SQLAlchemy for better Python 3.13 compatibility
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SimpleDB:
    def __init__(self, db_path="porsche_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = self.get_connection()
        try:
            # Create listings table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cargurus_id TEXT UNIQUE NOT NULL,
                    make TEXT NOT NULL DEFAULT 'Porsche',
                    model TEXT,
                    year INTEGER,
                    trim TEXT,
                    price INTEGER NOT NULL,
                    mileage INTEGER,
                    condition TEXT DEFAULT 'Used',
                    exterior_color TEXT,
                    interior_color TEXT,
                    vin TEXT,
                    transmission TEXT,
                    drivetrain TEXT,
                    fuel_type TEXT,
                    dealer_name TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    distance_from_user REAL,
                    url TEXT NOT NULL,
                    image_urls TEXT,
                    description TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_watched BOOLEAN DEFAULT 0
                )
            ''')
            
            # Create watch criteria table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS watch_criteria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    make TEXT DEFAULT 'Porsche',
                    models TEXT,  -- JSON array
                    min_year INTEGER,
                    max_year INTEGER,
                    min_price INTEGER,
                    max_price INTEGER,
                    conditions TEXT,  -- JSON array
                    max_mileage INTEGER,
                    max_distance REAL,
                    user_zip_code TEXT,
                    exterior_colors TEXT,  -- JSON array
                    interior_colors TEXT,  -- JSON array
                    transmissions TEXT,  -- JSON array
                    drivetrains TEXT,  -- JSON array
                    email_notifications BOOLEAN DEFAULT 1,
                    sms_notifications BOOLEAN DEFAULT 0,
                    notification_email TEXT,
                    notification_phone TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_checked DATETIME
                )
            ''')
            
            # Create price history table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    price_change INTEGER,
                    price_change_percentage REAL,
                    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'cargurus',
                    mileage INTEGER,
                    days_on_market INTEGER,
                    FOREIGN KEY (listing_id) REFERENCES listings (id)
                )
            ''')
            
            # Create VIN data table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS vin_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_id INTEGER NOT NULL UNIQUE,
                    vin TEXT NOT NULL,
                    engine TEXT,
                    engine_size TEXT,
                    engine_cylinders INTEGER,
                    horsepower INTEGER,
                    torque TEXT,
                    plant_country TEXT,
                    plant_city TEXT,
                    plant_company_name TEXT,
                    optional_equipment TEXT,  -- JSON array
                    standard_equipment TEXT,  -- JSON array
                    msrp INTEGER,
                    market_value_estimate INTEGER,
                    market_value_source TEXT,
                    depreciation_rate REAL,
                    accident_history BOOLEAN,
                    service_records_count INTEGER,
                    previous_owners_count INTEGER,
                    title_issues TEXT,  -- JSON array
                    recall_count INTEGER DEFAULT 0,
                    open_recalls TEXT,  -- JSON array
                    completed_recalls TEXT,  -- JSON array
                    data_source TEXT,
                    api_response_raw TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_quality_score REAL,
                    confidence_score REAL,
                    FOREIGN KEY (listing_id) REFERENCES listings (id)
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_listings_cargurus_id ON listings(cargurus_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_listings_active ON listings(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_listings_watched ON listings(is_watched)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_listing ON price_history(listing_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_watch_criteria_active ON watch_criteria(is_active)')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def add_sample_data(self):
        """Add sample watch criteria for testing"""
        conn = self.get_connection()
        try:
            # Check if we already have data
            cursor = conn.execute('SELECT COUNT(*) FROM watch_criteria')
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info("Sample data already exists")
                return
            
            # Add sample watch criteria
            sample_criteria = [
                {
                    'name': 'Dream 911',
                    'models': json.dumps(['911']),
                    'min_year': 2018,
                    'max_year': 2024,
                    'max_price': 200000,
                    'max_mileage': 50000,
                    'max_distance': 100.0,
                    'user_zip_code': '90210',
                    'exterior_colors': json.dumps(['Guards Red', 'GT Silver Metallic', 'Black']),
                    'conditions': json.dumps(['Used', 'CPO']),
                    'email_notifications': True,
                    'notification_email': 'user@example.com'
                },
                {
                    'name': 'Cayenne Family Car',
                    'models': json.dumps(['Cayenne']),
                    'min_year': 2019,
                    'max_year': 2024,
                    'max_price': 80000,
                    'max_mileage': 40000,
                    'max_distance': 50.0,
                    'user_zip_code': '90210',
                    'conditions': json.dumps(['Used', 'CPO', 'New']),
                    'email_notifications': True,
                    'notification_email': 'user@example.com'
                }
            ]
            
            for criteria in sample_criteria:
                conn.execute('''
                    INSERT INTO watch_criteria 
                    (name, models, min_year, max_year, max_price, max_mileage, max_distance, 
                     user_zip_code, exterior_colors, conditions, email_notifications, notification_email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    criteria['name'], criteria['models'], criteria['min_year'], criteria['max_year'],
                    criteria['max_price'], criteria['max_mileage'], criteria['max_distance'],
                    criteria['user_zip_code'], criteria.get('exterior_colors'), criteria['conditions'],
                    criteria['email_notifications'], criteria['notification_email']
                ))
            
            conn.commit()
            logger.info("Sample data added successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Error adding sample data: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # Listing methods
    def add_listing(self, listing_data: Dict) -> Optional[int]:
        """Add a new listing"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                INSERT INTO listings 
                (cargurus_id, make, model, year, trim, price, mileage, condition, 
                 exterior_color, interior_color, vin, transmission, drivetrain, fuel_type,
                 dealer_name, city, state, zip_code, distance_from_user, url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                listing_data.get('cargurus_id'),
                listing_data.get('make', 'Porsche'),
                listing_data.get('model'),
                listing_data.get('year'),
                listing_data.get('trim'),
                listing_data.get('price'),
                listing_data.get('mileage'),
                listing_data.get('condition', 'Used'),
                listing_data.get('exterior_color'),
                listing_data.get('interior_color'),
                listing_data.get('vin'),
                listing_data.get('transmission'),
                listing_data.get('drivetrain'),
                listing_data.get('fuel_type'),
                listing_data.get('dealer_name'),
                listing_data.get('city'),
                listing_data.get('state'),
                listing_data.get('zip_code'),
                listing_data.get('distance_from_user'),
                listing_data.get('url'),
                listing_data.get('description')
            ))
            
            listing_id = cursor.lastrowid
            conn.commit()
            
            # Add initial price history record
            self.add_price_history(listing_id, listing_data.get('price'))
            
            logger.info(f"Added new listing: {listing_id}")
            return listing_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"Listing already exists: {listing_data.get('cargurus_id')}")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error adding listing: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_listing_by_cargurus_id(self, cargurus_id: str) -> Optional[Dict]:
        """Get listing by CarGurus ID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM listings WHERE cargurus_id = ?', (cargurus_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_listing_by_id(self, listing_id: int) -> Optional[Dict]:
        """Get listing by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM listings WHERE id = ?', (listing_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_active_listings(self, limit: int = 100) -> List[Dict]:
        """Get active listings"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM listings 
                WHERE is_active = 1 
                ORDER BY first_seen DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_watched_listings(self) -> List[Dict]:
        """Get watched listings"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM listings 
                WHERE is_watched = 1 AND is_active = 1 
                ORDER BY last_updated DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def update_listing_price(self, listing_id: int, new_price: int) -> bool:
        """Update listing price and add to price history"""
        conn = self.get_connection()
        try:
            # Get current price
            cursor = conn.execute('SELECT price FROM listings WHERE id = ?', (listing_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            old_price = row[0]
            
            # Update listing
            conn.execute('''
                UPDATE listings 
                SET price = ?, last_updated = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_price, listing_id))
            
            # Add price history
            price_change = new_price - old_price
            price_change_pct = (price_change / old_price * 100) if old_price > 0 else 0
            
            conn.execute('''
                INSERT INTO price_history 
                (listing_id, price, price_change, price_change_percentage)
                VALUES (?, ?, ?, ?)
            ''', (listing_id, new_price, price_change, price_change_pct))
            
            conn.commit()
            logger.info(f"Updated listing {listing_id} price: ${old_price} -> ${new_price}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating listing price: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def watch_listing(self, listing_id: int) -> bool:
        """Add listing to watch list"""
        return self._update_watch_status(listing_id, True)
    
    def unwatch_listing(self, listing_id: int) -> bool:
        """Remove listing from watch list"""
        return self._update_watch_status(listing_id, False)
    
    def _update_watch_status(self, listing_id: int, watched: bool) -> bool:
        """Update watch status for a listing"""
        conn = self.get_connection()
        try:
            conn.execute('''
                UPDATE listings 
                SET is_watched = ?, last_updated = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (watched, listing_id))
            
            conn.commit()
            action = "watched" if watched else "unwatched"
            logger.info(f"Listing {listing_id} {action}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating watch status: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # Watch criteria methods
    def get_active_watch_criteria(self) -> List[Dict]:
        """Get active watch criteria"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM watch_criteria 
                WHERE is_active = 1 
                ORDER BY created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def add_watch_criteria(self, criteria_data: Dict) -> Optional[int]:
        """Add new watch criteria"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                INSERT INTO watch_criteria 
                (name, models, min_year, max_year, min_price, max_price, max_mileage, 
                 max_distance, user_zip_code, exterior_colors, conditions, 
                 email_notifications, notification_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                criteria_data.get('name'),
                criteria_data.get('models'),
                criteria_data.get('min_year'),
                criteria_data.get('max_year'),
                criteria_data.get('min_price'),
                criteria_data.get('max_price'),
                criteria_data.get('max_mileage'),
                criteria_data.get('max_distance'),
                criteria_data.get('user_zip_code'),
                criteria_data.get('exterior_colors'),
                criteria_data.get('conditions'),
                criteria_data.get('email_notifications', True),
                criteria_data.get('notification_email')
            ))
            
            criteria_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added new watch criteria: {criteria_id}")
            return criteria_id
            
        except sqlite3.Error as e:
            logger.error(f"Error adding watch criteria: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    # Price history methods
    def add_price_history(self, listing_id: int, price: int, price_change: int = None) -> bool:
        """Add price history record"""
        conn = self.get_connection()
        try:
            conn.execute('''
                INSERT INTO price_history (listing_id, price, price_change)
                VALUES (?, ?, ?)
            ''', (listing_id, price, price_change))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error adding price history: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_price_history(self, listing_id: int) -> List[Dict]:
        """Get price history for a listing"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM price_history 
                WHERE listing_id = ? 
                ORDER BY recorded_at DESC
            ''', (listing_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # Statistics methods
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        conn = self.get_connection()
        try:
            stats = {}
            
            # Total active listings
            cursor = conn.execute('SELECT COUNT(*) FROM listings WHERE is_active = 1')
            stats['total_listings'] = cursor.fetchone()[0]
            
            # Watched listings
            cursor = conn.execute('SELECT COUNT(*) FROM listings WHERE is_watched = 1 AND is_active = 1')
            stats['watched_listings'] = cursor.fetchone()[0]
            
            # Active criteria
            cursor = conn.execute('SELECT COUNT(*) FROM watch_criteria WHERE is_active = 1')
            stats['active_criteria'] = cursor.fetchone()[0]
            
            # Recent price changes
            cursor = conn.execute('''
                SELECT COUNT(*) FROM price_history 
                WHERE recorded_at > datetime('now', '-7 days')
                AND price_change IS NOT NULL
            ''')
            stats['recent_price_changes'] = cursor.fetchone()[0]
            
            return stats
            
        finally:
            conn.close()
    
    def search_listings(self, filters: Dict) -> List[Dict]:
        """Search listings with filters"""
        conn = self.get_connection()
        try:
            where_clauses = ['is_active = 1']
            params = []
            
            if filters.get('model'):
                where_clauses.append('model = ?')
                params.append(filters['model'])
            
            if filters.get('min_year'):
                where_clauses.append('year >= ?')
                params.append(filters['min_year'])
            
            if filters.get('max_year'):
                where_clauses.append('year <= ?')
                params.append(filters['max_year'])
            
            if filters.get('min_price'):
                where_clauses.append('price >= ?')
                params.append(filters['min_price'])
            
            if filters.get('max_price'):
                where_clauses.append('price <= ?')
                params.append(filters['max_price'])
            
            if filters.get('max_mileage'):
                where_clauses.append('mileage <= ?')
                params.append(filters['max_mileage'])
            
            where_sql = ' AND '.join(where_clauses)
            order_by = 'first_seen DESC'
            
            if filters.get('sort') == 'price_low':
                order_by = 'price ASC'
            elif filters.get('sort') == 'price_high':
                order_by = 'price DESC'
            elif filters.get('sort') == 'mileage':
                order_by = 'mileage ASC'
            elif filters.get('sort') == 'year':
                order_by = 'year DESC'
            
            query = f'''
                SELECT * FROM listings 
                WHERE {where_sql} 
                ORDER BY {order_by}
                LIMIT 100
            '''
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def get_gt3rs_market_data(self, generation: str = None) -> Dict:
        """Get GT3 RS specific market analysis"""
        conn = self.get_connection()
        try:
            # Define generation year ranges
            generation_ranges = {
                '991.1': (2015, 2017),
                '991.2': (2018, 2019), 
                '992': (2022, 2024)
            }
            
            # Base query for GT3 RS listings
            where_clause = "model = '911' AND (trim LIKE '%GT3 RS%' OR trim LIKE '%GT3RS%') AND is_active = 1"
            params = []
            
            if generation and generation in generation_ranges:
                min_year, max_year = generation_ranges[generation]
                where_clause += " AND year >= ? AND year <= ?"
                params.extend([min_year, max_year])
            
            # Get current listings
            cursor = conn.execute(f'''
                SELECT year, price, mileage, trim, first_seen 
                FROM listings 
                WHERE {where_clause}
                ORDER BY year DESC
            ''', params)
            
            listings = [dict(row) for row in cursor.fetchall()]
            
            if not listings:
                return {'error': 'No GT3 RS listings found'}
            
            # Calculate market metrics
            prices = [listing['price'] for listing in listings if listing['price']]
            years = [listing['year'] for listing in listings if listing['year']]
            
            # Group by generation
            gen_data = {
                '991.1': [],
                '991.2': [],
                '992': []
            }
            
            for listing in listings:
                year = listing['year']
                if 2015 <= year <= 2017:
                    gen_data['991.1'].append(listing)
                elif 2018 <= year <= 2019:
                    gen_data['991.2'].append(listing)
                elif 2022 <= year <= 2024:
                    gen_data['992'].append(listing)
            
            # Calculate average prices by generation
            generation_prices = {}
            for gen, gen_listings in gen_data.items():
                if gen_listings:
                    gen_prices = [l['price'] for l in gen_listings if l['price']]
                    if gen_prices:
                        generation_prices[gen] = {
                            'avg_price': sum(gen_prices) // len(gen_prices),
                            'min_price': min(gen_prices),
                            'max_price': max(gen_prices),
                            'count': len(gen_listings),
                            'avg_mileage': sum(l['mileage'] for l in gen_listings if l['mileage']) // max(1, len([l for l in gen_listings if l['mileage']]))
                        }
            
            return {
                'total_listings': len(listings),
                'overall_avg_price': sum(prices) // len(prices) if prices else 0,
                'price_range': {'min': min(prices), 'max': max(prices)} if prices else {},
                'year_range': {'min': min(years), 'max': max(years)} if years else {},
                'generation_data': generation_prices,
                'market_premium': self._calculate_gt3rs_premium(),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting GT3 RS market data: {str(e)}")
            return {'error': str(e)}
        finally:
            conn.close()
    
    def _calculate_gt3rs_premium(self) -> float:
        """Calculate GT3 RS market premium vs MSRP"""
        # Estimated MSRP values for GT3 RS generations
        msrp_estimates = {
            '991.1': 175000,  # 2015-2017
            '991.2': 190000,  # 2018-2019
            '992': 240000     # 2022+
        }
        
        # This would use actual market data in a real implementation
        # For now, return estimated premium based on typical GT3 RS appreciation
        return 45.0  # 45% premium over MSRP average
    
    def add_gt3rs_sample_data(self):
        """Add sample GT3 RS listings for testing"""
        sample_listings = [
            {
                'cargurus_id': 'gt3rs_991_1_2016',
                'model': '911',
                'year': 2016,
                'trim': 'GT3 RS',
                'price': 285000,
                'mileage': 5200,
                'condition': 'Used',
                'exterior_color': 'Guards Red',
                'interior_color': 'Black Alcantara',
                'dealer_name': 'Porsche Beverly Hills',
                'city': 'Beverly Hills',
                'state': 'CA',
                'url': 'https://www.cargurus.com/sample/gt3rs-991-1'
            },
            {
                'cargurus_id': 'gt3rs_991_2_2019',
                'model': '911',
                'year': 2019,
                'trim': 'GT3 RS',
                'price': 320000,
                'mileage': 2800,
                'condition': 'Used',
                'exterior_color': 'Racing Yellow',
                'interior_color': 'Black/Yellow',
                'dealer_name': 'Porsche Manhattan',
                'city': 'New York',
                'state': 'NY',
                'url': 'https://www.cargurus.com/sample/gt3rs-991-2'
            },
            {
                'cargurus_id': 'gt3rs_992_2023',
                'model': '911',
                'year': 2023,
                'trim': 'GT3 RS',
                'price': 380000,
                'mileage': 450,
                'condition': 'Used',
                'exterior_color': 'Shark Blue',
                'interior_color': 'Black/Blue',
                'dealer_name': 'Porsche North Scottsdale',
                'city': 'Scottsdale',
                'state': 'AZ',
                'url': 'https://www.cargurus.com/sample/gt3rs-992'
            }
        ]
        
        for listing_data in sample_listings:
            existing = self.get_listing_by_cargurus_id(listing_data['cargurus_id'])
            if not existing:
                self.add_listing(listing_data)
                logger.info(f"Added sample GT3 RS: {listing_data['year']} {listing_data['trim']}")

# Global database instance
db = SimpleDB()
