FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install specific ChromeDriver version (using direct download that's compatible with Chrome 134)
RUN wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/134.0.6047.0/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64 \
    && echo "ChromeDriver installation completed" \
    && chromedriver --version || echo "ChromeDriver installation failed"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RENDER=true

# Set the port
ENV PORT=8501

# Run the application
CMD streamlit run main.py --server.port $PORT --server.address 0.0.0.0
