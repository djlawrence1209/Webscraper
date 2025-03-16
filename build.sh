#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting build process..."

# Detect if running on Render
if [ -n "$RENDER" ]; then
    echo "Running on Render platform"
    
    # Update package lists
    echo "Updating package lists..."
    apt-get update
    
    # Install required dependencies
    echo "Installing dependencies..."
    apt-get install -y wget curl unzip apt-transport-https ca-certificates gnupg
    
    # Try multiple methods to install Chrome
    
    # Method 1: Using Google's repository
    echo "Adding Google Chrome repository..."
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
    apt-get update
    
    echo "Installing Google Chrome..."
    apt-get install -y google-chrome-stable
    
    # Create a symbolic link to ensure Chrome is found in common locations
    if [ -f "/usr/bin/google-chrome-stable" ] && [ ! -f "/usr/bin/google-chrome" ]; then
        echo "Creating symbolic link to google-chrome..."
        ln -s /usr/bin/google-chrome-stable /usr/bin/google-chrome
    fi
    
    # Method 2: Direct download as fallback
    if [ ! -f "/usr/bin/google-chrome" ] && [ ! -f "/usr/bin/google-chrome-stable" ]; then
        echo "Google Chrome not found after apt install, trying direct download..."
        CHROME_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
        wget -q $CHROME_URL
        dpkg -i google-chrome-stable_current_amd64.deb || true
        apt-get install -y -f  # Fix any dependency issues
        rm google-chrome-stable_current_amd64.deb
    fi
    
    # Method 3: Use Chromium as fallback
    if [ ! -f "/usr/bin/google-chrome" ] && [ ! -f "/usr/bin/google-chrome-stable" ]; then
        echo "Google Chrome installation failed, trying Chromium instead..."
        apt-get install -y chromium-browser
        
        # Create a symbolic link so our code can find it
        if [ -f "/usr/bin/chromium-browser" ] && [ ! -f "/usr/bin/google-chrome" ]; then
            ln -s /usr/bin/chromium-browser /usr/bin/google-chrome
        fi
    fi
    
    # Check if we have Chrome/Chromium installed
    if [ -f "/usr/bin/google-chrome" ]; then
        echo "✅ Chrome/Chromium installation successful"
        echo "Chrome version: $(/usr/bin/google-chrome --version)"
    else
        echo "❌ Failed to install Chrome or Chromium!"
        echo "Available browsers:"
        find /usr/bin -name "*chrome*" || true
        find /usr/bin -name "*chromium*" || true
    fi
    
    # Set up ChromeDriver
    echo "Setting up ChromeDriver..."
    CHROME_VERSION=$(/usr/bin/google-chrome --version 2>/dev/null | awk '{print $3}' | cut -d '.' -f 1 || echo "110")
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION" || echo "110.0.5481.77")
    
    echo "Downloading ChromeDriver version $CHROMEDRIVER_VERSION..."
    wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
    unzip -q chromedriver_linux64.zip
    chmod +x chromedriver
    mv chromedriver /usr/local/bin/
    rm chromedriver_linux64.zip
    
    echo "ChromeDriver version: $(chromedriver --version)"
else
    echo "Not running on Render, skipping Chrome installation"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Build completed successfully!" 