#!/usr/bin/env python3
"""
Configuration Example for Porsche Tracker
Copy this to config_local.py and update with your settings
"""

# CarGurus Authentication (for real data scraping)
CARGURUS_USERNAME = "your_email@example.com"
CARGURUS_PASSWORD = "your_password"

# Default Search Parameters  
DEFAULT_ZIP_CODE = "90210"
DEFAULT_SEARCH_DISTANCE = 100
MAX_LISTINGS_PER_SCRAPE = 50

# Flask Configuration
FLASK_DEBUG = True
SECRET_KEY = "your-secret-key-here"

# Database
DATABASE_PATH = "porsche_tracker.db"

# Scraping Settings
REQUEST_DELAY = 2  # Seconds between requests
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Notification Settings (Future Implementation)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = ""
SMTP_PASSWORD = ""

TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_FROM_PHONE = ""

# Feature Flags
ENABLE_EMAIL_NOTIFICATIONS = False
ENABLE_SMS_NOTIFICATIONS = False
ENABLE_PRICE_TRACKING = True
ENABLE_VIN_ENRICHMENT = True
