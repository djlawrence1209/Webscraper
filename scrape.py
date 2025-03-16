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
import sys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import streamlit as st

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
    
    # Try using which command on Linux/Mac
    if platform.system() != "Windows":
        try:
            which_chrome = subprocess.check_output(["which", "google-chrome"], stderr=subprocess.STDOUT).decode().strip()
            if which_chrome:
                print(f"Chrome binary found using 'which': {which_chrome}")
                return which_chrome
        except:
            pass
        
        try:
            which_chromium = subprocess.check_output(["which", "chromium-browser"], stderr=subprocess.STDOUT).decode().strip()
            if which_chromium:
                print(f"Chromium binary found using 'which': {which_chromium}")
                return which_chromium
        except:
            pass
    
    print("No Chrome binary found in common locations")
    return None

def find_chromedriver():
    """Find ChromeDriver binary"""
    # Check in PATH first
    try:
        if platform.system() == "Windows":
            which_cmd = "where"
        else:
            which_cmd = "which"
        
        driver_path = subprocess.check_output([which_cmd, "chromedriver"], stderr=subprocess.STDOUT).decode().strip()
        if driver_path:
            print(f"ChromeDriver found in PATH: {driver_path}")
            return driver_path
    except Exception as e:
        print(f"Error finding ChromeDriver in PATH: {e}")
    
    # Check common locations
    driver_paths = [
        # Docker container location
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
        # Custom location for Render
        os.path.expanduser("~/.local/bin/chromedriver"),
        # Standard locations
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
    ]
    
    for path in driver_paths:
        if os.path.exists(path):
            print(f"ChromeDriver found at: {path}")
            return path
    
    print("No ChromeDriver found in common locations")
    return None

def is_streamlit_cloud():
    """Check if running on Streamlit Cloud"""
    return "STREAMLIT_SHARING" in os.environ or "STREAMLIT_CLOUD" in os.environ

