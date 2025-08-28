#!/usr/bin/env python3
"""
Simple Porsche Tracker Application
Uses built-in sqlite3 instead of SQLAlchemy for Python 3.13 compatibility
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from simple_db import db
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = 'porsche-tracker-secret-key-change-in-production'

# Routes
@app.route('/')
def dashboard():
    """Dashboard homepage"""
    try:
        # Get summary statistics
        stats = db.get_dashboard_stats()
        
        # Get recent listings
        recent_listings = db.get_active_listings(limit=10)
        
        # Get recent price changes (simplified)
        recent_price_changes = []
        
        return render_template('simple_dashboard.html',
                             total_listings=stats.get('total_listings', 0),
                             watched_listings=stats.get('watched_listings', 0),
                             active_criteria=stats.get('active_criteria', 0),
                             recent_price_changes=stats.get('recent_price_changes', 0),
                             recent_listings=recent_listings)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('simple_dashboard.html',
                             total_listings=0,
                             watched_listings=0,
                             active_criteria=0,
                             recent_price_changes=0,
                             recent_listings=[])

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
                             current_filters=request.args)
        
    except Exception as e:
        logger.error(f"Error loading listings: {str(e)}")
        flash(f'Error loading listings: {str(e)}', 'error')
        return render_template('simple_listings.html', listings=[], models=[], colors=[], current_filters={})

@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    """Detailed view of a specific listing"""
    try:
        # Get listing (simplified - we'll need to add this method to SimpleDB)
        listing = db.get_listing_by_id(listing_id)
        if not listing:
            flash('Listing not found', 'error')
            return redirect(url_for('listings'))
        
        # Get price history
        price_history = db.get_price_history(listing_id)
        
        return render_template('simple_listing_detail.html',
                             listing=listing,
                             price_history=price_history)
        
    except Exception as e:
        logger.error(f"Error loading listing detail: {str(e)}")
        flash(f'Error loading listing: {str(e)}', 'error')
        return redirect(url_for('listings'))

@app.route('/watch-criteria')
def watch_criteria():
    """Manage watch criteria"""
    try:
        criteria_list = db.get_active_watch_criteria()
        return render_template('simple_criteria.html', criteria_list=criteria_list)
        
    except Exception as e:
        logger.error(f"Error loading watch criteria: {str(e)}")
        flash(f'Error loading watch criteria: {str(e)}', 'error')
        return render_template('simple_criteria.html', criteria_list=[])

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
        db.add_gt3rs_sample_data()
        return jsonify({'success': True, 'message': 'Sample GT3 RS listings added successfully'})
    except Exception as e:
        logger.error(f"Error adding GT3 RS samples: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('simple_error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('simple_error.html', error='Internal server error'), 500

if __name__ == '__main__':
    # Initialize database and add sample data
    db.init_database()
    db.add_sample_data()
    db.add_gt3rs_sample_data()  # Add GT3 RS sample listings
    
    logger.info("Starting Simple Porsche Tracker...")
    app.run(host='0.0.0.0', port=5000, debug=True)
