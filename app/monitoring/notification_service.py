import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from app.models import Listing, WatchCriteria

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending email and SMS notifications"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize Twilio client if credentials are available
        self.twilio_client = None
        if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
            try:
                self.twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
    
    def send_new_listing_alert(self, listings: List[Listing], criteria: WatchCriteria):
        """Send alert for new listings matching criteria"""
        try:
            if criteria.email_notifications and criteria.notification_email:
                self._send_new_listing_email(listings, criteria)
            
            if criteria.sms_notifications and criteria.notification_phone:
                self._send_new_listing_sms(listings, criteria)
                
        except Exception as e:
            logger.error(f"Error sending new listing alerts: {str(e)}")
    
    def send_price_change_alert(self, listing: Listing, old_price: int, new_price: int, criteria: WatchCriteria):
        """Send alert for price changes on watched listings"""
        try:
            if criteria.email_notifications and criteria.notification_email:
                self._send_price_change_email(listing, old_price, new_price, criteria)
            
            if criteria.sms_notifications and criteria.notification_phone:
                self._send_price_change_sms(listing, old_price, new_price, criteria)
                
        except Exception as e:
            logger.error(f"Error sending price change alerts: {str(e)}")
    
    def _send_new_listing_email(self, listings: List[Listing], criteria: WatchCriteria):
        """Send email notification for new listings"""
        try:
            if not self.config.EMAIL_USER or not self.config.EMAIL_PASSWORD:
                logger.warning("Email credentials not configured")
                return
            
            subject = f"New Porsche Listings Found - {criteria.name}"
            
            # Build HTML email content
            html_content = self._build_new_listing_email_html(listings, criteria)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.EMAIL_USER
            msg['To'] = criteria.notification_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Sent new listing email to {criteria.notification_email}")
            
        except Exception as e:
            logger.error(f"Error sending new listing email: {str(e)}")
    
    def _send_new_listing_sms(self, listings: List[Listing], criteria: WatchCriteria):
        """Send SMS notification for new listings"""
        try:
            if not self.twilio_client:
                logger.warning("Twilio client not configured")
                return
            
            # Build SMS message (keep it concise)
            if len(listings) == 1:
                listing = listings[0]
                message = f"New Porsche found!\n{listing.year} {listing.model}\n${listing.price:,}\n{listing.city}, {listing.state}\n{listing.url}"
            else:
                message = f"Found {len(listings)} new Porsche listings matching '{criteria.name}'!\nCheck your email for details."
            
            # Send SMS
            self.twilio_client.messages.create(
                body=message,
                from_=self.config.TWILIO_PHONE_NUMBER,
                to=criteria.notification_phone
            )
            
            logger.info(f"Sent new listing SMS to {criteria.notification_phone}")
            
        except TwilioException as e:
            logger.error(f"Twilio error sending SMS: {str(e)}")
        except Exception as e:
            logger.error(f"Error sending new listing SMS: {str(e)}")
    
    def _send_price_change_email(self, listing: Listing, old_price: int, new_price: int, criteria: WatchCriteria):
        """Send email notification for price changes"""
        try:
            if not self.config.EMAIL_USER or not self.config.EMAIL_PASSWORD:
                logger.warning("Email credentials not configured")
                return
            
            price_change = new_price - old_price
            price_change_pct = (price_change / old_price) * 100
            
            change_type = "increased" if price_change > 0 else "decreased"
            change_color = "red" if price_change > 0 else "green"
            
            subject = f"Price Alert: {listing.year} {listing.model} {change_type} by ${abs(price_change):,}"
            
            # Build HTML email content
            html_content = f"""
            <html>
            <body>
                <h2>Price Change Alert</h2>
                <p>The following Porsche listing has had a price change:</p>
                
                <div style="border: 1px solid #ccc; padding: 15px; margin: 10px 0;">
                    <h3>{listing.year} {listing.make} {listing.model}</h3>
                    {f'<p><strong>Trim:</strong> {listing.trim}</p>' if listing.trim else ''}
                    <p><strong>VIN:</strong> {listing.vin if listing.vin else 'Not available'}</p>
                    <p><strong>Mileage:</strong> {f'{listing.mileage:,} miles' if listing.mileage else 'Not specified'}</p>
                    <p><strong>Location:</strong> {listing.city}, {listing.state}</p>
                    <p><strong>Dealer:</strong> {listing.dealer_name or 'Not specified'}</p>
                    
                    <div style="font-size: 18px; margin: 15px 0;">
                        <p><strong>Old Price:</strong> <span style="text-decoration: line-through;">${old_price:,}</span></p>
                        <p><strong>New Price:</strong> <span style="color: {change_color}; font-weight: bold;">${new_price:,}</span></p>
                        <p><strong>Change:</strong> <span style="color: {change_color};">${price_change:+,} ({price_change_pct:+.1f}%)</span></p>
                    </div>
                    
                    <p><a href="{listing.url}" style="background-color: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Listing</a></p>
                </div>
                
                <p><em>You are receiving this alert because this listing matches your watch criteria: {criteria.name}</em></p>
            </body>
            </html>
            """
            
            # Create and send message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.EMAIL_USER
            msg['To'] = criteria.notification_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Sent price change email to {criteria.notification_email}")
            
        except Exception as e:
            logger.error(f"Error sending price change email: {str(e)}")
    
    def _send_price_change_sms(self, listing: Listing, old_price: int, new_price: int, criteria: WatchCriteria):
        """Send SMS notification for price changes"""
        try:
            if not self.twilio_client:
                return
            
            price_change = new_price - old_price
            change_type = "📈" if price_change > 0 else "📉"
            
            message = f"{change_type} Price Alert!\n{listing.year} {listing.model}\nWas: ${old_price:,}\nNow: ${new_price:,}\nChange: ${price_change:+,}\n{listing.url}"
            
            self.twilio_client.messages.create(
                body=message,
                from_=self.config.TWILIO_PHONE_NUMBER,
                to=criteria.notification_phone
            )
            
            logger.info(f"Sent price change SMS to {criteria.notification_phone}")
            
        except Exception as e:
            logger.error(f"Error sending price change SMS: {str(e)}")
    
    def _build_new_listing_email_html(self, listings: List[Listing], criteria: WatchCriteria) -> str:
        """Build HTML email content for new listings"""
        html_content = f"""
        <html>
        <body>
            <h2>New Porsche Listings Found!</h2>
            <p>Found {len(listings)} new listing{'s' if len(listings) != 1 else ''} matching your criteria: <strong>{criteria.name}</strong></p>
        """
        
        for listing in listings:
            # Calculate deal quality if VIN data is available
            deal_info = ""
            if listing.vin_data and listing.vin_data.market_value_estimate:
                value_analysis = listing.vin_data.calculate_value_analysis(listing.price)
                if value_analysis:
                    if value_analysis['is_good_deal']:
                        deal_color = "green"
                        deal_text = f"Great Deal! ${abs(value_analysis['value_difference']):,} under market value"
                    else:
                        deal_color = "red"
                        deal_text = f"${value_analysis['value_difference']:,} over market value"
                    deal_info = f'<p style="color: {deal_color}; font-weight: bold;">{deal_text}</p>'
            
            html_content += f"""
            <div style="border: 1px solid #ccc; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <h3 style="color: #333;">{listing.year} {listing.make} {listing.model}</h3>
                {f'<p><strong>Trim:</strong> {listing.trim}</p>' if listing.trim else ''}
                <p><strong>Price:</strong> <span style="font-size: 20px; color: #007cba; font-weight: bold;">${listing.price:,}</span></p>
                {deal_info}
                <p><strong>Mileage:</strong> {f'{listing.mileage:,} miles' if listing.mileage else 'Not specified'}</p>
                <p><strong>Condition:</strong> {listing.condition}</p>
                {f'<p><strong>Exterior Color:</strong> {listing.exterior_color}</p>' if listing.exterior_color else ''}
                {f'<p><strong>Interior Color:</strong> {listing.interior_color}</p>' if listing.interior_color else ''}
                <p><strong>Location:</strong> {listing.city}, {listing.state} {f'({listing.distance_from_user:.1f} miles)' if listing.distance_from_user else ''}</p>
                <p><strong>Dealer:</strong> {listing.dealer_name or 'Not specified'}</p>
                {f'<p><strong>VIN:</strong> {listing.vin}</p>' if listing.vin else ''}
                
                <p><a href="{listing.url}" style="background-color: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Listing</a></p>
            </div>
            """
        
        html_content += """
            <p><em>You are receiving this alert because these listings match your monitoring criteria. You can manage your alerts and criteria in your Porsche Tracker dashboard.</em></p>
        </body>
        </html>
        """
        
        return html_content
