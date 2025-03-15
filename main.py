import streamlit as st 
import contextlib
import re
import os
from scrape import (
    scrape_website, 
    split_dom_content, 
    clean_body_content, 
    extract_body_content
)
from parse import parse_with_ollama

# Detect if running on cloud platform
is_cloud_platform = os.environ.get('RENDER') or os.environ.get('DYNO')
if is_cloud_platform:
    st.set_page_config(
        page_title="AI Web Scraper",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

# Add custom CSS for styling the buttons and spinner
custom_css = """
/* Styling for Streamlit buttons */
.stButton > button {
    width: 150px;
    height: 50px;
    background-color: white;
    color: #568fa6;
    position: relative;
    overflow: hidden;
    font-size: 12px;  /* Reduced font size */
    letter-spacing: 0.5px;  /* Reduced letter spacing */
    font-weight: 500;
    text-transform: none;  /* Remove uppercase transformation */
    transition: all 0.3s ease;
    cursor: pointer;
    border: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 3px;
    box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);
    white-space: nowrap;  /* Prevent line breaks */
}

/* Capitalize just the first letter of each word */
.stButton > button {
    text-transform: capitalize;
}

/* Maintain button color on hover */
.stButton > button:hover {
    color: #44d8a4;
    background-color: #f8f8f8;
    border: 2px solid #44d8a4;
}

/* Maintain button color when clicked/active */
.stButton > button:active,
.stButton > button:focus {
    color: #568fa6 !important;
    background-color: white !important;
    border: 0 !important;
    box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1) !important;
    outline: none !important;
}

/* Restore hover effect after focus */
.stButton > button:focus:hover {
    color: #44d8a4 !important;
    background-color: #f8f8f8 !important;
    border: 2px solid #44d8a4 !important;
}

.stButton > button::after {
    content: "";
    position: absolute;
    width: 0;
    height: 2px;
    background-color: #44d8a4;
    transition: all 0.3s cubic-bezier(0.35, 0.1, 0.25, 1);
    bottom: 0;
    left: 0;
}

.stButton > button:hover::after {
    width: 100%;
}

/* Specific styling for the scrape button */
.stButton[data-testid*="scrape"] > button:hover::before {
    content: "Scrape!";
    position: absolute;
    color: #44d8a4;
    font-size: 12px;
}

/* Specific styling for the parse button */
.stButton[data-testid*="parse"] > button:hover::before {
    content: "Parse!";
    position: absolute;
    color: #44d8a4;
    font-size: 12px;
}

/* Custom spinner styling */
.custom-spinner-container {
  position: relative;
  display: inline-block;
  height: 30px;
  width: 30px;
  margin-right: 10px;
  vertical-align: middle;
}

.custom-spinner {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  height: 30px;
  width: 30px;
  animation: rotate_3922 1.2s linear infinite;
  background-color: #9b59b6;
  background-image: linear-gradient(#9b59b6, #84cdfa, #5ad1cd);
}

.custom-spinner span {
  position: absolute;
  border-radius: 50%;
  height: 100%;
  width: 100%;
  background-color: #9b59b6;
  background-image: linear-gradient(#9b59b6, #84cdfa, #5ad1cd);
}

.custom-spinner span:nth-of-type(1) {
  filter: blur(5px);
}

.custom-spinner span:nth-of-type(2) {
  filter: blur(10px);
}

.custom-spinner span:nth-of-type(3) {
  filter: blur(25px);
}

.custom-spinner span:nth-of-type(4) {
  filter: blur(50px);
}

.custom-spinner::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  right: 3px;
  bottom: 3px;
  background-color: #fff;
  border: solid 2px #ffffff;
  border-radius: 50%;
}

@keyframes rotate_3922 {
  from {
    transform: translate(-50%, -50%) rotate(0deg);
  }

  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

/* Hide the default Streamlit spinner */
.stSpinner {
    display: none !important;
}

.spinner-text {
    display: inline-block;
    vertical-align: middle;
}

/* Example text styling */
.example-text {
    font-size: 0.9em;
    color: #888;
    font-style: italic;
    margin-top: -15px;
    margin-bottom: 15px;
}

/* How it works section styling */
.how-it-works-header {
    margin-top: 200px;  /* Doubled from 100px to 200px to add more space */
    padding-top: 20px;
    border-top: 1px solid #eee;
}

.step-title {
    font-weight: bold;
}

/* Make How It Works section wider */
.wider-section {
    max-width: 1200px !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}
"""

st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)

