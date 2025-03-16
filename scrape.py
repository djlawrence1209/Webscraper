import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
import time
from bs4 import BeautifulSoup
import re
import platform
import os
import subprocess
import tempfile
import shutil
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

def kill_chrome_processes():
    """Terminate any hanging Chrome processes on Windows"""
    # This function has been disabled to prevent closing user's Chrome tabs
    print("Chrome process management disabled to preserve user's browser tabs")
    return

def find_chrome_binary():
    """Find Chrome binary on different systems"""
    # Common Chrome binary locations on different systems
    chrome_paths = [
        # Linux paths
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        # Add Render specific paths
        "/opt/render/project/chrome-bin/chrome",
        "/opt/google/chrome/chrome",
        # Windows paths
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]
    
    # Check if any of the paths exist
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"Chrome binary found at: {path}")
            return path
    
    print("No Chrome binary found in common locations")
    return None

def scrape_website(website):
    print("Launching chrome browser in headless mode...")

    # Check if the website URL is valid
    if not website or website.strip() == "":
        return "<p>Please enter a valid URL</p>"
    
    # Make sure URL has http:// or https:// prefix
    if not re.match(r'^https?://', website):
        website = 'https://' + website
    
    # Ensure the URL is properly formatted
    try:
        # Additional validation could be added here if needed
        print(f"Attempting to scrape: {website}")
    except Exception as e:
        print(f"URL validation error: {e}")
        return f"<p>Invalid URL: {website}</p>"

    # Create a temporary directory for Chrome data
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="chrome_scraper_")
        print(f"Created temporary directory for Chrome: {temp_dir}")
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")  # Use newer headless mode
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Use temporary directory for Chrome data
        options.add_argument(f"--user-data-dir={temp_dir}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Check if running on Render or other cloud platform
        if os.environ.get('RENDER') or os.environ.get('DYNO'):
            print("Running on cloud platform, using special configuration")
            options.add_argument("--disable-infobars")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--remote-debugging-port=9222")
            
            # Find Chrome binary
            chrome_binary = find_chrome_binary()
            if chrome_binary:
                print(f"Setting Chrome binary to: {chrome_binary}")
                options.binary_location = chrome_binary
            else:
                print("WARNING: No Chrome binary found. This may cause issues.")
        
        print("Setting up Chrome driver with webdriver-manager...")
        if platform.system() == "Windows":
            # Windows-specific setup
            print("Using Windows-specific Chrome setup")
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
        else:
            # Linux/Mac setup
            print("Using Linux/Mac Chrome setup")
            try:
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                    options=options
                )
            except Exception as e:
                print(f"Failed to use ChromeDriverManager: {e}")
                print("Trying direct ChromeDriver path...")
                
                # Try to use ChromeDriver directly if webdriver_manager fails
                chromedriver_path = "/usr/local/bin/chromedriver"
                if os.path.exists(chromedriver_path):
                    print(f"Using ChromeDriver at: {chromedriver_path}")
                    driver = webdriver.Chrome(
                        service=Service(chromedriver_path),
                        options=options
                    )
                else:
                    raise Exception(f"ChromeDriver not found at {chromedriver_path}")
        
        # Set page load timeout to avoid hanging
        driver.set_page_load_timeout(30)
        
        try:
            print(f"Navigating to {website}...")
            driver.get(website)
            print("Page loaded successfully")
            time.sleep(5)  # Reduced wait time
            html = driver.page_source
            return html
        except Exception as e:
            print(f"Error during page load: {e}")
            return f"<p>Failed to load the website: {str(e)}</p>"
        finally:
            print("Closing Chrome driver...")
            driver.quit()
            
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        error_msg = str(e)
        
        # Cloud platform specific troubleshooting
        if os.environ.get('RENDER') or os.environ.get('DYNO'):
            # Get a list of available packages and binaries to help diagnose
            try:
                print("Checking system for Chrome installation:")
                if os.path.exists("/usr/bin"):
                    print("Contents of /usr/bin (grep chrome):")
                    os.system("ls -la /usr/bin | grep -i chrome")
                
                print("Checking installed packages:")
                os.system("apt list --installed | grep -i chrome")
                
                print("Checking for Chromium:")
                os.system("which chromium-browser")
            except:
                pass
                
            return f"""<p>Failed to initialize Chrome browser on cloud platform: {error_msg}</p>
            <p>This appears to be a server-side issue with Chrome configuration.</p>
            """
        
        # Windows-specific troubleshooting suggestions
        elif platform.system() == "Windows":
            return f"""<p>Failed to initialize Chrome browser: {error_msg}</p>
            <p>Try these troubleshooting steps:</p>
            <ol>
                <li>Make sure Chrome is up-to-date (currently using {get_chrome_version() or 'unknown version'})</li>
                <li>Close any Chrome windows that might be interfering</li>
                <li>Check your antivirus isn't blocking Chrome automation</li>
                <li>Try restarting the application</li>
            </ol>
            """
        else:
            return f"<p>Failed to initialize browser: {error_msg}</p>"
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Removed temporary Chrome directory: {temp_dir}")
            except Exception as e:
                print(f"Failed to remove temporary directory: {e}")

def get_chrome_version():
    """Get the installed Chrome version"""
    try:
        if platform.system() == "Windows":
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_path):
                result = subprocess.run([chrome_path, "--version"], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE,
                                       creationflags=subprocess.CREATE_NO_WINDOW,
                                       timeout=1)
                return result.stdout.decode().strip()
        return None
    except:
        return None

def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    body_content = soup.body
    return str(body_content) if body_content else ""

def clean_body_content(body_content):
    soup = BeautifulSoup(body_content, "html.parser")

    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()

    cleaned_content = soup.get_text(separator="\n")
    cleaned_content = "\n".join(line.strip() for line in cleaned_content.splitlines() if line.strip())

    return cleaned_content

def split_dom_content(dom_content, max_length=6000):
    return [dom_content[i : i + max_length] for i in range(0, len(dom_content), max_length)]
