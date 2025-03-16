import streamlit as st
import platform
import os
import subprocess
import sys

# Run the setup script to install Playwright browsers
try:
    from setup import install_playwright_browsers
    install_playwright_browsers()
except ImportError:
    pass

# Import from scrape.py (Selenium based)
from scrape import (
    scrape_website as scrape_with_selenium, 
    extract_body_content, 
    clean_body_content, 
    split_dom_content
)

# Import from playwright_scrape.py (Playwright based - works on Streamlit Cloud)
try:
    from playwright_scrape import scrape_website_playwright
    playwright_available = True
except ImportError:
    playwright_available = False

# Import parsing functions
from parse import parse_with_ollama

# Page config  
st.set_page_config(page_title="AI Web Scraper", page_icon="🔍", layout="wide")

# Check if running on Streamlit Cloud
def is_streamlit_cloud():
    return "STREAMLIT_SHARING" in os.environ or "STREAMLIT_CLOUD" in os.environ

# Check if Chrome is installed
def is_chrome_installed():
    if is_streamlit_cloud():
        # On Streamlit Cloud, assume Chrome is not properly installed for Selenium
        return False
    elif platform.system() == "Windows":
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        return os.path.exists(chrome_path)
    else:
        # Linux/Mac
        try:
            result = subprocess.run(["which", "google-chrome"], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
            return result.returncode == 0
        except:
            return False

# Title
st.title("AI Web Scraper")

# Choose the appropriate scraper based on environment
def scrape_website(url):
    if is_streamlit_cloud() and playwright_available:
        st.info("Using Playwright for web scraping (Streamlit Cloud compatible)")
        return scrape_website_playwright(url)
    else:
        return scrape_with_selenium(url)

# Display warning if on Streamlit Cloud
if is_streamlit_cloud():
    if not playwright_available:
        st.warning("Running on Streamlit Cloud without Playwright support. Install 'playwright' package for better compatibility.")
elif not is_chrome_installed():
    st.warning("Google Chrome doesn't appear to be installed on this system.")
    st.info("The web scraper requires Google Chrome to function properly. Please install Chrome and restart the application.")
    st.markdown("[Download Chrome](https://www.google.com/chrome/)")

# Input for website URL
website_url = st.text_input("Enter a Website URL:", "https://djlawrence1209.com/")
st.caption("Example: https://djlawrence1209.com/")

# Store scraped data in session state for persistence
if 'html_content' not in st.session_state:
    st.session_state.html_content = None
if 'cleaned_text' not in st.session_state:
    st.session_state.cleaned_text = None
if 'text_chunks' not in st.session_state:
    st.session_state.text_chunks = None
if 'parsed_result' not in st.session_state:
    st.session_state.parsed_result = None
if 'parsing_in_progress' not in st.session_state:
    st.session_state.parsing_in_progress = False

# Button to scrape website
if st.button("Scrape Site"):
    if is_streamlit_cloud() and not playwright_available:
        st.error("Playwright package is required for scraping on Streamlit Cloud. Please add 'playwright' to your requirements.txt file.")
    else:
        with st.spinner("Scraping website..."):
            html_content = scrape_website(website_url)
            
            # Check if there's an error message
            if html_content.startswith("<p>Failed") or html_content.startswith("<p>Error"):
                st.error(html_content)
            else:
                st.success("Website scraped successfully!")
                
                # Store raw HTML in session state
                st.session_state.html_content = html_content
                
                # Extract and clean the body content
                body_content = extract_body_content(html_content)
                
                # Clean the content for text display and processing
                cleaned_text = clean_body_content(body_content)
                st.session_state.cleaned_text = cleaned_text
                
                # Split the cleaned text for LLM processing - use smaller chunks for faster processing
                text_chunks = [cleaned_text[i:i+4000] for i in range(0, len(cleaned_text), 4000)]
                st.session_state.text_chunks = text_chunks
                
                # Show extracted text
                st.subheader("Extracted Text")
                st.text_area("Extracted Content", value=cleaned_text[:5000] + ("..." if len(cleaned_text) > 5000 else ""), height=300)
                
                # Reset previous parsing results when new content is scraped
                st.session_state.parsed_result = None

# Only show parsing section if we have content
if st.session_state.text_chunks:
    st.markdown("---")
    st.subheader("Extract Information with Ollama")
    
    # Input for parse description
    parse_description = st.text_area(
        "What information would you like to extract?",
        "Make a table with the skills"
    )
    
    # Button to parse the content
    if st.button("Parse Content with Ollama") and not st.session_state.parsing_in_progress:
        # Set flag to prevent multiple parsing runs
        st.session_state.parsing_in_progress = True
        
        with st.spinner("Parsing content with Ollama..."):
            # Only parse if we don't already have a result or if this is a new parse request
            if st.session_state.parsed_result is None:
                parsed_content = parse_with_ollama(st.session_state.text_chunks, parse_description)
                st.session_state.parsed_result = parsed_content
            else:
                parsed_content = st.session_state.parsed_result
            
            # Display the parsed content
            st.subheader("Parsed Content")
            st.write(parsed_content)
        
        # Reset the flag after parsing is complete
        st.session_state.parsing_in_progress = False
    
    # If we have a previous parsing result, display it
    elif st.session_state.parsed_result is not None:
        st.subheader("Parsed Content")
        st.write(st.session_state.parsed_result)

# How it works section
st.markdown("---")
st.markdown("### How It Works")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**1. Scrape Website**")
    st.markdown("Enter a URL and scrape it using a headless browser")

with col2:
    st.markdown("**2. Extract Text**")
    st.markdown("The scraped HTML is processed to extract clean text content")

with col3:
    st.markdown("**3. Extract Information**")
    st.markdown("Use Ollama's local LLM to extract the specific information you need")

st.markdown("---")
st.markdown("Created by [DJ Lawrence](https://djlawrence1209.com)")
        