# Create a custom spinner context manager
@contextlib.contextmanager
def custom_spinner(text="Loading..."):
    # Create a container for the spinner
    spinner_container = st.empty()
    
    # Show spinner with text
    spinner_html = f"""
    <div style="display: flex; align-items: center;">
        <div class="custom-spinner-container">
            <div class="custom-spinner">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
        <div class="spinner-text">{text}</div>
    </div>
    """
    spinner_container.markdown(spinner_html, unsafe_allow_html=True)
    
    try:
        # Execute the context block
        yield
    finally:
        # Remove the spinner
        spinner_container.empty()

# Function to validate URL format
def is_valid_url(url):
    if not url or url.strip() == "":
        return False, "Please enter a website URL"
    
    # Simple URL validation pattern
    url_pattern = re.compile(
        r'^(https?:\/\/)?' # http:// or https:// (optional)
        r'(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)+' # domain
        r'([a-zA-Z]{2,})(\/[-a-zA-Z0-9@:%_\+.~#?&//=]*)?' # path (optional)
        r'$'
    )
    
    if not url_pattern.match(url):
        return False, "Please enter a valid URL (e.g., example.com or https://example.com)"
    
    return True, ""

st.title("AI Web Scraper")
url = st.text_input("Enter a Website URL: ")
st.markdown("<div class='example-text'>Example: https://djlawrence1209.com/</div>", unsafe_allow_html=True)

# Create Streamlit button with custom key
if st.button("Scrape Site", key="scrape_button"):
    # Validate URL first
    is_valid, error_message = is_valid_url(url)
    if not is_valid:
        st.error(error_message)
    else:
        with custom_spinner("Scraping the website..."):
            result = scrape_website(url)
            
            # Check if the result contains an error message
            if result.startswith("<p>"):
                st.error(result.replace("<p>", "").replace("</p>", ""))
            else:
                st.success("Website scraped successfully!")
                
                body_content = extract_body_content(result)
                cleaned_content = clean_body_content(body_content)
                
                if cleaned_content:
                    st.session_state.dom_content = cleaned_content
                    
                    with st.expander("View DOM Content"):
                        st.text_area("DOM Content", cleaned_content, height=300)
                else:
                    st.warning("No content was found on the page or the page structure couldn't be parsed.")

# Only show parse section if we have content
if "dom_content" in st.session_state:
    parse_description = st.text_area("Describe what you want to parse?")
    st.markdown("<div class='example-text'>Example: Make a table with all of the skills listed</div>", unsafe_allow_html=True)
    
    # Create Streamlit button with custom key
    if st.button("Parse Content", key="parse_button"):
        if not parse_description:
            st.error("Please describe what you want to parse")
        else:
            with custom_spinner("Parsing the content..."):
                dom_chunks = split_dom_content(st.session_state.dom_content)
                result = parse_with_ollama(dom_chunks, parse_description)
                st.success("Content parsed successfully!")
                st.write(result)

# Add "How It Works" section using Streamlit's native components
st.markdown("<div class='how-it-works-header'></div>", unsafe_allow_html=True)

# Create a container with wide format
with st.container():
    # Apply custom CSS to make it wider
    st.markdown("<style>.block-container {max-width: 1200px;}</style>", unsafe_allow_html=True)
    
    st.header("How It Works")
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        st.write("1.")
    with col2:
        st.markdown("**Enter a Website Link** - Drop a URL into the input field, and the tool validates it.")
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        st.write("2.")
    with col2:
        st.markdown("**Web Scraping with Selenium & BeautifulSoup** - Selenium loads the site (including JavaScript), while BeautifulSoup extracts the structured content, removing unnecessary elements.")
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        st.write("3.")
    with col2:
        st.markdown("**Pre-Processing the DOM** - The extracted HTML is cleaned using lxml and html5lib, then split into chunks for efficient processing.")
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        st.write("4.")
    with col2:
        st.markdown("**AI Analysis with Ollama 3.2 & LangChain** - Describe what you want to extract. LangChain structures the request, and Ollama 3.2 generates insights from the data.")
    
    col1, col2 = st.columns([0.05, 0.95])
    with col1:
        st.write("5.")
    with col2:
        st.markdown("**Results in Streamlit** - Parsed results are displayed instantly in an interactive Streamlit interface.")
    
    st.markdown("Learn more about me at [djlawrence1209.com](https://djlawrence1209.com/)")
        