#!/usr/bin/env python3
"""
Use Claude Code directly to analyze thermostat images
This version saves images for Claude Code to analyze
"""
import cv2
import numpy as np
import requests
import json
import os
from datetime import datetime
import time

class ClaudeCodeVisionReader:
    def __init__(self):
        self.thermostat_url = "http://blade:5000"
        self.captures_dir = "experimental/claude_analysis"
        os.makedirs(self.captures_dir, exist_ok=True)
        
    def capture_for_analysis(self):
        """Capture image and prepare for Claude Code analysis"""
        try:
            response = requests.get(f"{self.thermostat_url}/video_feed", 
                                  stream=True, timeout=10)
            
            if response.status_code == 200:
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        jpg_data = bytes_data[a:b+2]
                        
                        # Save original
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_path = f"{self.captures_dir}/thermostat_{timestamp}.jpg"
                        
                        with open(image_path, 'wb') as f:
                            f.write(jpg_data)
                        
                        # Also save as "latest" for easy access
                        latest_path = f"{self.captures_dir}/latest_capture.jpg"
                        with open(latest_path, 'wb') as f:
                            f.write(jpg_data)
                        
                        # Create analysis request file
                        request_file = f"{self.captures_dir}/analysis_request.txt"
                        with open(request_file, 'w') as f:
                            f.write(f"ANALYZE THIS IMAGE: {latest_path}\n")
                            f.write("What temperature is displayed on this thermostat?\n")
                            f.write("Please respond with just the temperature number.\n")
                        
                        return image_path, latest_path
                        
        except Exception as e:
            print(f"Error capturing: {e}")
            
        return None, None
    
    def create_interactive_script(self):
        """Create a script that captures and prompts for analysis"""
        script_content = '''#!/usr/bin/env python3
"""
Interactive thermostat reader using Claude Code
"""
import os
import sys
import time
from claude_code_vision import ClaudeCodeVisionReader

def main():
    reader = ClaudeCodeVisionReader()
    
    print("Claude Code Thermostat Vision Reader")
    print("="*50)
    
    while True:
        print("\\nCapturing thermostat display...")
        image_path, latest_path = reader.capture_for_analysis()
        
        if image_path:
            print(f"✓ Captured: {image_path}")
            print("\\nTo analyze with Claude Code, I'll look at the image now...")
            print(f"Image location: {latest_path}")
            
            # Here Claude Code can directly analyze the image
            # since it can see images in the conversation
            
            # Wait for user input
            response = input("\\nPress Enter to capture again, or 'q' to quit: ")
            if response.lower() == 'q':
                break
        else:
            print("Failed to capture image")
            
        time.sleep(1)

if __name__ == "__main__":
    main()
'''
        
        script_path = "experimental/interactive_vision.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        return script_path

def analyze_current_display():
    """Capture and analyze current display"""
    reader = ClaudeCodeVisionReader()
    
    print("Capturing current thermostat display...")
    image_path, latest_path = reader.capture_for_analysis()
    
    if image_path:
        print(f"✓ Image saved to: {latest_path}")
        print("\nI'll analyze this image now...")
        
        # Load and display the image for Claude Code to see
        return latest_path
    
    return None

if __name__ == "__main__":
    # Capture and prepare for analysis
    image_path = analyze_current_display()
    
    if image_path:
        print(f"\nReady for analysis: {image_path}")
        print("Claude Code can now look at this image and read the temperature.")