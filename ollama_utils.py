import requests
import subprocess
import sys
import os
import json
import time
import streamlit as st

def check_ollama_running():
    """Check if Ollama is running and provide diagnostic information"""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            return {
                "running": True,
                "version": response.json().get("version", "unknown"),
                "status": "Ollama is running correctly"
            }
        else:
            return {
                "running": False,
                "status": f"Ollama returned unexpected status code: {response.status_code}",
                "error": response.text
            }
    except requests.exceptions.ConnectionError:
        return {
            "running": False,
            "status": "Cannot connect to Ollama. Is it running?",
            "error": "Connection refused to localhost:11434"
        }
    except Exception as e:
        return {
            "running": False,
            "status": "Error checking Ollama status",
            "error": str(e)
        }

def list_available_models():
    """List all available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model.get("name") for model in models]
        return []
    except:
        return []

def get_model_info(model_name):
    """Get detailed information about a specific Ollama model"""
    try:
        response = requests.post(
            "http://localhost:11434/api/show", 
            json={"name": model_name},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def start_ollama():
    """Attempt to start Ollama if it's not running"""
    try:
        # Check if already running
        status = check_ollama_running()
        if status["running"]:
            return {"success": True, "message": "Ollama is already running", "version": status.get("version")}
        
        # Try to start Ollama
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                ["start", "ollama", "serve"], 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:  # Linux/Mac
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        # Wait for it to start
        for _ in range(5):  # Try 5 times with 1 second delay
            time.sleep(1)
            status = check_ollama_running()
            if status["running"]:
                return {"success": True, "message": "Successfully started Ollama", "version": status.get("version")}
        
        return {"success": False, "message": "Failed to start Ollama after multiple attempts"}
    except Exception as e:
        return {"success": False, "message": f"Error starting Ollama: {str(e)}"}

def display_ollama_status():
    """Display Ollama status information in Streamlit"""
    status = check_ollama_running()
    
    if status["running"]:
        st.success(f"✅ Ollama is running (version: {status.get('version', 'unknown')})")
        models = list_available_models()
        if models:
            st.write("Available models:")
            for model in models:
                st.write(f"- {model}")
        else:
            st.warning("No models found. You might need to download a model with 'ollama pull llama3'")
    else:
        st.error(f"❌ Ollama is not running: {status['status']}")
        st.info("Make sure Ollama is installed and running with 'ollama serve' command")
        
        # Add a button to try starting Ollama
        if st.button("Try to start Ollama"):
            result = start_ollama()
            if result["success"]:
                st.success(result["message"])
                st.experimental_rerun()
            else:
                st.error(result["message"])
                st.info("Please manually start Ollama from the command line with 'ollama serve'")

def test_model(model_name="llama3"):
    """Test if a specific model works"""
    try:
        payload = {
            "model": model_name,
            "prompt": "Respond with only the word 'working' if you can read this."
        }
        response = requests.post(
            "http://localhost:11434/api/generate", 
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            return {"success": False, "message": f"Model test failed: HTTP {response.status_code}"}
        
        # Parse streaming response
        text = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        text += data["response"]
                    if "done" in data and data["done"]:
                        break
                except:
                    pass
        
        if "working" in text.lower():
            return {"success": True, "message": f"Model '{model_name}' is working properly"}
        else:
            return {"success": False, "message": f"Model responded but with unexpected output: {text[:50]}"}
    except Exception as e:
        return {"success": False, "message": f"Error testing model: {str(e)}"} 