def download_chromedriver_if_needed():
    """Attempt to download and install ChromeDriver if not found"""
    if platform.system() == "Windows":
        return None  # We'll use ChromeDriverManager on Windows
    
    # Streamlit Cloud has restrictions on writing to certain directories
    if is_streamlit_cloud():
        try:
            return ChromeDriverManager().install()
        except Exception as e:
            print(f"Error using ChromeDriverManager on Streamlit Cloud: {e}")
            return None
    
    try:
        # First check if we already have ChromeDriver
        existing_driver = find_chromedriver()
        if existing_driver:
            return existing_driver
            
        print("Attempting to download ChromeDriver...")
        
        # Get Chrome version
        chrome_binary = find_chrome_binary()
        if not chrome_binary:
            print("Cannot download ChromeDriver: Chrome binary not found")
            return None
            
        chrome_version_cmd = f"{chrome_binary} --version"
        chrome_version_output = subprocess.check_output(chrome_version_cmd, shell=True).decode()
        chrome_version = chrome_version_output.split()[2].split('.')[0]  # Get major version
        
        print(f"Detected Chrome version: {chrome_version}")
        
        # Create a directory for ChromeDriver
        driver_dir = os.path.expanduser("~/.local/bin")
        os.makedirs(driver_dir, exist_ok=True)
        
        # Get latest ChromeDriver version for this Chrome version
        try:
            version_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{chrome_version}"
            chromedriver_version = subprocess.check_output(f"curl -s {version_url}", shell=True).decode().strip()
        except:
            # Fallback to a known working version if version detection fails
            chromedriver_version = "114.0.5735.90"
            print(f"Version detection failed, using fallback version: {chromedriver_version}")
        
        print(f"Using ChromeDriver version: {chromedriver_version}")
        
        # Download and install ChromeDriver
        download_url = f"https://chromedriver.storage.googleapis.com/{chromedriver_version}/chromedriver_linux64.zip"
        driver_path = os.path.join(driver_dir, "chromedriver")
        
        subprocess.check_call(f"wget -q -O /tmp/chromedriver.zip {download_url}", shell=True)
        subprocess.check_call("unzip -o /tmp/chromedriver.zip -d /tmp", shell=True)
        subprocess.check_call(f"mv /tmp/chromedriver {driver_path}", shell=True)
        subprocess.check_call(f"chmod +x {driver_path}", shell=True)
        
        print(f"ChromeDriver installed to {driver_path}")
        return driver_path
    except Exception as e:
        print(f"Error downloading ChromeDriver: {e}")
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
        # Use a more reliable temp dir approach for Streamlit Cloud
        if is_streamlit_cloud():
            # Streamlit Cloud may have restrictions on certain temp directories
            temp_dir = os.path.join(os.path.expanduser("~"), ".streamlit_chrome_temp")
            os.makedirs(temp_dir, exist_ok=True)
        else:
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
        
        # Add more options that help with Streamlit Cloud
        options.add_argument('--disable-features=NetworkService')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-breakpad')
        options.add_argument('--disable-infobars')
        options.add_argument('--ignore-certificate-errors')
        
        # Check if running on Render, Streamlit Cloud or other cloud platform
        if os.environ.get('RENDER') or os.environ.get('DYNO') or is_streamlit_cloud():
            print("Running on cloud platform, using special configuration")
            options.add_argument("--single-process")  # Important for resource-constrained environments
            
            # Find Chrome binary
            chrome_binary = find_chrome_binary()
            if chrome_binary:
                print(f"Setting Chrome binary to: {chrome_binary}")
                options.binary_location = chrome_binary
            else:
                print("WARNING: No Chrome binary found. This may cause issues.")

            # Add directory with ChromeDriver to PATH if in Render
            local_bin = os.path.expanduser("~/.local/bin")
            if os.path.exists(local_bin):
                os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
                print(f"Added {local_bin} to PATH")
        
        print("Setting up Chrome driver...")
        
        # Get ChromeDriver path - Try different methods
        chromedriver_path = None
        
        # Special handling for Streamlit Cloud
        if is_streamlit_cloud():
            print("Running on Streamlit Cloud")
            try:
                # Try to use ChromeDriverManager which should work on Streamlit Cloud
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )
            except Exception as e:
                print(f"Failed with ChromeDriverManager: {e}")
                # Last resort: Let Selenium try to find it
                driver = webdriver.Chrome(options=options)
                
        # For Docker environment, check if we need to download ChromeDriver
        elif os.environ.get('RENDER_ENV_IS_DOCKER'):
            print("Running in Docker environment")
            # Try to find existing ChromeDriver
            chromedriver_path = find_chromedriver()
            
            if not chromedriver_path:
                # If not found, try to download it
                print("ChromeDriver not found in expected locations, attempting to download...")
                chromedriver_path = download_chromedriver_if_needed()
                
            if chromedriver_path:
                print(f"Using ChromeDriver at: {chromedriver_path}")
                driver = webdriver.Chrome(
                    service=Service(chromedriver_path),
                    options=options
                )
            else:
                # Last resort: Let Selenium try to find it
                print("Using Selenium WebDriver without explicit ChromeDriver path")
                driver = webdriver.Chrome(options=options)
                
        elif platform.system() == "Windows":
            # Windows-specific setup
            print("Using Windows-specific Chrome setup")
            try:
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )
            except Exception as e:
                print(f"Failed with ChromeDriverManager: {e}")
                # Fallback to found driver
                chromedriver_path = find_chromedriver()
                if chromedriver_path:
                    driver = webdriver.Chrome(
                        service=Service(chromedriver_path),
                        options=options
                    )
                else:
                    raise e
        else:
            # Linux/Mac setup
            print("Using Linux/Mac Chrome setup")
            chromedriver_path = find_chromedriver()
            if chromedriver_path:
                print(f"Using ChromeDriver at: {chromedriver_path}")
                driver = webdriver.Chrome(
                    service=Service(chromedriver_path),
                    options=options
                )
            else:
                try:
                    driver = webdriver.Chrome(
                        service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                        options=options
                    )
                except Exception as e:
                    # Provide more context about the error
                    error_details = str(e)
                    system_details = f"Python {sys.version}, OS: {platform.system()} {platform.release()}"
                    raise Exception(f"{error_details}\nSystem info: {system_details}")
        
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
        
        # Check if running on Streamlit Cloud
        if is_streamlit_cloud():
            system_info = f"Python {sys.version}, Platform: {platform.platform()}"
            environment_vars = "\n".join([f"{k}={v}" for k, v in os.environ.items() if k.startswith(("CHROME", "PATH", "STREAMLIT"))])
            
            # Create a more user-friendly error message for Streamlit Cloud
            return f"""<p>Failed to initialize Chrome browser on Streamlit Cloud: {error_msg}</p>
            <p>This may be due to Streamlit Cloud's limitations with Selenium.</p>
            <details>
                <summary>Technical Details (click to expand)</summary>
                <pre>{system_info}\n\n{environment_vars}</pre>
            </details>
            <p>Consider trying the app locally or on another hosting platform like Render.</p>
            """
            
        # Cloud platform specific troubleshooting
        elif os.environ.get('RENDER') or os.environ.get('DYNO'):
            # Get system information to help diagnose
            system_info = f"Python {sys.version}, Platform: {platform.platform()}"
            environment_vars = "\n".join([f"{k}={v}" for k, v in os.environ.items() if k.startswith(("CHROME", "PATH", "RENDER"))])
            
            # Try to get some diagnostic info
            diagnostics = []
            try:
                diagnostics.append(f"PATH: {os.environ.get('PATH', 'Not set')}")
                
                if os.path.exists("/usr/bin"):
                    chrome_bins = subprocess.check_output("find /usr/bin -name '*chrome*' 2>/dev/null || true", shell=True).decode()
                    diagnostics.append(f"Chrome binaries in /usr/bin: {chrome_bins}")
                
                chromium_location = subprocess.check_output("which chromium-browser 2>/dev/null || echo 'Not found'", shell=True).decode().strip()
                diagnostics.append(f"Chromium location: {chromium_location}")
                
                # Check installed ChromeDriver version
                try:
                    chromedriver_version = subprocess.check_output("chromedriver --version 2>/dev/null || echo 'Not found'", shell=True).decode().strip()
                    diagnostics.append(f"ChromeDriver version: {chromedriver_version}")
                except:
                    diagnostics.append("Could not determine ChromeDriver version")
                    
                # Check if Docker-installed ChromeDriver exists
                if os.path.exists("/usr/local/bin/chromedriver"):
                    try:
                        docker_driver_version = subprocess.check_output("/usr/local/bin/chromedriver --version 2>/dev/null || echo 'Not executable'", shell=True).decode().strip()
                        diagnostics.append(f"Docker ChromeDriver version: {docker_driver_version}")
                        
                        # Check permissions
                        chromedriver_perms = subprocess.check_output("ls -la /usr/local/bin/chromedriver", shell=True).decode().strip()
                        diagnostics.append(f"ChromeDriver permissions: {chromedriver_perms}")
                    except Exception as e:
                        diagnostics.append(f"Error checking Docker ChromeDriver: {e}")
                else:
                    diagnostics.append("Docker ChromeDriver not found at /usr/local/bin/chromedriver")
                    
                # Check if we can write to ~/.local/bin
                local_bin = os.path.expanduser("~/.local/bin")
                try:
                    os.makedirs(local_bin, exist_ok=True)
                    with open(f"{local_bin}/test.txt", "w") as f:
                        f.write("test")
                    os.remove(f"{local_bin}/test.txt")
                    diagnostics.append(f"Can write to {local_bin}: Yes")
                except Exception as e:
                    diagnostics.append(f"Can write to {local_bin}: No - {e}")
                    
                # Try to list all chrome/driver related files
                try:
                    find_result = subprocess.check_output("find / -name '*chromedriver*' -o -name '*chrome*' 2>/dev/null | grep -v 'lib\\|share\\|man'", shell=True).decode()
                    diagnostics.append(f"Chrome/ChromeDriver related files:\n{find_result}")
                except:
                    pass
                    
            except Exception as e:
                diagnostics.append(f"Failed to collect diagnostic information: {e}")
            
            diagnostic_info = "\n".join(diagnostics)
                
            return f"""<p>Failed to initialize Chrome browser on cloud platform: {error_msg}</p>
            <p>This appears to be a server-side issue with Chrome configuration.</p>
            <details>
                <summary>Technical Details (click to expand)</summary>
                <pre>{system_info}\n\n{environment_vars}\n\n{diagnostic_info}</pre>
            </details>
            <p>You can also try running the scraper on your local machine as a workaround.</p>
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
        if temp_dir and os.path.exists(temp_dir) and not is_streamlit_cloud():
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
