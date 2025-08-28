#!/usr/bin/env python3
"""
Porsche Tracker Application
Main entry point for the Flask web application
"""

import os
import logging
import schedule
import time
import threading
from app import create_app, db
from app.models import Listing, WatchCriteria, PriceHistory, VinData
from app.monitoring import ListingMonitor, PriceTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('porsche_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create Flask app
app = create_app()

def run_scheduled_monitoring():
    """Run monitoring tasks on schedule"""
    with app.app_context():
        try:
            logger.info("Running scheduled monitoring cycle...")
            
            monitor = ListingMonitor(app.config)
            price_tracker = PriceTracker(app.config)
            
            # Run monitoring for new listings
            monitor.run_monitoring_cycle()
            
            # Run price tracking for watched listings
            price_tracker.track_watched_listings()
            
            logger.info("Scheduled monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in scheduled monitoring: {str(e)}")

def start_scheduler():
    """Start the background scheduler"""
    logger.info("Starting background scheduler...")
    
    # Schedule monitoring every 30 minutes
    schedule.every(30).minutes.do(run_scheduled_monitoring)
    
    # Schedule price tracking every hour
    schedule.every().hour.do(lambda: threading.Thread(target=run_scheduled_monitoring).start())
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

@app.cli.command()
def init_db():
    """Initialize the database with sample data"""
    logger.info("Initializing database...")
    
    # Create all tables
    db.create_all()
    
    # Check if we already have data
    if WatchCriteria.query.first():
        logger.info("Database already has data, skipping initialization")
        return
    
    # Create sample watch criteria
    sample_criteria = WatchCriteria(
        name="Dream 911",
        make="Porsche",
        models='["911"]',
        min_year=2018,
        max_year=2024,
        max_price=200000,
        max_mileage=50000,
        max_distance=100.0,
        user_zip_code="90210",
        exterior_colors='["Guards Red", "GT Silver Metallic", "Black"]',
        conditions='["Used", "CPO"]',
        email_notifications=True,
        notification_email="user@example.com"
    )
    
    db.session.add(sample_criteria)
    
    # Create another sample criteria
    sample_criteria_2 = WatchCriteria(
        name="Cayenne Family Car",
        make="Porsche",
        models='["Cayenne"]',
        min_year=2019,
        max_year=2024,
        max_price=80000,
        max_mileage=40000,
        max_distance=50.0,
        user_zip_code="90210",
        conditions='["Used", "CPO", "New"]',
        email_notifications=True,
        notification_email="user@example.com"
    )
    
    db.session.add(sample_criteria_2)
    
    try:
        db.session.commit()
        logger.info("Sample data created successfully")
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        db.session.rollback()

@app.cli.command()
def run_monitoring():
    """Run monitoring cycle manually"""
    logger.info("Running manual monitoring cycle...")
    
    monitor = ListingMonitor(app.config)
    monitor.run_monitoring_cycle()
    
    logger.info("Manual monitoring cycle completed")

@app.cli.command()
def run_price_tracking():
    """Run price tracking manually"""
    logger.info("Running manual price tracking...")
    
    price_tracker = PriceTracker(app.config)
    price_tracker.track_watched_listings()
    
    logger.info("Manual price tracking completed")

@app.cli.command()
def cleanup_old_data():
    """Clean up old inactive listings and price history"""
    logger.info("Cleaning up old data...")
    
    from datetime import datetime, timedelta
    
    # Delete listings inactive for more than 30 days
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    old_listings = Listing.query.filter(
        Listing.is_active == False,
        Listing.last_updated < cutoff_date
    ).all()
    
    for listing in old_listings:
        logger.info(f"Deleting old listing: {listing.id}")
        db.session.delete(listing)
    
    # Keep only last 100 price history records per listing
    listings_with_history = db.session.query(Listing.id).join(PriceHistory).distinct().all()
    
    for listing_id, in listings_with_history:
        price_history = PriceHistory.query.filter_by(listing_id=listing_id)\
                                         .order_by(PriceHistory.recorded_at.desc())\
                                         .all()
        
        if len(price_history) > 100:
            old_records = price_history[100:]
            for record in old_records:
                db.session.delete(record)
    
    try:
        db.session.commit()
        logger.info("Data cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        db.session.rollback()

@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'Listing': Listing,
        'WatchCriteria': WatchCriteria,
        'PriceHistory': PriceHistory,
        'VinData': VinData,
        'ListingMonitor': ListingMonitor,
        'PriceTracker': PriceTracker
    }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'scheduler':
            # Run background scheduler
            logger.info("Starting Porsche Tracker with background scheduler...")
            
            # Start scheduler in a separate thread
            scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
            scheduler_thread.start()
            
            # Start Flask app
            app.run(host='0.0.0.0', port=5000, debug=False)
            
        elif command == 'dev':
            # Development mode without scheduler
            logger.info("Starting Porsche Tracker in development mode...")
            app.run(host='0.0.0.0', port=5000, debug=True)
            
        else:
            logger.error(f"Unknown command: {command}")
            print("Usage:")
            print("  python app.py dev        - Development mode")
            print("  python app.py scheduler  - Production mode with scheduler")
            print("  flask init-db           - Initialize database")
            print("  flask run-monitoring    - Run monitoring manually")
            print("  flask run-price-tracking - Run price tracking manually")
            print("  flask cleanup-old-data  - Clean up old data")
    else:
        # Default to development mode
        logger.info("Starting Porsche Tracker in development mode...")
        app.run(host='0.0.0.0', port=5000, debug=True)
