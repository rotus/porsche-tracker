# Porsche Tracker

A comprehensive web application for tracking, monitoring, and analyzing Porsche listings from CarGurus.com with advanced VIN data enrichment and price change alerts.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-orange.svg)

## Features

### 🔍 **Smart Monitoring System**
- **Custom Watch Criteria**: Set up personalized monitoring based on model, year, price range, mileage, distance, and color preferences
- **Automated Scanning**: Continuously monitors CarGurus for new listings matching your criteria
- **Real-time Alerts**: Instant email and SMS notifications when new matches are found

### 📈 **Advanced Price Tracking**
- **Price History**: Track price changes over time for any listing
- **Trend Analysis**: Identify price patterns and market trends
- **Smart Recommendations**: AI-powered buying recommendations based on price history and market conditions
- **Deal Scoring**: Automatic evaluation of listing value compared to market estimates

### 🔧 **VIN Data Enrichment**
- **Multiple Data Sources**: Integrates with NHTSA, Vehicle Database APIs, and Porsche-specific databases
- **Comprehensive Details**: Engine specs, build information, recall data, accident history
- **Market Valuation**: Real-time market value estimates and depreciation analysis
- **Quality Scoring**: Data confidence and completeness metrics

### 📊 **Market Analytics**
- **Market Overview**: Comprehensive analysis of current Porsche inventory
- **Price Distribution**: Statistical analysis of pricing across models and years
- **Comparison Tools**: Side-by-side listing comparisons with enriched data
- **Historical Trends**: Track market changes over time

### 🌐 **Modern Web Interface**
- **Responsive Design**: Beautiful, mobile-friendly interface built with Bootstrap
- **Interactive Charts**: Dynamic visualizations using Plotly.js
- **Real-time Updates**: Live price change notifications and listing updates
- **Easy Management**: Simple interface for managing watch criteria and alerts

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for web scraping)
- Email account (for notifications)
- Optional: Twilio account (for SMS alerts)
- Optional: VIN API key (for enhanced data)

### Installation

1. **Clone and setup**:
```bash
cd porsche-tracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment** (create `.env` file):
```env
# Database
DATABASE_URL=sqlite:///porsche_tracker.db

# Email notifications
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# SMS notifications (optional)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# VIN API (optional)
VIN_API_KEY=your_vin_api_key
VIN_API_URL=https://api.vehicledatabase.net/

# Security
SECRET_KEY=your-secret-key-here
```

3. **Initialize database**:
```bash
flask init-db
```

4. **Run the application**:
```bash
# Development mode
python app.py dev

# Production mode with background monitoring
python app.py scheduler
```

5. **Access the application**:
   - Open http://localhost:5000 in your browser
   - Create your first watch criteria
   - Start monitoring for listings!

## Usage

### Setting Up Watch Criteria

1. **Navigate to "Watch Criteria"** in the web interface
2. **Click "Create New Criteria"** and configure:
   - **Models**: Select which Porsche models to monitor (911, Cayenne, Macan, etc.)
   - **Price Range**: Set minimum and maximum price limits
   - **Year Range**: Specify model years of interest
   - **Location**: Set maximum distance from your ZIP code
   - **Condition**: Choose New, Used, or CPO
   - **Colors**: Select preferred exterior/interior colors
   - **Notifications**: Configure email and SMS alerts

### Monitoring and Alerts

The system automatically:
- **Searches CarGurus** every 30 minutes for new listings
- **Tracks prices** on watched listings hourly
- **Sends alerts** when new matches are found or prices change
- **Enriches data** with VIN information when available

### Manual Operations

Use the dashboard to:
- **Run immediate searches** for new listings
- **Update prices** on watched listings
- **View detailed analytics** for any listing
- **Compare multiple listings** side-by-side

### Command Line Tools

```bash
# Manual monitoring
flask run-monitoring

# Manual price tracking
flask run-price-tracking

