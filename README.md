# AI Web Scraper

A powerful web scraping and AI content extraction tool built with Streamlit, Selenium, and BeautifulSoup. This application allows you to scrape websites and extract structured information using AI.

## Features

- Web scraping with Selenium for JavaScript-rendered sites
- DOM cleaning and processing with BeautifulSoup
- AI-powered content extraction with Ollama 3.2 and LangChain
- User-friendly Streamlit interface

## Requirements

- Python 3.9 or higher
- Google Chrome browser
- Ollama server running locally (for AI parsing)

## Setup Instructions

### Local Setup

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd <repository-folder>
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure Chrome is installed**

   The web scraper requires Google Chrome to be installed on your system. If you don't have Chrome installed, download it from [google.com/chrome](https://www.google.com/chrome/).

4. **Run the debugging tool to verify setup**

   ```bash
   python debug_chrome.py
   ```

   This will check if Chrome is properly configured on your system.

5. **Start the application**

   ```bash
   streamlit run main.py
   ```

### Deploying to Render

1. **Create a new Web Service on Render**

2. **Connect your GitHub/GitLab repository**

3. **Configure the following settings:**

   - **Build Command:** `bash build.sh`
   - **Start Command:** `streamlit run main.py --server.port $PORT --server.address 0.0.0.0`

4. **Set Environment Variables:**
   - Add `RENDER=true`

5. **Deploy**

## Troubleshooting

### Common Issues - Local Environment

If you encounter errors when running the scraper locally:

1. **Chrome crashes or won't start**
   - Close all Chrome windows and processes
   - Update Chrome to the latest version
   - Run `python debug_chrome.py` to diagnose issues
   - Temporarily disable your antivirus software
   - Restart your computer

2. **Permission errors with chromedriver**
   - The application should handle this automatically, but if problems persist, try running the debug tool.

### Common Issues - Render Deployment

1. **Chrome binary errors**
   - Check the build logs to ensure Chrome was installed properly
   - Verify that the environment variable `RENDER=true` is set

2. **Timeout errors**
   - Increase the timeout duration in `scrape.py` if needed

## Project Structure

- `main.py` - Streamlit application entry point
- `scrape.py` - Web scraping functionality
- `parse.py` - AI parsing with Ollama
- `debug_chrome.py` - Diagnostic tool for Chrome issues
- `requirements.txt` - Python dependencies
- `build.sh` - Setup script for Render
- `render.yaml` - Render configuration

## License

MIT

## Contact

Your contact information or link to portfolio 