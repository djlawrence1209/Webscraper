#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting build process..."

# Detect if running on Render
if [ -n "$RENDER" ]; then
    echo "Running on Render platform with read-only filesystem"
    
    # Check for Chrome/Chromium binaries - we rely on packages in render.yaml
    echo "Checking for installed browsers:"
    
    # List available browsers
    echo "Available browsers:"
    which google-chrome google-chrome-stable chromium chromium-browser 2>/dev/null || echo "No browsers found in PATH"
    
    # Check common locations
    for browser_path in /usr/bin/google-chrome /usr/bin/google-chrome-stable /usr/bin/chromium /usr/bin/chromium-browser; do
        if [ -f "$browser_path" ]; then
            echo "Found browser at: $browser_path"
            echo "Version: $($browser_path --version 2>/dev/null || echo 'Unknown')"
        fi
    done
    
    # Check for ChromeDriver
    echo "Checking for ChromeDriver:"
    which chromedriver 2>/dev/null && chromedriver --version || echo "ChromeDriver not found in PATH"
    
    # Create directory for ChromeDriver if needed (in a writable location)
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    
    # Download ChromeDriver to a writable location if not already present
    if ! which chromedriver >/dev/null; then
        echo "ChromeDriver not found, downloading to $LOCAL_BIN..."
        
        # Default to a stable version that works with most Chrome versions
        CHROMEDRIVER_VERSION="114.0.5735.90"
        
        # Download and install ChromeDriver to user directory
        wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
        unzip -q chromedriver_linux64.zip
        chmod +x chromedriver
        mv chromedriver "$LOCAL_BIN/"
        rm chromedriver_linux64.zip
        
        # Add to PATH
        export PATH="$LOCAL_BIN:$PATH"
        
        echo "ChromeDriver installed to $LOCAL_BIN/chromedriver"
        echo "ChromeDriver version: $(chromedriver --version 2>/dev/null || echo 'Unknown')"
    fi
else
    echo "Not running on Render, skipping browser checks"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Build completed successfully!" 