# Clean up old data
flask cleanup-old-data
```

## Architecture

### Core Components

- **Flask Web Application**: Modern web interface with REST API
- **SQLAlchemy Database**: Robust data persistence with relationship management
- **Selenium Web Scraper**: Advanced CarGurus data extraction
- **Background Scheduler**: Automated monitoring and price tracking
- **Multi-source VIN Enrichment**: Comprehensive vehicle data integration
- **Notification System**: Email and SMS alert capabilities

### Database Schema

- **Listings**: Core vehicle data with pricing and location information
- **WatchCriteria**: User-defined monitoring parameters
- **PriceHistory**: Historical price tracking with analytics
- **VinData**: Enriched vehicle information from multiple sources

### Data Flow

1. **Monitor** → Scrapes CarGurus based on watch criteria
2. **Extract** → Parses listing data and checks for existing records
3. **Enrich** → Enhances data with VIN information when available
4. **Track** → Records price changes and market trends
5. **Alert** → Notifies users of new matches and price changes
6. **Analyze** → Provides market insights and recommendations

## Configuration

### Email Setup (Gmail)

1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: Account Settings → Security → App Passwords
3. Use your Gmail address and the app password in the configuration

### Twilio SMS Setup

1. Create a Twilio account and get a phone number
2. Find your Account SID and Auth Token in the console
3. Add the credentials to your configuration

### VIN API Setup

The application supports multiple VIN data providers:
- **NHTSA API**: Free, basic vehicle information
- **Vehicle Database API**: Paid, comprehensive data
- **Custom Porsche APIs**: Specialized Porsche data sources

## API Endpoints

### REST API

- `GET /api/listings/search` - Search listings
- `POST /api/watch-listing/<id>` - Add listing to watch list
- `POST /api/run-monitoring` - Trigger monitoring cycle
- `GET /api/market-analysis` - Get market analytics
- `GET /api/listing/<id>/analytics` - Get listing analytics

### Web Routes

- `/` - Dashboard with overview and quick actions
- `/listings` - Browse and filter all listings
- `/listing/<id>` - Detailed listing view with analytics
- `/watch-criteria` - Manage monitoring criteria
- `/compare` - Compare multiple listings side-by-side

## Development

### Project Structure
```
porsche-tracker/
├── app/
│   ├── models/           # Database models
│   ├── scrapers/         # Web scraping components
│   ├── monitoring/       # Monitoring and alerts
│   ├── templates/        # HTML templates
│   ├── static/          # CSS, JS, images
│   └── routes.py        # Flask routes
├── config/              # Configuration files
├── app.py              # Main application entry point
└── requirements.txt    # Python dependencies
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Legal and Ethical Usage

### Important Notes

- **Respect robots.txt**: Always check and respect CarGurus' robots.txt file
- **Rate Limiting**: The application includes delays between requests to avoid overloading servers
- **Terms of Service**: Ensure your usage complies with CarGurus' terms of service
- **Personal Use**: This tool is intended for personal use in car shopping research

### Data Sources

- **CarGurus.com**: Primary source for listing data
- **NHTSA**: Government vehicle safety and recall data
- **Third-party APIs**: Various VIN and market value services
- **User-generated**: Watch criteria and preference data

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues**:
   ```bash
   # Update Chrome driver
   pip install --upgrade webdriver-manager
   ```

2. **Database Errors**:
   ```bash
   # Reset database
   rm porsche_tracker.db
   flask init-db
   ```

3. **Scraping Failures**:
   - Check your internet connection
   - Verify CarGurus hasn't changed their layout
   - Update the scraper selectors if needed

4. **Email Issues**:
   - Ensure Gmail app password is correct
   - Check spam folder for notifications
   - Verify SMTP settings

### Performance Optimization

- **Database**: Regularly clean up old data using `flask cleanup-old-data`
- **Monitoring**: Adjust monitoring frequency based on your needs
- **Memory**: Monitor memory usage during long-running operations

## Roadmap

### Planned Features
- [ ] Mobile app (iOS/Android)
- [ ] Advanced filtering options
- [ ] Saved searches and favorites
- [ ] Market prediction algorithms
- [ ] Integration with more data sources
- [ ] Social sharing features
- [ ] Financing calculator integration

### Recent Updates
- ✅ Initial release with core functionality
- ✅ VIN data enrichment
- ✅ Price tracking and alerts
- ✅ Market analysis tools
- ✅ Responsive web interface

## Support

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Wiki**: Check the wiki for additional documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and personal use only. Users are responsible for ensuring their usage complies with all applicable terms of service and applicable laws. The authors are not responsible for any misuse of this software.

---

**Happy Porsche hunting! 🏎️**
