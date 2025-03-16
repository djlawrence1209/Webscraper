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

# Install a specific version of ChromeDriver known to work with Chrome 134
RUN CHROME_VERSION=$(google-chrome --version) \
    && echo "Detected Chrome version: $CHROME_VERSION" \
    && mkdir -p /tmp/chromedriver \
    && cd /tmp/chromedriver \
    && CHROMEDRIVER_VERSION="114.0.5735.90" \
    && echo "Using ChromeDriver version: $CHROMEDRIVER_VERSION" \
    && wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && chmod +x chromedriver \
    && mv chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver \
    && echo "ChromeDriver installed at: $(which chromedriver)" \
    && echo "ChromeDriver version: $(chromedriver --version)" \
    && ln -sf /usr/local/bin/chromedriver /usr/bin/chromedriver

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
