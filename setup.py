import subprocess
import sys
import os

def install_playwright_browsers():
    """Install Playwright browsers when running on Streamlit Cloud"""
    try:
        # Check if we're running on Streamlit Cloud
        if "STREAMLIT_SHARING" in os.environ or "STREAMLIT_CLOUD" in os.environ:
            print("Running on Streamlit Cloud, installing Playwright browsers...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("Playwright browsers installed successfully")
        else:
            print("Not running on Streamlit Cloud, skipping Playwright browsers installation")
    except Exception as e:
        print(f"Error installing Playwright browsers: {e}")

if __name__ == "__main__":
    install_playwright_browsers() 