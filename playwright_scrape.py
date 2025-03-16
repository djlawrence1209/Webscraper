import asyncio
from playwright.async_api import async_playwright
import platform
import os
import sys
import tempfile
import shutil
from bs4 import BeautifulSoup
import re

async def scrape_with_playwright(website):
    """Scrape a website using Playwright (works on Streamlit Cloud)"""
    print("Starting Playwright browser...")
    
    # Check if the website URL is valid
    if not website or website.strip() == "":
        return "<p>Please enter a valid URL</p>"
    
    # Make sure URL has http:// or https:// prefix
    if not re.match(r'^https?://', website):
        website = 'https://' + website
    
    try:
        # Initialize Playwright
        async with async_playwright() as p:
            # Launch browser (chromium works better than firefox on Streamlit Cloud)
            browser = await p.chromium.launch(headless=True)
            
            # Set browser context with viewport and user agent
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Create a new page and navigate to the URL
            print(f"Navigating to {website}...")
            page = await context.new_page()
            
            # Set timeout to 30 seconds
            page.set_default_timeout(30000)
            
            # Navigate to the URL
            response = await page.goto(website, wait_until="domcontentloaded")
            
            if not response.ok:
                print(f"Error loading page: {response.status} {response.status_text}")
                await browser.close()
                return f"<p>Failed to load website: HTTP {response.status} {response.status_text}</p>"
                
            # Wait for content to load - dynamic content needs more time
            try:
                # Wait for the main content to be available
                await page.wait_for_selector('body', timeout=5000)
            except Exception as e:
                print(f"Warning when waiting for body: {e}")
                # Continue anyway - we might have partial content
            
            # Perform additional wait for dynamic content
            await asyncio.sleep(3)
            
            # Get the page content
            html = await page.content()
            
            # Additional processing: Wait for images (optional)
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception as e:
                print(f"Network idle timeout (expected): {e}")
                # This is expected, no need to handle
            
            # Close the browser
            await browser.close()
            
            print("Page loaded successfully with Playwright")
            
            # Check if content is valid
            if not html or len(html.strip()) < 100:
                print("Warning: Empty or very small HTML content")
                return "<p>Error: Retrieved empty or invalid content from website</p>"
                
            return html
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error with Playwright: {error_msg}")
        system_info = f"Python {sys.version}, OS: {platform.system()} {platform.release()}"
        
        return f"""<p>Failed to scrape the website using Playwright: {error_msg}</p>
        <p>System info: {system_info}</p>
        """

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

# Function to run the async scraper
def scrape_website_playwright(website):
    """Synchronous wrapper for the async scraping function"""
    return asyncio.run(scrape_with_playwright(website)) 