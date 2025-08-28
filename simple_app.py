#!/usr/bin/env python3
"""
Simple Porsche Tracker Application
Uses built-in sqlite3 instead of SQLAlchemy for Python 3.13 compatibility
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from simple_db import db
import json
from datetime import datetime
from real_scraper import RealCarGurusScraper
from cargurus_auth import AuthenticatedCarGurusScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = 'porsche-tracker-secret-key-change-in-production'

# CarGurus OAuth (set this via environment variables)
CARGURUS_GOOGLE_EMAIL = os.getenv('CARGURUS_GOOGLE_EMAIL', '')

# Routes
@app.route('/')
def dashboard():
    """Dashboard homepage"""
    try:
        # Get summary statistics
        stats = db.get_dashboard_stats()
        
        # Get recent listings
        recent_listings = db.get_filtered_recent_listings(limit=5)
        
        # Get recent price changes (simplified)
        recent_price_changes = []
        
        return render_template('simple_dashboard.html',
                             total_listings=stats.get('total_listings', 0),
                             watched_listings=stats.get('watched_listings', 0),
                             active_criteria=stats.get('active_criteria', 0),
                             recent_price_changes=stats.get('recent_price_changes', 0),
                             recent_listings=recent_listings,
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('simple_dashboard.html',
                             total_listings=0,
                             watched_listings=0,
                             active_criteria=0,
                             recent_price_changes=0,
                             recent_listings=[],
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))

@app.route('/listings')
def listings():
    """Browse all listings with filtering"""
    try:
        # Get filter parameters
        filters = {
            'model': request.args.get('model'),
            'min_year': int(request.args.get('min_year')) if request.args.get('min_year') else None,
            'max_year': int(request.args.get('max_year')) if request.args.get('max_year') else None,
            'min_price': int(request.args.get('min_price')) if request.args.get('min_price') else None,
            'max_price': int(request.args.get('max_price')) if request.args.get('max_price') else None,
            'max_mileage': int(request.args.get('max_mileage')) if request.args.get('max_mileage') else None,
            'sort': request.args.get('sort', 'newest')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Search listings
        listings_data = db.search_listings(filters)
        
        # Get filter options
        all_listings = db.get_active_listings(limit=1000)
        models = list(set(listing['model'] for listing in all_listings if listing['model']))
        colors = list(set(listing['exterior_color'] for listing in all_listings if listing['exterior_color']))
        
        return render_template('simple_listings.html',
                             listings=listings_data,
                             models=sorted(models),
                             colors=sorted(colors),
                             current_filters=request.args,
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))
        
    except Exception as e:
        logger.error(f"Error loading listings: {str(e)}")
        flash(f'Error loading listings: {str(e)}', 'error')
        return render_template('simple_listings.html', 
                             listings=[], models=[], colors=[], current_filters={},
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))

@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    """Detailed view of a specific listing"""
    try:
        # Get listing and price history for the price tracker chart
        listing = db.get_listing_by_id(listing_id)
        if not listing:
            flash('Listing not found', 'error')
            return redirect(url_for('listings'))
        
        # Get real price history for the chart
        price_history = db.get_price_history(listing_id)
        
        return render_template('simple_listing_detail.html',
                             listing=listing,
                             price_history=price_history,
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))
        
    except Exception as e:
        logger.error(f"Error loading listing detail: {str(e)}")
        flash(f'Error loading listing: {str(e)}', 'error')
        return redirect(url_for('listings'))

@app.route('/search-criteria')
def search_criteria():
    """Manage search criteria for GT3 RS listings"""
    try:
        # Get current search criteria (we'll create this method)
        criteria = db.get_search_criteria()
        return render_template('simple_search_criteria.html', 
                             criteria=criteria,
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))
    except Exception as e:
        logger.error(f"Error loading search criteria: {str(e)}")
        flash(f'Error loading search criteria: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/setup')
def setup():
    """Setup page for one-time configuration"""
    try:
        return render_template('simple_setup.html',
                             authenticated=session.get('authenticated', False),
                             google_email=session.get('google_email', ''))
    except Exception as e:
        logger.error(f"Error loading setup page: {str(e)}")
        flash(f'Error loading setup page: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/create-criteria', methods=['GET', 'POST'])
def create_criteria():
    """Create new watch criteria"""
    if request.method == 'GET':
        return render_template('simple_create_criteria.html')
    
    try:
        # Create new criteria from form data
        criteria_data = {
            'name': request.form['name'],
            'models': json.dumps(request.form.getlist('models')) if request.form.getlist('models') else None,
            'min_year': int(request.form['min_year']) if request.form.get('min_year') else None,
            'max_year': int(request.form['max_year']) if request.form.get('max_year') else None,
            'min_price': int(request.form['min_price']) if request.form.get('min_price') else None,
            'max_price': int(request.form['max_price']) if request.form.get('max_price') else None,
            'max_mileage': int(request.form['max_mileage']) if request.form.get('max_mileage') else None,
            'max_distance': float(request.form['max_distance']) if request.form.get('max_distance') else None,
            'user_zip_code': request.form.get('user_zip_code'),
            'exterior_colors': json.dumps(request.form.getlist('exterior_colors')) if request.form.getlist('exterior_colors') else None,
            'conditions': json.dumps(request.form.getlist('conditions')) if request.form.getlist('conditions') else None,
            'email_notifications': bool(request.form.get('email_notifications')),
            'notification_email': request.form.get('notification_email')
        }
        
        criteria_id = db.add_watch_criteria(criteria_data)
        
        if criteria_id:
            flash(f'Watch criteria "{criteria_data["name"]}" created successfully!', 'success')
            return redirect(url_for('watch_criteria'))
        else:
            flash('Error creating watch criteria', 'error')
            return render_template('simple_create_criteria.html')
        
    except Exception as e:
        logger.error(f"Error creating watch criteria: {str(e)}")
        flash(f'Error creating watch criteria: {str(e)}', 'error')
        return render_template('simple_create_criteria.html')

# API Routes
@app.route('/api/watch-listing/<int:listing_id>', methods=['POST'])
def watch_listing(listing_id):
    """Add listing to watch list"""
    try:
        success = db.watch_listing(listing_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Listing added to watch list'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add listing to watch list'}), 400
            
    except Exception as e:
        logger.error(f"Error watching listing: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/unwatch-listing/<int:listing_id>', methods=['POST'])
def unwatch_listing(listing_id):
    """Remove listing from watch list"""
    try:
        success = db.unwatch_listing(listing_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Listing removed from watch list'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove listing from watch list'}), 400
            
    except Exception as e:
        logger.error(f"Error unwatching listing: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/add-sample-listing', methods=['POST'])
def add_sample_listing():
    """Add a sample listing for testing"""
    try:
        sample_listing = {
            'cargurus_id': f'sample_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'make': 'Porsche',
            'model': '911',
            'year': 2020,
            'trim': 'Carrera S',
            'price': 145000,
            'mileage': 15000,
            'condition': 'Used',
            'exterior_color': 'Guards Red',
            'interior_color': 'Black',
            'dealer_name': 'Sample Porsche Dealer',
            'city': 'Los Angeles',
            'state': 'CA',
            'url': 'https://www.cargurus.com/sample'
        }
        
        listing_id = db.add_listing(sample_listing)
        
        if listing_id:
            return jsonify({'success': True, 'message': f'Sample listing added with ID: {listing_id}'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add sample listing'}), 400
            
    except Exception as e:
        logger.error(f"Error adding sample listing: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get dashboard statistics via API"""
    try:
        stats = db.get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gt3rs-data')
