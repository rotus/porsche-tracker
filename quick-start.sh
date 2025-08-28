#!/bin/bash

# Porsche Tracker Quick Start Script
# This script will set up and run the Porsche tracking application

echo "🏎️  Porsche Tracker Quick Start"
echo "================================"

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "🔧 Setting up for the first time..."
    python3 setup.py
fi

# Activate virtual environment
echo "🚀 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists and has been configured
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run setup.py first."
    exit 1
fi

# Check if email is configured
if grep -q "your_email@gmail.com" .env; then
    echo "⚠️  Email not configured in .env file"
    echo "   Edit .env and add your Gmail credentials for notifications"
    echo "   Press Enter to continue anyway, or Ctrl+C to exit and configure first"
    read
fi

# Start the application
echo "🌟 Starting Porsche Tracker..."
echo "   Open http://localhost:5000 in your browser"
echo "   Press Ctrl+C to stop the application"
echo ""

python app.py dev
