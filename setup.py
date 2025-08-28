#!/usr/bin/env python3
"""
Porsche Tracker Setup Script
Automated setup and configuration for the Porsche tracking application
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_chrome():
    """Check if Chrome is installed"""
    chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',     # Windows
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        '/usr/bin/google-chrome',  # Linux
        '/usr/bin/chromium-browser'
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print("✅ Chrome browser found")
            return True
    
    # Try to find chrome in PATH
    if shutil.which('google-chrome') or shutil.which('chrome') or shutil.which('chromium-browser'):
        print("✅ Chrome browser found in PATH")
        return True
    
    print("⚠️  Chrome browser not found. Please install Google Chrome for web scraping.")
    return False

def create_virtual_environment():
    """Create a virtual environment"""
    if os.path.exists('venv'):
        print("✅ Virtual environment already exists")
        return
    
    print("📦 Creating virtual environment...")
    try:
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        print("✅ Virtual environment created")
    except subprocess.CalledProcessError:
        print("❌ Failed to create virtual environment")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    
    # Determine the correct pip path
    if sys.platform == 'win32':
        pip_path = os.path.join('venv', 'Scripts', 'pip')
    else:
        pip_path = os.path.join('venv', 'bin', 'pip')
    
    try:
        subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def create_env_file():
    """Create .env file from template"""
    env_file = Path('.env')
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("⚙️  Creating .env configuration file...")
    
    env_template = """# Database Configuration
DATABASE_URL=sqlite:///porsche_tracker.db

# Email Configuration (for notifications)
# Generate an App Password in your Google Account settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Twilio Configuration (for SMS alerts - optional)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# VIN API Configuration (optional)
VIN_API_KEY=your_vin_api_key
VIN_API_URL=https://api.vehicledatabase.net/

# Flask Configuration
SECRET_KEY=porsche-tracker-secret-key-change-this-in-production
FLASK_ENV=development
"""
    
    with open('.env', 'w') as f:
        f.write(env_template)
    
    print("✅ .env file created")
    print("⚠️  Please edit .env file with your actual configuration values")

def initialize_database():
    """Initialize the database"""
    print("🗄️  Initializing database...")
    
    # Determine the correct flask path
    if sys.platform == 'win32':
        flask_path = os.path.join('venv', 'Scripts', 'flask')
    else:
        flask_path = os.path.join('venv', 'bin', 'flask')
    
    try:
        env = os.environ.copy()
        env['FLASK_APP'] = 'app.py'
        
        subprocess.run([flask_path, 'init-db'], check=True, env=env)
        print("✅ Database initialized with sample data")
    except subprocess.CalledProcessError:
        print("❌ Failed to initialize database")
        sys.exit(1)

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Edit the .env file with your email credentials:")
    print("   - EMAIL_USER: Your Gmail address")
    print("   - EMAIL_PASSWORD: Gmail App Password (not your regular password)")
    print("   - Optional: Add Twilio credentials for SMS alerts")
    print("   - Optional: Add VIN API key for enhanced data")
    
    print("\n2. Start the application:")
    
    if sys.platform == 'win32':
        print("   venv\\Scripts\\activate")
        print("   python app.py dev")
    else:
        print("   source venv/bin/activate")
        print("   python app.py dev")
    
    print("\n3. Open your browser and go to: http://localhost:5000")
    
    print("\n4. Create your first watch criteria and start monitoring!")
    
    print("\n📚 Additional Commands:")
    print("   flask run-monitoring      - Manually search for listings")
    print("   flask run-price-tracking  - Check for price changes") 
    print("   python app.py scheduler   - Run with background monitoring")
    
    print("\n📖 For detailed instructions, see README.md")
    print("💡 For Gmail setup, see: https://support.google.com/accounts/answer/185833")

def main():
    """Main setup process"""
    print("🏎️  Porsche Tracker Setup")
    print("="*40)
    
    # Check system requirements
    check_python_version()
    check_chrome()
    
    # Setup Python environment
    create_virtual_environment()
    install_dependencies()
    
    # Setup configuration
    create_env_file()
    initialize_database()
    
    # Print completion message
    print_next_steps()

if __name__ == '__main__':
    main()
