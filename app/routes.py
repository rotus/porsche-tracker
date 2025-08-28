from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app import db
from app.models import Listing, WatchCriteria, PriceHistory, VinData
from app.monitoring import ListingMonitor, PriceTracker, NotificationService
from app.scrapers import CarGurusScraper, VinEnricher
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

# Initialize services (these would normally be dependency-injected)
def get_services():
    from flask import current_app
    config = current_app.config
    return {
        'monitor': ListingMonitor(config),
        'price_tracker': PriceTracker(config),
        'scraper': CarGurusScraper(config),
        'vin_enricher': VinEnricher(config)
    }

# Main web routes
@main_bp.route('/')
def index():
    """Dashboard homepage"""
    try:
        # Get summary statistics
        total_listings = Listing.query.filter_by(is_active=True).count()
        watched_listings = Listing.query.filter_by(is_watched=True, is_active=True).count()
        active_criteria = WatchCriteria.query.filter_by(is_active=True).count()
        
        # Get recent listings
        recent_listings = Listing.query.filter_by(is_active=True)\
                                      .order_by(Listing.first_seen.desc())\
                                      .limit(10).all()
        
        # Get recent price changes
        recent_price_changes = db.session.query(PriceHistory, Listing)\
                                       .join(Listing)\
                                       .filter(Listing.is_active == True)\
                                       .order_by(PriceHistory.recorded_at.desc())\
                                       .limit(10).all()
        
        return render_template('dashboard.html',
                             total_listings=total_listings,
                             watched_listings=watched_listings,
                             active_criteria=active_criteria,
                             recent_listings=recent_listings,
                             recent_price_changes=recent_price_changes)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html',
                             total_listings=0,
                             watched_listings=0,
                             active_criteria=0,
                             recent_listings=[],
                             recent_price_changes=[])

