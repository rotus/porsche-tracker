#!/usr/bin/env python3
"""
Test Google OAuth Authentication for CarGurus
Run this to test the OAuth flow before using it in the main app
"""

import sys
import logging
from cargurus_auth import AuthenticatedCarGurusScraper

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_oauth_flow():
    """Test the Google OAuth authentication flow"""
    
    if len(sys.argv) < 2:
        print("Usage: python test_oauth.py your.email@gmail.com")
        print("Example: python test_oauth.py john.doe@gmail.com")
        sys.exit(1)
    
    google_email = sys.argv[1]
    
    print(f"🚀 Testing Google OAuth for CarGurus with email: {google_email}")
    print("=" * 60)
    
    try:
        # Create scraper with OAuth
        scraper = AuthenticatedCarGurusScraper(google_email)
        
        # Attempt authentication
        print("📋 Starting OAuth authentication...")
        auth_success = scraper.authenticate_with_google_oauth()
        
        if auth_success:
            print("✅ OAuth authentication successful!")
            print("🎯 You can now use the authenticated scraper in the main app")
            
            # Optional: Test a quick scrape
            response = input("Would you like to test scraping a few listings? (y/n): ")
            if response.lower().startswith('y'):
                print("🔍 Testing scraping with authenticated session...")
                listings = scraper.scrape_porsche_listings(max_listings=2)
                
                if listings:
                    print(f"✅ Successfully scraped {len(listings)} listings!")
                    for i, listing in enumerate(listings, 1):
                        print(f"   {i}. {listing.get('year')} {listing.get('model')} {listing.get('trim')} - ${listing.get('price', 'N/A'):,}")
                        if listing.get('url'):
                            print(f"      URL: {listing['url']}")
                else:
                    print("⚠️  No listings found - may need to adjust scraping logic")
        else:
            print("❌ OAuth authentication failed")
            print("💡 Common issues:")
            print("   - Google blocked the automated browser")
            print("   - User didn't complete the OAuth flow")
            print("   - Network/timeout issues")
            
    except Exception as e:
        print(f"❌ Error during OAuth test: {str(e)}")
        
    finally:
        # Clean up browser
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.driver.quit()
            print("🧹 Browser cleaned up")

if __name__ == "__main__":
    test_oauth_flow()
