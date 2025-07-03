#!/usr/bin/env python3
"""
Service that uses Claude Code CLI to read thermostat temperature
"""
import os
import subprocess
import time
import json
import requests
from datetime import datetime

class ClaudeVisionService:
    def __init__(self):
        self.log_file = "experimental/claude_vision_log.json"
        self.readings = []
        self.interval = 30  # seconds
        
    def capture_display(self):
        """Capture current thermostat display"""
        try:
            response = requests.get('http://blade:5000/video_feed', stream=True, timeout=10)
            if response.status_code == 200:
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg_data = bytes_data[a:b+2]
                        # Save it
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f'experimental/claude_capture_{timestamp}.jpg'
                        with open(filename, 'wb') as f:
                            f.write(jpg_data)
                        return filename
        except Exception as e:
            print(f"Error capturing: {e}")
        return None
    
    def ask_claude_temperature(self, image_path):
        """Use Claude CLI to read temperature from image"""
        try:
            # Build the command
            prompt = f"Look at {image_path} - what temperature number is shown on this thermostat display? Reply with just the number."
            cmd = ['claude', prompt]
            
            # Run Claude CLI
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Extract temperature from response
                response = result.stdout.strip()
                # Try to parse as number
                try:
                    temp = int(response.replace('°F', '').replace('°', '').strip())
                    if 50 <= temp <= 90:  # Sanity check
                        return temp
                except ValueError:
                    pass
            
        except Exception as e:
            print(f"Error asking Claude: {e}")
        
        return None
    
    def update_thermostat_system(self, temperature):
        """Send the Claude-detected temperature to the thermostat system"""
        try:
            # This could update a global variable or send to an endpoint
            # For now, we'll just log it
            reading = {
                "timestamp": datetime.now().isoformat(),
                "temperature": temperature,
                "source": "claude_vision"
            }
            
            self.readings.append(reading)
            
            # Save to file
            with open(self.log_file, 'w') as f:
                json.dump(self.readings[-100:], f, indent=2)  # Keep last 100
            
            print(f"Updated system with temperature: {temperature}°F")
            
        except Exception as e:
            print(f"Error updating system: {e}")
    
    def cleanup_old_images(self):
        """Remove old capture images"""
        try:
            # Get all claude_capture images
            captures = [f for f in os.listdir('experimental') if f.startswith('claude_capture_')]
            captures.sort()
            
            # Keep only last 5
            if len(captures) > 5:
                for old_file in captures[:-5]:
                    os.remove(f'experimental/{old_file}')
        except:
            pass
    
    def run_once(self):
        """Run one detection cycle"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting detection cycle...")
        
        # Capture display
        image_path = self.capture_display()
        if not image_path:
            print("Failed to capture display")
            return False
        
        print(f"Captured: {image_path}")
        
        # Ask Claude
        print("Asking Claude to read temperature...")
        temperature = self.ask_claude_temperature(image_path)
        
        if temperature:
            print(f"Claude read: {temperature}°F")
            self.update_thermostat_system(temperature)
            self.cleanup_old_images()
            return True
        else:
            print("Claude couldn't read temperature")
            return False
    
    def run_continuous(self):
        """Run continuous monitoring"""
        print("Claude Vision Temperature Service")
        print("=================================")
        print(f"Reading every {self.interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                self.run_once()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                print("\nStopping service...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(self.interval)

def test_single_reading():
    """Test a single reading"""
    service = ClaudeVisionService()
    service.run_once()

def start_service():
    """Start the continuous service"""
    service = ClaudeVisionService()
    service.run_continuous()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_single_reading()
    else:
        start_service()