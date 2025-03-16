from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup
import re
import platform
import os
import subprocess
import sys
import tempfile
import shutil
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import traceback

def auto_setup_playwright():
    """Automatically set up Playwright dependencies if needed"""
    # Only run this on Streamlit Cloud
    if not ('STREAMLIT_SHARING' in os.environ or 'STREAMLIT_CLOUD' in os.environ):
        print("Not running on Streamlit Cloud, skipping auto-setup")
        return
        
    print("Running on Streamlit Cloud, checking Playwright setup...")
    
    # Check if Playwright browsers are installed
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--help"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print("Playwright CLI not working correctly, trying to reinstall")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--force-reinstall", "playwright==1.41.0"],
                check=False
            )
    except Exception as e:
        print(f"Error checking Playwright installation: {e}")
    
    # Try to install the browsers silently
    try:
        print("Attempting to install Playwright browsers...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if "Browser downloaded successfully" in result.stdout:
            print("Successfully installed Playwright Chromium browser")
        else:
            print("Playwright browser installation output:")
            print(result.stdout)
            print(result.stderr)
            
    except Exception as e:
        print(f"Error installing Playwright browsers: {e}")
        # Don't fail if we can't install, we'll fall back to requests

# Run auto-setup at import time
try:
    auto_setup_playwright()
except Exception as setup_error:
    print(f"Auto-setup failed but continuing anyway: {setup_error}")

def detect_environment():
    """Detect the current environment and provide diagnostic information"""
    env_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "is_streamlit_cloud": 'STREAMLIT_SHARING' in os.environ or 'STREAMLIT_CLOUD' in os.environ,
        "temp_dir_writable": os.access(tempfile.gettempdir(), os.W_OK),
        "home_dir_writable": os.access(os.path.expanduser("~"), os.W_OK),
        "cwd": os.getcwd(),
        "cwd_writable": os.access(os.getcwd(), os.W_OK)
    }
    
    # Check for Playwright installation
    try:
        subprocess.run([sys.executable, "-m", "playwright", "--version"], 
                       capture_output=True, text=True, check=False)
        env_info["playwright_installed"] = True
    except (subprocess.SubprocessError, FileNotFoundError):
        env_info["playwright_installed"] = False
    
    # Print environment info
    print("\n=== Environment Information ===")
    for key, value in env_info.items():
        print(f"{key}: {value}")
    print("=============================\n")
    
    return env_info

# Run environment detection at module import time
ENV_INFO = detect_environment()

