"""
Chrome debugging script for AI Web Scraper
Run this script to check for common Chrome and Selenium issues.
"""
import os
import sys
import platform
import subprocess
import shutil
import time
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

print("=" * 60)
print("Chrome Debugging Tool for AI Web Scraper")
print("=" * 60)

# System information
print(f"\n1. System Information:")
print(f"   OS: {platform.system()} {platform.version()}")
print(f"   Python: {sys.version}")

# Check for Chrome installation
def find_chrome():
    print("\n2. Checking for Chrome installation:")
    chrome_found = False
    
    if platform.system() == "Windows":
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"   ✅ Chrome found at: {path}")
                chrome_found = True
                try:
                    # Try to get Chrome version
                    result = subprocess.run([path, "--version"], 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE,
                                           timeout=2,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                    version = result.stdout.decode().strip()
                    print(f"   Chrome version: {version}")
                except Exception as e:
                    print(f"   Could not determine Chrome version: {e}")
                break
                
        if not chrome_found:
            print("   ❌ Chrome not found in standard locations")
    
    elif platform.system() == "Darwin":  # macOS
        if os.path.exists("/Applications/Google Chrome.app"):
            print("   ✅ Chrome found at: /Applications/Google Chrome.app")
            chrome_found = True
        else:
            print("   ❌ Chrome not found in standard location")
    
    else:  # Linux
        chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser")
        if chrome_path:
            print(f"   ✅ Chrome found at: {chrome_path}")
            chrome_found = True
        else:
            print("   ❌ Chrome not found in PATH")
    
    return chrome_found

# Check for running Chrome processes
def check_running_chrome():
    print("\n3. Checking for running Chrome processes:")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
            if "chrome.exe" in result.stdout:
                print("   ⚠️ Chrome processes are running - this might cause conflicts")
                print("   Chrome process details:")
                for line in result.stdout.splitlines():
                    if "chrome.exe" in line:
                        print(f"   {line.strip()}")
            else:
                print("   ✅ No Chrome processes running")
        
        elif platform.system() in ["Darwin", "Linux"]:
            result = subprocess.run(["ps", "aux"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
            
            chrome_count = 0
            for line in result.stdout.splitlines():
                if "chrome" in line.lower() and "defunct" not in line:
                    chrome_count += 1
            
            if chrome_count > 0:
                print(f"   ⚠️ {chrome_count} Chrome processes are running - this might cause conflicts")
            else:
                print("   ✅ No Chrome processes running")
    
    except Exception as e:
        print(f"   ❓ Could not check running Chrome processes: {e}")

# Test ChromeDriver with temporary directory
def test_chromedriver():
    print("\n4. Testing ChromeDriver with temporary directory:")
    temp_dir = None
    
    try:
        print("   Creating a temporary directory for Chrome data...")
        temp_dir = tempfile.mkdtemp(prefix="chrome_test_")
        print(f"   ✅ Temporary directory created: {temp_dir}")
        
        print("   Downloading appropriate ChromeDriver...")
        if platform.system() == "Windows":
            driver_path = ChromeDriverManager().install()
        else:
            driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        
        print(f"   ✅ ChromeDriver downloaded to: {driver_path}")
        
        print("   Configuring Chrome options...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-data-dir={temp_dir}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1920,1080")
        
        print("   Attempting to start Chrome with ChromeDriver...")
        driver = webdriver.Chrome(service=Service(driver_path), options=options)
        print("   ✅ ChromeDriver successfully started Chrome!")
        
        print("   Testing navigation...")
        driver.get("https://www.google.com")
        print(f"   ✅ Successfully loaded page with title: {driver.title}")
        
        driver.quit()
        print("   ✅ Chrome closed successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ ChromeDriver test failed: {e}")
        return False
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"   ✅ Temporary directory removed: {temp_dir}")
            except Exception as e:
                print(f"   ⚠️ Failed to remove temporary directory: {e}")

# Test if temporary directory can be created and accessed
def test_temp_directory():
    print("\n5. Testing temporary directory functionality:")
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="chrome_scraper_test_")
        print(f"   ✅ Temporary directory created: {temp_dir}")
        
        # Test if we can write a file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        print(f"   ✅ Successfully wrote to file in temporary directory")
        
        # Test if we can read the file
        with open(test_file, 'r') as f:
            content = f.read()
        
        if content == "Test content":
            print(f"   ✅ Successfully read from file in temporary directory")
        else:
            print(f"   ⚠️ File content doesn't match what was written")
        
        return True
    except Exception as e:
        print(f"   ❌ Temporary directory test failed: {e}")
        return False
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"   ✅ Temporary directory removed: {temp_dir}")
            except Exception as e:
                print(f"   ⚠️ Failed to remove temporary directory: {e}")

# Run the checks
chrome_installed = find_chrome()
check_running_chrome()
temp_dir_works = test_temp_directory()

if chrome_installed and temp_dir_works:
    chromedriver_works = test_chromedriver()
    
    if chromedriver_works:
        print("\n✅ All tests passed! Chrome should work with the AI Web Scraper.")
    else:
        print("\n⚠️ ChromeDriver test failed. Try these troubleshooting steps:")
        print("   1. Close all Chrome windows and processes")
        print("   2. Update Chrome to the latest version")
        print("   3. Temporarily disable antivirus software")
        print("   4. Check if your computer has enough free disk space (at least 1GB)")
else:
    if not chrome_installed:
        print("\n❌ Chrome is not installed. Please install Google Chrome first:")
        print("   Download from: https://www.google.com/chrome/")
    
    if not temp_dir_works:
        print("\n❌ Temporary directory functionality failed. This could be due to:")
        print("   1. Insufficient permissions on your system")
        print("   2. Antivirus software blocking temp file creation")
        print("   3. Disk space issues")

print("\n" + "=" * 60)
input("Press Enter to exit...") 