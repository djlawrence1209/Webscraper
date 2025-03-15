import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
import time
from bs4 import BeautifulSoup
import re

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

    chrome_driver_path = "./chromedriver.exe"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (no UI)
    options.add_argument("--disable-gpu")  # Disable GPU acceleration (recommended for headless mode)
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resources in some environments

    try:
        driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
        
        # Set page load timeout to avoid hanging
        driver.set_page_load_timeout(30)
        
        try:
            driver.get(website)
            print("Page loaded...")
            time.sleep(10)  # Delay for page loading (consider reducing this)
            html = driver.page_source
            return html
        except Exception as e:
            print(f"Error during page load: {e}")
            return f"<p>Failed to load the website: {str(e)}</p>"
        finally:
            driver.quit()
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return f"<p>Failed to initialize browser: {str(e)}</p>"

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