def scrape_website(website):
    """Scrape a website using Playwright"""
    print("Starting Playwright browser...")

    # Check if the website URL is valid
    if not website or website.strip() == "":
        return "<p>Please enter a valid URL</p>"
    
    # Make sure URL has http:// or https:// prefix
    if not re.match(r'^https?://', website):
        website = 'https://' + website
    
    # Ensure the URL is properly formatted
    try:
        print(f"Attempting to scrape: {website}")
    except Exception as e:
        print(f"URL validation error: {e}")
        return f"<p>Invalid URL: {website}</p>"

    # Check if we're on Streamlit Cloud
    is_streamlit_cloud = ENV_INFO["is_streamlit_cloud"]
    if is_streamlit_cloud:
        print("Detected Streamlit Cloud environment - using optimized method")
        
        # On Streamlit Cloud, try the pure requests method first
        # as it has the highest chance of working
        print("Trying pure requests method first (most reliable on Streamlit Cloud)")
        result = pure_requests_fallback(website)
        if result and not result.startswith("<p>All scraping methods failed"):
            return result
    
    try:
        # Use the async version with a manual event loop
        result = None

        # For Streamlit Cloud: Try direct requests first as it's most reliable there
        if is_streamlit_cloud:
            try:
                import requests
                print("Using direct requests method for Streamlit Cloud")
                response = requests.get(website, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                response.raise_for_status()
                result = response.text
                print("Direct requests method successful")
            except Exception as e:
                print(f"Direct requests method failed: {e}")
                print("Falling back to subprocess method...")
                # Continue to the normal methods

        if result is None:
            try:
                # For Python 3.12+ compatibility
                if sys.version_info.major == 3 and sys.version_info.minor >= 12:
                    # Different approach for Python 3.12+
                    print("Using Python 3.12+ compatible mode for Playwright")
                    result = run_in_subprocess(website)
                else:
                    # Normal approach for Python 3.11 and below
                    result = asyncio.run(async_scrape_website(website))
            except Exception as e:
                print(f"Error with asyncio approach: {e}")
                print("Trying sync Playwright as fallback...")
                
                # Fallback to sync API
                try:
                    with sync_playwright() as p:
                        # Launch browser with appropriate arguments
                        browser_args = []
                        if is_streamlit_cloud:
                            browser_args.extend([
                                '--no-sandbox',
                                '--disable-dev-shm-usage',
                                '--disable-gpu',
                                '--disable-setuid-sandbox'
                            ])
                        
                        # Launch browser
                        browser = p.chromium.launch(headless=True, args=browser_args)
                        
                        # Create a context
                        context = browser.new_context()
                        
                        # Create a new page
                        page = context.new_page()
                        
                        # Navigate to the website
                        page.goto(website, wait_until="domcontentloaded", timeout=60000)
                        
                        # Wait a bit for dynamic content
                        page.wait_for_timeout(3000)
                        
                        # Get the page content
                        result = page.content()
                        
                        # Close the browser
                        browser.close()
                except Exception as e2:
                    print(f"Sync Playwright also failed: {e2}")
                    # Try one more alternative method - requests with BeautifulSoup
                    try:
                        print("Using requests as last-resort fallback...")
                        result = pure_requests_fallback(website)
                    except Exception as e3:
                        print(f"All scraping methods failed: {e3}")
                        return f"<p>Failed to scrape the website after multiple attempts. Please check your Python version (3.12 has known issues with Playwright) and try installing the required dependencies with: pip install playwright==1.41.0 && python -m playwright install</p>"
        
        if result:
            print("Page loaded successfully")
            
            # Check if content is valid
            if not result or len(result.strip()) < 100:
                print("Warning: Empty or very small HTML content")
                return "<p>Error: Retrieved empty or invalid content from website</p>"
                
            return result
        else:
            return "<p>Failed to retrieve content from the website</p>"
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error with Playwright: {error_msg}")
        system_info = f"Python {sys.version}, OS: {platform.system()} {platform.release()}"
        
        # Final fallback - try pure requests approach
        print("Trying final fallback with pure requests method")
        try:
            return pure_requests_fallback(website)
        except Exception as req_err:
            print(f"Pure requests final fallback also failed: {req_err}")
        
        return f"""<p>Failed to scrape the website: {error_msg}</p>
        <p>System info: {system_info}</p>
        <p>Try installing the required dependencies with: pip install playwright==1.41.0 && python -m playwright install</p>
        """

async def async_scrape_website(website):
    """Async version of website scraping"""
    # Check if we're on Streamlit Cloud
    is_streamlit_cloud = 'STREAMLIT_SHARING' in os.environ or 'STREAMLIT_CLOUD' in os.environ
    
    async with async_playwright() as p:
        # Set browser arguments for cloud environment
        browser_args = []
        if is_streamlit_cloud:
            browser_args.extend([
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-setuid-sandbox'
            ])
            print("Using Streamlit Cloud specific browser arguments")
        
        try:
            # Launch browser
            print("Launching Chromium browser...")
            browser = await p.chromium.launch(headless=True, args=browser_args)
        except Exception as e:
            print(f"Failed to launch Chromium: {e}")
            if is_streamlit_cloud:
                print("Trying Firefox as fallback on Streamlit Cloud...")
                try:
                    browser = await p.firefox.launch(headless=True, args=browser_args)
                except Exception as e2:
                    print(f"Firefox also failed: {e2}")
                    print("Trying Webkit as final browser fallback...")
                    browser = await p.webkit.launch(headless=True, args=browser_args)
            else:
                # Re-raise if not on Streamlit Cloud and no fallback needed
                raise
        
        # Create a context with viewport and user agent
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Create a new page
        page = await context.new_page()
        
        # Set default timeout (60 seconds)
        page.set_default_timeout(60000)
        
        print(f"Navigating to {website}...")
        
        # Go to the website
        response = await page.goto(website, wait_until="domcontentloaded")
        
        if not response or not response.ok:
            status = response.status if response else "unknown"
            status_text = response.status_text if response else "No response"
            print(f"Error loading page: {status} {status_text}")
            await browser.close()
            return f"<p>Failed to load website: HTTP {status} {status_text}</p>"
        
        # Wait for the body to load
        try:
            await page.wait_for_selector('body', timeout=5000)
        except Exception as e:
            print(f"Warning when waiting for body: {e}")
            # Continue anyway
        
        # Additional waiting for dynamic content
        await page.wait_for_timeout(3000)
        
        # Get the page content
        html = await page.content()
        
        # Close the browser
        await browser.close()
        
        print("Page loaded successfully with Playwright async")
        
        return html

def run_in_subprocess(website):
    """Run the scraping in a subprocess for Python 3.12+ compatibility"""
    # Check environment
    is_streamlit_cloud = ENV_INFO["is_streamlit_cloud"]
    if is_streamlit_cloud:
        print("Warning: Using subprocess approach on Streamlit Cloud may have limitations")
        # On Streamlit Cloud, subprocess approach might fail due to restrictions
        # Consider returning pure_requests_fallback result directly
        print("Using a modified subprocess approach for Streamlit Cloud")
    
    # Create a temporary Python script with appropriate headers for environment
    script_content = f"""
import asyncio
from playwright.async_api import async_playwright
import sys
import os
import traceback

# Debugging information
print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Environment variables:", {{'PATH': os.environ.get('PATH', 'Not set'), 'PYTHONPATH': os.environ.get('PYTHONPATH', 'Not set')}})
print("Is Streamlit Cloud:", 'STREAMLIT_SHARING' in os.environ or 'STREAMLIT_CLOUD' in os.environ)

# Import fallback options
try:
    import requests
except ImportError:
    print("Warning: requests module not available for fallback")

async def main():
    try:
        print("Starting Playwright in subprocess...")
        async with async_playwright() as p:
            # Try to launch with more options for Streamlit Cloud
            browser_args = []
            
            # Add special args for Streamlit Cloud
            if 'STREAMLIT_SHARING' in os.environ or 'STREAMLIT_CLOUD' in os.environ:
                browser_args.extend([
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-setuid-sandbox'
                ])
            
            try:
                print("Launching browser with args:", browser_args)
                browser = await p.chromium.launch(headless=True, args=browser_args)
            except Exception as e:
                print(f"Failed to launch Chromium: {{e}}")
                print("Trying Firefox as fallback...")
                try:
                    browser = await p.firefox.launch(headless=True)
                except Exception as e2:
                    print(f"Firefox also failed: {{e2}}")
                    # Last resort - use Webkit
                    print("Trying Webkit as final fallback...")
                    browser = await p.webkit.launch(headless=True)
            
            page = await browser.new_page()
            
            try:
                await page.goto("{website}", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                content = await page.content()
                await browser.close()
                return content
            except Exception as e:
                print(f"Error during page navigation: {{e}}", file=sys.stderr)
                traceback.print_exc()
                await browser.close()
                return "<p>Error during page navigation: {{e}}</p>"
    except Exception as e:
        print(f"Critical error in Playwright subprocess: {{e}}", file=sys.stderr)
        traceback.print_exc()
        
        # Try fallback to requests
        try:
            # Always try to use requests as a fallback
            print("Trying requests fallback in subprocess...")
            import requests
            headers = {{
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }}
            response = requests.get("{website}", headers=headers, timeout=30)
            return response.text
        except Exception as req_e:
            print(f"Requests fallback also failed: {{req_e}}")
            return f"<p>Critical error in Playwright subprocess: {{e}}<br>Requests also failed: {{req_e}}</p>"

# Fallback to a simple requests approach if Playwright fails
def simple_requests_fallback():
    try:
        import requests
        print("Trying simple requests as ultimate fallback")
        response = requests.get("{website}", headers={{
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }})
        return response.text
    except Exception as e:
        print(f"Even requests fallback failed: {{e}}")
        return f"<p>All scraping methods failed, including requests: {{e}}</p>"

if __name__ == "__main__":
    try:
        content = asyncio.run(main())
        print(content)
    except Exception as e:
        print(f"Error running asyncio: {{e}}", file=sys.stderr)
        print(simple_requests_fallback())
    """
    
    # If on Streamlit Cloud and temp directory is not writable, try home directory
    temp_dir = None
    try:
        if is_streamlit_cloud and not ENV_INFO["temp_dir_writable"]:
            print("Temp directory not writable on Streamlit Cloud, trying home directory")
            if ENV_INFO["home_dir_writable"]:
                home_dir = os.path.expanduser("~")
                temp_subdir = os.path.join(home_dir, ".streamlit_scraper_temp")
                os.makedirs(temp_subdir, exist_ok=True)
                temp_dir = temp_subdir
            else:
                print("Home directory also not writable, trying current directory")
                if ENV_INFO["cwd_writable"]:
                    temp_subdir = os.path.join(os.getcwd(), ".streamlit_scraper_temp")
                    os.makedirs(temp_subdir, exist_ok=True)
                    temp_dir = temp_subdir
        
        # Fall back to default tempfile if no custom dir set
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp()
            
        script_path = os.path.join(temp_dir, "scrape_script.py")
        
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Special handling for Streamlit Cloud permissions
        if is_streamlit_cloud:
            try:
                os.chmod(script_path, 0o755)  # Make executable
            except Exception as perm_e:
                print(f"Warning: Could not set script permissions: {perm_e}")
        
        # Run the script in a subprocess with full error output captured
        try:
            result = subprocess.check_output(
                [sys.executable, script_path], 
                text=True,
                stderr=subprocess.STDOUT,  # Capture stderr in the output too
                timeout=120  # Increase timeout for cloud environments
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Subprocess error (code {e.returncode}):")
            print(e.output)  # Print the combined stdout/stderr
            
            # On Streamlit Cloud, always fall back to pure requests if subprocess fails
            if is_streamlit_cloud:
                print("Subprocess failed on Streamlit Cloud - using pure requests fallback")
                return pure_requests_fallback(website)
            
            return f"<p>Error in subprocess: {e.output}</p>"
        except subprocess.TimeoutExpired:
            print("Subprocess timed out after 120 seconds")
            if is_streamlit_cloud:
                print("Timeout on Streamlit Cloud - using pure requests fallback")
                return pure_requests_fallback(website)
            return "<p>Scraping timed out after 120 seconds. The website might be too large or slow to respond.</p>"
    except Exception as outer_e:
        print(f"Error preparing subprocess: {outer_e}")
        
        # On Streamlit Cloud, always fall back to pure requests if anything fails
        if is_streamlit_cloud:
            print("Error in subprocess setup on Streamlit Cloud - using pure requests fallback")
            return pure_requests_fallback(website)
            
        return f"<p>Error preparing subprocess: {outer_e}</p>"
    finally:
        # Clean up
        if temp_dir:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")

def extract_body_content(html_content):
    """Extract the body content from the HTML, preserving DOM structure"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove all script, style tags completely
        for script in soup(["script", "style", "noscript", "iframe"]):
            script.decompose()
        
        # Get the body content
        body = soup.body
        
        if not body:
            print("Warning: No body tag found in HTML")
            # Fall back to the entire document
            return str(soup)
            
        # Convert specific problematic attributes that might contain JS
        for tag in body.find_all(True):
            for attr in list(tag.attrs):
                if attr.startswith('on') or attr in ['href', 'src'] and tag.get(attr, '').startswith('javascript:'):
                    del tag[attr]
        
        return str(body)
    except Exception as e:
        print(f"Error extracting body content: {e}")
        return html_content

def clean_body_content(body_content):
    """Clean the body content to extract text only"""
    try:
        soup = BeautifulSoup(body_content, "html.parser")

        # Remove all non-text elements
        for element in soup(["script", "style", "meta", "link", "svg", "path"]):
            element.decompose()

        # Get text with reasonable spacing
        cleaned_content = soup.get_text(separator="\n", strip=True)
        
        # Clean up multiple newlines and spaces
        cleaned_content = re.sub(r'\n\s*\n', '\n\n', cleaned_content)
        cleaned_content = re.sub(r'[ \t]+', ' ', cleaned_content)
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content.strip()
    except Exception as e:
        print(f"Error cleaning body content: {e}")
        # Return something sensible if parsing fails
        return re.sub(r'<[^>]*>', '', body_content)

def split_dom_content(dom_content, max_length=6000):
    """Split DOM content into manageable chunks for LLM processing"""
    # If content is smaller than max_length, return as a single chunk
    if len(dom_content) <= max_length:
        return [dom_content]
        
    # Find a good splitting strategy for HTML
    chunks = []
    soup = BeautifulSoup(dom_content, 'html.parser')
    
    # Try to split at major section dividers
    dividers = soup.find_all(['div', 'section', 'article', 'main', 'header', 'footer'])
    
    if dividers and len(dividers) > 1:
        # Use major dividers as chunk boundaries
        current_chunk = ""
        for div in dividers:
            div_str = str(div)
            
            # If adding this divider would exceed max_length, save current chunk and start a new one
            if len(current_chunk) + len(div_str) > max_length:
                if current_chunk:  # Only append non-empty chunks
                    chunks.append(current_chunk)
                
                # If the divider itself is too large, split it
                if len(div_str) > max_length:
                    div_chunks = [div_str[i:i+max_length] for i in range(0, len(div_str), max_length)]
                    chunks.extend(div_chunks)
                    current_chunk = ""
                else:
                    current_chunk = div_str
            else:
                current_chunk += div_str
                
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
    else:
        # Fallback: simple character-based splitting
        chunks = [dom_content[i:i+max_length] for i in range(0, len(dom_content), max_length)]
    
    # Ensure all chunks are proper HTML fragments by wrapping in a div if needed
    for i in range(len(chunks)):
        if not chunks[i].strip().startswith('<'):
            chunks[i] = f'<div>{chunks[i]}</div>'
    
    return chunks

def pure_requests_fallback(url):
    """
    A pure requests-based fallback method for scraping
    This should work in even the most restricted environments
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        print("Using pure requests fallback method")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Try with a session to handle cookies
        session = requests.Session()
        
        # Add a retry mechanism
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Make the request
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        
        # Basic validation of HTML content
        if len(html_content) < 100:
            print("Warning: Very short HTML content received")
            return f"<p>Warning: Website returned very little content ({len(html_content)} bytes)</p>"
        
        # Try to make sure we have valid HTML
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            if not soup.body:
                print("Warning: No body tag found in HTML, possibly invalid content")
                return f"<p>Warning: Website returned content without a proper HTML body</p>" + html_content
        except Exception as parse_err:
            print(f"HTML parsing warning: {parse_err}")
            # Continue anyway, return the raw content
        
        print(f"Successfully retrieved content with requests ({len(html_content)} bytes)")
        return html_content
        
    except Exception as e:
        print(f"Pure requests fallback failed: {e}")
        error_details = str(e)
        traceback_str = traceback.format_exc()
        print(f"Traceback: {traceback_str}")
        
        return f"""
        <p>All scraping methods failed. Error details:</p>
        <pre>{error_details}</pre>
        <p>Please verify the URL is correct and accessible.</p>
        """