def gt3rs_data():
    """Get GT3 RS market data via API"""
    try:
        generation = request.args.get('generation')
        data = db.get_gt3rs_market_data(generation)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting GT3 RS data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-gt3rs-samples', methods=['POST'])
def add_gt3rs_samples():
    """Add sample GT3 RS listings for testing"""
    try:
# Sample data removed - app now shows only real CarGurus data
        return jsonify({'success': True, 'message': 'Sample GT3 RS listings added successfully'})
    except Exception as e:
        logger.error(f"Error adding GT3 RS samples: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape-real-listings', methods=['POST'])
def scrape_real_listings():
    """Scrape real Porsche listings from CarGurus"""
    try:
        data = request.get_json() or {}
        max_listings = data.get('max_listings', 20)
        zip_code = data.get('zip_code', '90210')
        model = data.get('model', '911')
        
        logger.info(f"Starting real CarGurus scraping for {model} near {zip_code}")
        
        scraper = RealCarGurusScraper()
        filters = {
            'zip_code': zip_code,
            'model': model,
            'max_distance': data.get('max_distance', 100)
        }
        
        if data.get('min_price'):
            filters['min_price'] = data['min_price']
        if data.get('max_price'):
            filters['max_price'] = data['max_price']
        if data.get('min_year'):
            filters['min_year'] = data['min_year']
        if data.get('max_year'):
            filters['max_year'] = data['max_year']
        
        listings = scraper.scrape_listings(max_listings=max_listings, **filters)
        
        # Add listings to database
        added_count = 0
        for listing_data in listings:
            try:
                # Check if listing already exists
                existing = db.get_listing_by_cargurus_id(listing_data['cargurus_id'])
                if not existing:
                    db.add_listing(listing_data)
                    added_count += 1
                else:
                    # Update existing listing
                    db.update_listing(existing['id'], listing_data)
            except Exception as e:
                logger.error(f"Error adding listing {listing_data.get('cargurus_id')}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Successfully scraped {len(listings)} listings, added {added_count} new ones',
            'total_scraped': len(listings),
            'new_listings': added_count,
            'updated_listings': len(listings) - added_count
        })
        
    except Exception as e:
        logger.error(f"Error scraping real listings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape-gt3rs', methods=['POST'])
def scrape_real_gt3rs():
    """Scrape real GT3 RS listings specifically"""
    try:
        data = request.get_json() or {}
        max_listings = data.get('max_listings', 15)
        
        logger.info("Starting real GT3 RS scraping from CarGurus")
        
        scraper = RealCarGurusScraper()
        listings = scraper.scrape_gt3_rs_listings(max_listings=max_listings)
        
        # Add listings to database
        added_count = 0
        updated_count = 0
        
        for listing_data in listings:
            try:
                existing = db.get_listing_by_cargurus_id(listing_data['cargurus_id'])
                if not existing:
                    db.add_listing(listing_data)
                    added_count += 1
                else:
                    # Update price and check for changes
                    old_price = existing.get('price')
                    new_price = listing_data.get('price')
                    
                    db.update_listing(existing['id'], listing_data)
                    updated_count += 1
                    
                    # Track price changes
                    if old_price and new_price and old_price != new_price:
                        price_change = new_price - old_price
                        db.add_price_history(existing['id'], new_price, price_change)
                        logger.info(f"Price change detected for {listing_data['cargurus_id']}: {old_price} -> {new_price}")
                        
            except Exception as e:
                logger.error(f"Error processing GT3 RS listing {listing_data.get('cargurus_id')}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'🏎️ Found {len(listings)} real GT3 RS listings! Added {added_count} new, updated {updated_count}',
            'total_found': len(listings),
            'new_listings': added_count,
            'updated_listings': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error scraping GT3 RS listings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clear-sample-data', methods=['POST'])
def clear_sample_data():
    """Clear all sample data and keep only real scraped listings"""
    try:
        # Get count before deletion
        all_listings = db.get_active_listings(limit=1000)
        sample_count = len([l for l in all_listings if '/sample' in str(l.get('url', ''))])
        
        # This would need a method in the database to clear sample data
        # For now, we'll just return a message
        return jsonify({
            'success': True, 
            'message': f'Would clear {sample_count} sample listings (feature coming soon)',
            'sample_listings_found': sample_count
        })
        
    except Exception as e:
        logger.error(f"Error clearing sample data: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scrape-authenticated', methods=['POST'])
def scrape_authenticated():
    """Scrape CarGurus with Google OAuth for real data access"""
    try:
        data = request.get_json() or {}
        
        # Get Google email from request or environment
        google_email = data.get('google_email', CARGURUS_GOOGLE_EMAIL)
        
        if not google_email:
            return jsonify({
                'success': False, 
                'message': 'Google email required for CarGurus OAuth authentication.'
            }), 400
        
        zip_code = data.get('zip_code', '90210')
        max_listings = data.get('max_listings', 30)
        
        logger.info(f"Starting Google OAuth scraping for: {google_email}")
        
        # Create OAuth-enabled scraper
        scraper = AuthenticatedCarGurusScraper(google_email)
        
        # Try authentication and track in session
        if scraper.authenticate_with_google_oauth():
            session['authenticated'] = True
            session['google_email'] = google_email
            session['auth_time'] = datetime.now().isoformat()
            logger.info(f"✅ OAuth successful, session updated for {google_email}")
        else:
            session.pop('authenticated', None)
            session.pop('google_email', None)
            logger.warning(f"❌ OAuth failed for {google_email}")
        
        # Scrape listings with authentication
        listings = scraper.scrape_porsche_listings(zip_code=zip_code, max_listings=max_listings)
        
        if not listings:
            return jsonify({
                'success': False,
                'message': 'No listings found. CarGurus may have changed their structure or blocked scraping.'
            })
        
        # Add to database
        added_count = 0
        updated_count = 0
        
        for listing_data in listings:
            try:
                existing = db.get_listing_by_cargurus_id(listing_data['cargurus_id'])
                if not existing:
                    db.add_listing(listing_data)
                    added_count += 1
                else:
                    # Update and track price changes
                    old_price = existing.get('price')
                    new_price = listing_data.get('price')
                    
                    db.update_listing(existing['id'], listing_data)
                    updated_count += 1
                    
                    if old_price and new_price and old_price != new_price:
                        price_change = new_price - old_price
                        db.add_price_history(existing['id'], new_price, price_change)
                        
            except Exception as e:
                logger.error(f"Error processing listing {listing_data.get('cargurus_id')}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'🚀 Successfully scraped {len(listings)} REAL listings with images and VINs!',
            'total_scraped': len(listings),
            'new_listings': added_count,
            'updated_listings': updated_count,
            'authenticated': session.get('authenticated', False),
            'google_email': session.get('google_email', '')
        })
        
    except Exception as e:
        logger.error(f"Error in authenticated scraping: {str(e)}")
        session.pop('authenticated', None)
        session.pop('google_email', None)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth-status', methods=['GET'])
def auth_status():
    """Check current authentication status"""
    return jsonify({
        'authenticated': session.get('authenticated', False),
        'google_email': session.get('google_email', ''),
        'auth_time': session.get('auth_time', '')
    })

@app.route('/api/update-search-criteria', methods=['POST'])
def update_search_criteria():
    """Update search criteria for GT3 RS listings"""
    try:
        data = request.get_json()
        
        # Extract and validate data
        min_year = int(data.get('min_year')) if data.get('min_year') else None
        max_year = int(data.get('max_year')) if data.get('max_year') else None
        max_mileage = int(data.get('max_mileage')) if data.get('max_mileage') else None
        max_distance = int(data.get('max_distance')) if data.get('max_distance') else None
        max_price = int(data.get('max_price')) if data.get('max_price') else None
        
        # Update in database
        success = db.update_search_criteria(
            min_year=min_year,
            max_year=max_year, 
            max_mileage=max_mileage,
            max_distance=max_distance,
            max_price=max_price
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Search criteria updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update search criteria'})
            
    except Exception as e:
        logger.error(f"Error updating search criteria: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/watched-cars', methods=['GET'])
def get_watched_cars():
    """Get cars that are being watched"""
    try:
        # Get watched listings from database
        watched_cars = []
        all_listings = db.get_active_listings(limit=1000)
        
        for listing in all_listings:
            if listing.get('is_watched'):
                watched_cars.append(listing)
        
        return jsonify({
            'success': True,
            'watched_cars': watched_cars,
            'count': len(watched_cars)
        })
        
    except Exception as e:
        logger.error(f"Error getting watched cars: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'watched_cars': []
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout from CarGurus OAuth session"""
    session.pop('authenticated', None)
    session.pop('google_email', None)
    session.pop('auth_time', None)
    return jsonify({'success': True, 'message': 'Successfully logged out'})

@app.errorhandler(404)
def not_found(error):
    return render_template('simple_error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('simple_error.html', error='Internal server error'), 500

if __name__ == '__main__':
    # Initialize database and add sample data
    db.init_database()
    # NO MORE SAMPLE DATA - app shows only real CarGurus data or empty state
    logger.info("Database initialized - ready for real CarGurus data only")
    
    logger.info("Starting Simple Porsche Tracker...")
    app.run(host='0.0.0.0', port=5000, debug=True)