@main_bp.route('/listings')
def listings():
    """Browse all listings with filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Build query with filters
        query = Listing.query.filter_by(is_active=True)
        
        # Apply filters
        model = request.args.get('model')
        if model:
            query = query.filter_by(model=model)
        
        min_year = request.args.get('min_year', type=int)
        if min_year:
            query = query.filter(Listing.year >= min_year)
        
        max_year = request.args.get('max_year', type=int)
        if max_year:
            query = query.filter(Listing.year <= max_year)
        
        min_price = request.args.get('min_price', type=int)
        if min_price:
            query = query.filter(Listing.price >= min_price)
        
        max_price = request.args.get('max_price', type=int)
        if max_price:
            query = query.filter(Listing.price <= max_price)
        
        max_mileage = request.args.get('max_mileage', type=int)
        if max_mileage:
            query = query.filter(Listing.mileage <= max_mileage)
        
        exterior_color = request.args.get('exterior_color')
        if exterior_color:
            query = query.filter_by(exterior_color=exterior_color)
        
        # Sort options
        sort_by = request.args.get('sort', 'newest')
        if sort_by == 'price_low':
            query = query.order_by(Listing.price.asc())
        elif sort_by == 'price_high':
            query = query.order_by(Listing.price.desc())
        elif sort_by == 'mileage':
            query = query.order_by(Listing.mileage.asc())
        elif sort_by == 'year':
            query = query.order_by(Listing.year.desc())
        else:  # newest
            query = query.order_by(Listing.first_seen.desc())
        
        # Paginate results
        listings_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Get filter options for the form
        models = db.session.query(Listing.model.distinct()).filter(Listing.model.isnot(None)).all()
        models = [m[0] for m in models]
        
        colors = db.session.query(Listing.exterior_color.distinct()).filter(Listing.exterior_color.isnot(None)).all()
        colors = [c[0] for c in colors]
        
        return render_template('listings.html',
                             listings_page=listings_page,
                             models=models,
                             colors=colors,
                             current_filters=request.args)
        
    except Exception as e:
        logger.error(f"Error loading listings: {str(e)}")
        flash(f'Error loading listings: {str(e)}', 'error')
        return render_template('listings.html', listings_page=None, models=[], colors=[])

@main_bp.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    """Detailed view of a specific listing"""
    try:
        listing = Listing.query.get_or_404(listing_id)
        
        # Get price history
        price_history = PriceHistory.query.filter_by(listing_id=listing_id)\
                                         .order_by(PriceHistory.recorded_at.desc())\
                                         .all()
        
        # Get price analytics
        services = get_services()
        price_analytics = services['price_tracker'].get_price_history_analytics(listing_id)
        
        # Get similar listings
        similar_listings = Listing.query.filter(
            Listing.model == listing.model,
            Listing.year.between(listing.year - 2, listing.year + 2),
            Listing.id != listing.id,
            Listing.is_active == True
        ).limit(5).all()
        
        return render_template('listing_detail.html',
                             listing=listing,
                             price_history=price_history,
                             price_analytics=price_analytics,
                             similar_listings=similar_listings)
        
    except Exception as e:
        logger.error(f"Error loading listing detail: {str(e)}")
        flash(f'Error loading listing: {str(e)}', 'error')
        return redirect(url_for('main.listings'))

@main_bp.route('/watch-criteria')
def watch_criteria():
    """Manage watch criteria"""
    try:
        criteria_list = WatchCriteria.query.order_by(WatchCriteria.created_at.desc()).all()
        return render_template('watch_criteria.html', criteria_list=criteria_list)
        
    except Exception as e:
        logger.error(f"Error loading watch criteria: {str(e)}")
        flash(f'Error loading watch criteria: {str(e)}', 'error')
        return render_template('watch_criteria.html', criteria_list=[])

@main_bp.route('/create-criteria', methods=['GET', 'POST'])
def create_criteria():
    """Create new watch criteria"""
    if request.method == 'GET':
        return render_template('create_criteria.html')
    
    try:
        # Create new criteria from form data
        criteria = WatchCriteria(
            name=request.form['name'],
            make='Porsche',
            models=json.dumps(request.form.getlist('models')),
            min_year=int(request.form['min_year']) if request.form.get('min_year') else None,
            max_year=int(request.form['max_year']) if request.form.get('max_year') else None,
            min_price=int(request.form['min_price']) if request.form.get('min_price') else None,
            max_price=int(request.form['max_price']) if request.form.get('max_price') else None,
            max_mileage=int(request.form['max_mileage']) if request.form.get('max_mileage') else None,
            max_distance=float(request.form['max_distance']) if request.form.get('max_distance') else None,
            user_zip_code=request.form.get('user_zip_code'),
            exterior_colors=json.dumps(request.form.getlist('exterior_colors')),
            interior_colors=json.dumps(request.form.getlist('interior_colors')),
            transmissions=json.dumps(request.form.getlist('transmissions')),
            drivetrains=json.dumps(request.form.getlist('drivetrains')),
            conditions=json.dumps(request.form.getlist('conditions')),
            email_notifications=bool(request.form.get('email_notifications')),
            sms_notifications=bool(request.form.get('sms_notifications')),
            notification_email=request.form.get('notification_email'),
            notification_phone=request.form.get('notification_phone')
        )
        
        db.session.add(criteria)
        db.session.commit()
        
        flash(f'Watch criteria "{criteria.name}" created successfully!', 'success')
        return redirect(url_for('main.watch_criteria'))
        
    except Exception as e:
        logger.error(f"Error creating watch criteria: {str(e)}")
        flash(f'Error creating watch criteria: {str(e)}', 'error')
        db.session.rollback()
        return render_template('create_criteria.html')

@main_bp.route('/compare')
def compare_listings():
    """Compare multiple listings"""
    try:
        listing_ids = request.args.getlist('ids', type=int)
        if not listing_ids:
            flash('Please select listings to compare', 'warning')
            return redirect(url_for('main.listings'))
        
        listings = Listing.query.filter(Listing.id.in_(listing_ids), Listing.is_active == True).all()
        
        if not listings:
            flash('No valid listings found for comparison', 'error')
            return redirect(url_for('main.listings'))
        
        # Get enhanced data for comparison
        comparison_data = []
        for listing in listings:
            data = listing.to_dict()
            
            # Add VIN enriched data
            if listing.vin_data:
                data['vin_data'] = listing.vin_data.to_dict()
                if listing.vin_data.market_value_estimate:
                    data['value_analysis'] = listing.vin_data.calculate_value_analysis(listing.price)
            
            # Add price history summary
            price_history = PriceHistory.query.filter_by(listing_id=listing.id).all()
            if price_history:
                prices = [ph.price for ph in price_history]
                data['price_history_summary'] = {
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'price_changes': len(price_history)
                }
            
            comparison_data.append(data)
        
        return render_template('compare_listings.html', comparison_data=comparison_data)
        
    except Exception as e:
        logger.error(f"Error comparing listings: {str(e)}")
        flash(f'Error comparing listings: {str(e)}', 'error')
        return redirect(url_for('main.listings'))

# API Routes
@api_bp.route('/watch-listing/<int:listing_id>', methods=['POST'])
def watch_listing(listing_id):
    """Add listing to watch list"""
    try:
        services = get_services()
        success = services['monitor'].mark_listing_as_watched(listing_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Listing added to watch list'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add listing to watch list'}), 400
            
    except Exception as e:
        logger.error(f"Error watching listing: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/unwatch-listing/<int:listing_id>', methods=['POST'])
def unwatch_listing(listing_id):
    """Remove listing from watch list"""
    try:
        services = get_services()
        success = services['monitor'].unwatch_listing(listing_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Listing removed from watch list'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove listing from watch list'}), 400
            
    except Exception as e:
        logger.error(f"Error unwatching listing: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/run-monitoring', methods=['POST'])
def run_monitoring():
    """Manually trigger monitoring cycle"""
    try:
        services = get_services()
        services['monitor'].run_monitoring_cycle()
        return jsonify({'success': True, 'message': 'Monitoring cycle completed'})
        
    except Exception as e:
        logger.error(f"Error running monitoring: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/price-tracking', methods=['POST'])
def run_price_tracking():
    """Manually trigger price tracking"""
    try:
        services = get_services()
        services['price_tracker'].track_watched_listings()
        return jsonify({'success': True, 'message': 'Price tracking completed'})
        
    except Exception as e:
        logger.error(f"Error running price tracking: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/market-analysis')
def market_analysis():
    """Get market analysis data"""
    try:
        model = request.args.get('model')
        min_year = request.args.get('min_year', type=int)
        max_year = request.args.get('max_year', type=int)
        
        year_range = None
        if min_year and max_year:
            year_range = (min_year, max_year)
        
        services = get_services()
        analysis = services['price_tracker'].get_market_analysis(model, year_range)
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error getting market analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/listing/<int:listing_id>/analytics')
def listing_analytics(listing_id):
    """Get price analytics for a specific listing"""
    try:
        services = get_services()
        analytics = services['price_tracker'].get_price_history_analytics(listing_id)
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Error getting listing analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/enrich-vin', methods=['POST'])
def enrich_vin():
    """Enrich a listing with VIN data"""
    try:
        data = request.get_json()
        listing_id = data.get('listing_id')
        
        if not listing_id:
            return jsonify({'success': False, 'message': 'listing_id required'}), 400
        
        listing = Listing.query.get(listing_id)
        if not listing or not listing.vin:
            return jsonify({'success': False, 'message': 'Listing not found or no VIN available'}), 404
        
        services = get_services()
        services['monitor']._enrich_listing_with_vin_data(listing)
        
        return jsonify({'success': True, 'message': 'VIN data enrichment completed'})
        
    except Exception as e:
        logger.error(f"Error enriching VIN: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/criteria/<int:criteria_id>/toggle', methods=['POST'])
def toggle_criteria(criteria_id):
    """Toggle criteria active status"""
    try:
        criteria = WatchCriteria.query.get_or_404(criteria_id)
        criteria.is_active = not criteria.is_active
        db.session.commit()
        
        status = 'activated' if criteria.is_active else 'deactivated'
        return jsonify({'success': True, 'message': f'Criteria {status}', 'is_active': criteria.is_active})
        
    except Exception as e:
        logger.error(f"Error toggling criteria: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/listings/search')
def search_listings():
    """Search listings via AJAX"""
    try:
        query = Listing.query.filter_by(is_active=True)
        
        # Apply search filters (similar to main listings route)
        search_term = request.args.get('q')
        if search_term:
            query = query.filter(
                db.or_(
                    Listing.model.ilike(f'%{search_term}%'),
                    Listing.trim.ilike(f'%{search_term}%'),
                    Listing.dealer_name.ilike(f'%{search_term}%')
                )
            )
        
        # Add other filters as needed...
        
        listings = query.limit(50).all()
        results = [listing.to_dict() for listing in listings]
        
        return jsonify({'listings': results})
        
    except Exception as e:
        logger.error(f"Error searching listings: {str(e)}")
        return jsonify({'error': str(e)}), 500
