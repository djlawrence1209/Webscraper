import subprocess
import sys
import os

def install_playwright_browsers():
    """Install Playwright browsers for the application"""
    try:
        print("Checking for Playwright browsers...")
        
        # Always install Chromium browser for Playwright
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("Playwright Chromium browser installed successfully")
        except Exception as e:
            print(f"Error installing Playwright Chromium: {e}")
            print("Trying alternative installation method...")
            
            # Try installing with pip if direct method fails
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                print("Playwright installed and Chromium browser installed via pip")
            except Exception as e2:
                print(f"Failed to install Playwright browsers: {e2}")
                print("You may need to manually install Playwright browsers with:")
                print("  python -m playwright install chromium")
                
    except Exception as e:
        print(f"Error during Playwright setup: {e}")

if __name__ == "__main__":
    install_playwright_browsers() 