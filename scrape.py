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

    try:
        # Use the async version with a manual event loop
        result = None

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
                    # Launch browser
                    browser = p.chromium.launch(headless=True)
                    
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
                    import requests
                    print("Using requests as last-resort fallback...")
                    response = requests.get(website, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    })
                    response.raise_for_status()
                    result = response.text
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
        
        return f"""<p>Failed to scrape the website: {error_msg}</p>
        <p>System info: {system_info}</p>
        <p>Try installing the required dependencies with: pip install playwright==1.41.0 && python -m playwright install</p>
        """

async def async_scrape_website(website):
    """Async version of website scraping"""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        
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
    # Create a temporary Python script
    script_content = f"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto("{website}", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            await browser.close()
            return content
        except Exception as e:
            print(f"Error in subprocess: {{e}}", file=sys.stderr)
            await browser.close()
            return "<p>Error: {{e}}</p>"

if __name__ == "__main__":
    content = asyncio.run(main())
    print(content)
    """
    
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "scrape_script.py")
    
    try:
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Run the script in a subprocess
        result = subprocess.check_output([sys.executable, script_path], text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {e}")
        return f"<p>Error in subprocess: {e}</p>"
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

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
