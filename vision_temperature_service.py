#!/usr/bin/env python3
"""
Centralized Vision Temperature Service
This service continuously monitors the thermostat display using AI vision
and writes the temperature to a file that multiple frontends can read.
"""

import time
import json
import os
import logging
import requests
from datetime import datetime
import subprocess
import signal
import sys

# Configuration
UPDATE_INTERVAL = 30  # Update every 30 seconds
OUTPUT_FILE = "/var/tmp/thermostat_temperature.json"
LOG_FILE = "/var/log/vision_temperature_service.log"
IMAGE_URL = "http://localhost:5000/video_feed"  # URL to get latest image
TEMP_IMAGE_PATH = "/tmp/vision_temp_capture.jpg"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

class VisionTemperatureService:
    def __init__(self):
        self.running = True
        self.last_temperature = None
        self.last_update = None
        self.confidence = "LOW"
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def capture_image(self):
        """Capture the latest image from the thermostat camera"""
        try:
            # Get the latest image from the Flask server
            response = requests.get(IMAGE_URL, timeout=10, stream=True)
            response.raise_for_status()
            
            # Extract the image from the multipart response
            if 'multipart' in response.headers.get('content-type', ''):
                # Read until we find the image data
                for line in response.iter_lines():
                    if line == b'--frame':
                        # Skip headers
                        response.raw.read_until(b'\r\n\r\n')
                        # Read image data until next boundary
                        image_data = b''
                        while True:
                            chunk = response.raw.read(1024)
                            if b'--frame' in chunk:
                                image_data += chunk.split(b'--frame')[0]
                                break
                            image_data += chunk
                        
                        # Save image
                        with open(TEMP_IMAGE_PATH, 'wb') as f:
                            f.write(image_data)
                        return True
            else:
                # Direct image response
                with open(TEMP_IMAGE_PATH, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
                
        except Exception as e:
            logging.error(f"Error capturing image: {e}")
            # Try alternative method - get from static image path
            try:
                static_image_path = "/home/jason/smart-thermostat/static/images/latest_image.jpg"
                if os.path.exists(static_image_path):
                    # Copy the file
                    subprocess.run(['cp', static_image_path, TEMP_IMAGE_PATH], check=True)
                    return True
            except Exception as e2:
                logging.error(f"Error using static image: {e2}")
                
        return False
        
    def get_claude_temperature(self):
        """Get temperature reading from Claude"""
        try:
            # Use the claude command to read the temperature
            claude_path = '/home/jason/.nvm/versions/node/v18.20.8/bin/claude'
            prompt = f"Look at {TEMP_IMAGE_PATH} - what temperature number is shown on this thermostat display? Reply with just the number."
            
            result = subprocess.run(
                [claude_path, prompt],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                try:
                    # Extract just the number
                    temp = int(response.replace('°F', '').replace('°', '').strip())
                    if 50 <= temp <= 90:
                        logging.info(f"Claude read temperature: {temp}°F")
                        return temp
                    else:
                        logging.warning(f"Temperature {temp} out of valid range")
                except ValueError:
                    logging.error(f"Could not parse temperature from response: {response}")
            else:
                logging.error(f"Claude command failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.error("Claude command timed out")
        except Exception as e:
            logging.error(f"Error getting Claude temperature: {e}")
            
        return None
        
    def calculate_confidence(self, age_seconds):
        """Calculate confidence based on reading age"""
        if age_seconds < 60:
            return "HIGH"
        elif age_seconds < 300:
            return "MEDIUM"
        else:
            return "LOW"
            
    def write_temperature_file(self):
        """Write the current temperature data to the output file"""
        try:
            data = {
                "temperature": self.last_temperature,
                "timestamp": self.last_update.isoformat() if self.last_update else None,
                "confidence": self.confidence,
                "age_seconds": (datetime.now() - self.last_update).total_seconds() if self.last_update else None
            }
            
            # Write to a temporary file first, then move it atomically
            temp_file = OUTPUT_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Atomic move
            os.replace(temp_file, OUTPUT_FILE)
            
            # Make sure the file is readable by all
            os.chmod(OUTPUT_FILE, 0o644)
            
            logging.info(f"Wrote temperature data: {data}")
            
        except Exception as e:
            logging.error(f"Error writing temperature file: {e}")
            
    def run_update_cycle(self):
        """Run a single update cycle"""
        try:
            # Capture image
            if self.capture_image():
                # Get temperature from Claude
                temp = self.get_claude_temperature()
                
                if temp is not None:
                    self.last_temperature = temp
                    self.last_update = datetime.now()
                    self.confidence = "HIGH"
                else:
                    # Update confidence based on age of last reading
                    if self.last_update:
                        age = (datetime.now() - self.last_update).total_seconds()
                        self.confidence = self.calculate_confidence(age)
                        
                # Always write the file, even if we couldn't get a new reading
                self.write_temperature_file()
            else:
                logging.warning("Failed to capture image")
                # Still update confidence and write file
                if self.last_update:
                    age = (datetime.now() - self.last_update).total_seconds()
                    self.confidence = self.calculate_confidence(age)
                    self.write_temperature_file()
                    
        except Exception as e:
            logging.error(f"Error in update cycle: {e}")
            
    def run(self):
        """Main service loop"""
        logging.info("Vision Temperature Service starting...")
        
        # Initial update
        self.run_update_cycle()
        
        # Main loop
        while self.running:
            try:
                # Wait for the update interval
                time.sleep(UPDATE_INTERVAL)
                
                if self.running:
                    self.run_update_cycle()
                    
            except Exception as e:
                logging.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)  # Brief pause before continuing
                
        logging.info("Vision Temperature Service stopped")
        
        # Write a final status file indicating service is stopped
        try:
            data = {
                "temperature": self.last_temperature,
                "timestamp": self.last_update.isoformat() if self.last_update else None,
                "confidence": "SERVICE_STOPPED",
                "age_seconds": (datetime.now() - self.last_update).total_seconds() if self.last_update else None,
                "service_status": "stopped"
            }
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass


if __name__ == "__main__":
    service = VisionTemperatureService()
    service.run()