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

# Import scraping functions from scrape.py (now Playwright-based)
from scrape import (
    scrape_website, 
    extract_body_content, 
    clean_body_content, 
    split_dom_content
)

# Import parsing functions
from parse import parse_with_ollama

# Import Ollama utilities
try:
    from ollama_utils import (
        check_ollama_running, 
        list_available_models,
        display_ollama_status,
        test_model
    )
    OLLAMA_UTILS_AVAILABLE = True
except ImportError:
    OLLAMA_UTILS_AVAILABLE = False

# Page config  
st.set_page_config(page_title="AI Web Scraper", page_icon="🔍", layout="wide")

# Title
st.title("AI Web Scraper")

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
if 'ollama_checked' not in st.session_state:
    st.session_state.ollama_checked = False
if 'available_models' not in st.session_state:
    st.session_state.available_models = []

# Button to scrape website
if st.button("Scrape Site"):
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
            
            # Reset previous parsing results when new content is scraped
            st.session_state.parsed_result = None

# Always show extracted text if we have content
if st.session_state.cleaned_text:
    st.subheader("Extracted Text")
    st.text_area("Extracted Content", value=st.session_state.cleaned_text[:5000] + ("..." if len(st.session_state.cleaned_text) > 5000 else ""), height=300)

# Only show parsing section if we have content
if st.session_state.text_chunks:
    st.markdown("---")
    st.subheader("Extract Information with Ollama")
    
    # Show Ollama status if utils are available
    if OLLAMA_UTILS_AVAILABLE:
        with st.expander("Ollama Status", expanded=not st.session_state.ollama_checked):
            display_ollama_status()
            st.session_state.ollama_checked = True
            
            # Test connection button
            if st.button("Test Ollama Connection"):
                status = check_ollama_running()
                if status["running"]:
                    # Get available models
                    models = list_available_models()
                    if models:
                        st.session_state.available_models = models
                        st.success(f"Found {len(models)} models: {', '.join(models[:5])}" + ("..." if len(models) > 5 else ""))
                        
                        # Test default model
                        default_model = "llama3" if "llama3" in models else models[0]
                        test_result = test_model(default_model)
                        if test_result["success"]:
                            st.success(test_result["message"])
                        else:
                            st.warning(test_result["message"])
                    else:
                        st.warning("No models found. You need to pull a model first.")
                        st.code("ollama pull llama3", language="bash")
                else:
                    st.error(f"Ollama is not running: {status['status']}")
    else:
        st.info("This feature requires Ollama to be running locally. If you haven't started Ollama, run 'ollama serve' in a terminal window first.")
    
    # Model selection - use available models if we have them
    if OLLAMA_UTILS_AVAILABLE and st.session_state.available_models:
        selected_model = st.selectbox("Select Ollama Model", st.session_state.available_models, index=0)
    else:
        model_options = ["llama3.2", "llama3", "phi3:medium", "mistral"]
        selected_model = st.selectbox("Select Ollama Model", model_options, index=0)
    
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
            # Get the text chunks from session state
            text_chunks = st.session_state.text_chunks
            
            # Check if text chunks exist and are not empty
            if not text_chunks or not any(chunk.strip() for chunk in text_chunks):
                st.error("No content to parse. Please scrape a website first.")
                st.session_state.parsing_in_progress = False
            else:
                try:
                    # Check if Ollama is running
                    if OLLAMA_UTILS_AVAILABLE:
                        status = check_ollama_running()
                        if status["running"]:
                            st.success("Connected to Ollama successfully")
                        else:
                            st.error(f"Could not connect to Ollama: {status['status']}")
                            st.error("Make sure Ollama is running with 'ollama serve' command.")
                            st.session_state.parsing_in_progress = False
                            st.stop()
                    else:
                        # Fallback to direct request check
                        import requests
                        try:
                            response = requests.get("http://localhost:11434/api/version", timeout=2)
                            if response.status_code == 200:
                                st.success("Connected to Ollama successfully")
                            else:
                                st.warning(f"Ollama connection issue: Status code {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Could not connect to Ollama at http://localhost:11434. Make sure it's running with 'ollama serve' command.")
                            st.error(f"Error details: {str(e)}")
                            st.session_state.parsing_in_progress = False
                            st.stop()
                    
                    # If we made it here, we can try to process with Ollama
                    # Process with Ollama
                    parsed_content = parse_with_ollama(text_chunks, parse_description, model_name=selected_model)
                    
                    # Check if we got a valid result
                    if parsed_content.startswith("No relevant information found"):
                        # Try one more time with a longer chunk to make sure we're sending enough content
                        if st.session_state.cleaned_text:
                            # Create larger chunks
                            st.info("First attempt didn't find relevant content. Trying with larger chunks...")
                            larger_chunks = [st.session_state.cleaned_text[i:i+6000] for i in range(0, len(st.session_state.cleaned_text), 6000)]
                            # Try again with larger chunks
                            parsed_content = parse_with_ollama(larger_chunks, parse_description, model_name=selected_model)
                    
                    # Store the result
                    st.session_state.parsed_result = parsed_content
                except Exception as e:
                    st.error(f"Error during parsing: {str(e)}")
                    import traceback
                    st.error(f"Traceback: {traceback.format_exc()}")
                    st.session_state.parsing_in_progress = False
        
        # Reset the flag after parsing is complete
        st.session_state.parsing_in_progress = False
    
    # Display parsing results
    if st.session_state.parsed_result:
        st.subheader("Parsed Content")
        try:
            # Try as markdown first
            st.markdown(st.session_state.parsed_result)
        except:
            # Fall back to plain text if markdown fails
            st.text(st.session_state.parsed_result)

# How it works section
st.markdown("---")
st.markdown("### How It Works")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**1. Scrape Website**")
    st.markdown("Enter a URL and scrape it using Playwright's headless browser")

with col2:
    st.markdown("**2. Extract Text**")
    st.markdown("The scraped HTML is processed to extract clean text content")

with col3:
    st.markdown("**3. Extract Information**")
    st.markdown("Use Ollama's local LLM to extract the specific information you need")

st.markdown("---")
st.markdown("Created by [DJ Lawrence](https://djlawrence1209.com)")
        