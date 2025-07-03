#!/usr/bin/env python3
"""
Script to capture thermostat image and prepare it for Claude vision analysis
This can be integrated into your thermostat system for accurate temperature reading
"""
import os
import requests
import json
from datetime import datetime
import time

class ThermostatVisionReader:
    def __init__(self, thermostat_url="http://blade:5000"):
        self.thermostat_url = thermostat_url
        self.captures_dir = "experimental/vision_captures"
        os.makedirs(self.captures_dir, exist_ok=True)
        
    def capture_display(self):
        """Capture current thermostat display"""
        try:
            # Try video feed endpoint
            response = requests.get(f"{self.thermostat_url}/video_feed", 
                                  stream=True, timeout=10)
            
            if response.status_code == 200:
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    # Look for JPEG markers
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        jpg_data = bytes_data[a:b+2]
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{self.captures_dir}/capture_{timestamp}.jpg"
                        
                        with open(filename, 'wb') as f:
                            f.write(jpg_data)
                        
                        # Update latest symlink
                        latest = f"{self.captures_dir}/latest.jpg"
                        if os.path.exists(latest):
                            os.remove(latest)
                        os.symlink(os.path.abspath(filename), latest)
                        
                        return filename
        
        except Exception as e:
            print(f"Error capturing display: {e}")
        
        return None
    
    def prepare_for_claude(self, image_path):
        """Prepare image and prompt for Claude analysis"""
        analysis_request = {
            "image_path": os.path.abspath(image_path),
            "timestamp": datetime.now().isoformat(),
            "prompt": """Look at this thermostat display and extract:
1. The temperature shown (just the number)
2. Any visible mode indicator (HEAT/COOL/OFF)
3. Your confidence level

Respond in this exact format:
TEMP: [number]
MODE: [mode or 'unknown']
CONFIDENCE: [high/medium/low]""",
            "expected_format": {
                "temperature": "integer between 50-90",
                "mode": "one of: heat, cool, off, unknown",
                "confidence": "one of: high, medium, low"
            }
        }
        
        # Save request
        request_file = f"{self.captures_dir}/request_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(request_file, 'w') as f:
            json.dump(analysis_request, f, indent=2)
        
        return request_file
    
    def create_test_script(self):
        """Create a test script for easy Claude integration"""
        test_script = """#!/bin/bash
# Test script to read temperature with Claude vision

echo "Capturing thermostat display..."
python3 vision_temperature_reader.py

echo -e "\\nTo analyze with Claude, run:"
echo "claude 'Look at experimental/vision_captures/latest.jpg - what temperature is shown on this thermostat display?'"
"""
        
        script_path = "experimental/test_vision_reading.sh"
        with open(script_path, 'w') as f:
            f.write(test_script)
        os.chmod(script_path, 0o755)
        
        return script_path

def main():
    """Main execution"""
    reader = ThermostatVisionReader()
    
    print("Thermostat Vision Reader")
    print("="*50)
    
    # Capture display
    print("Capturing thermostat display...")
    image_path = reader.capture_display()
    
    if image_path:
        print(f"✓ Captured: {image_path}")
        
        # Prepare for Claude
        request_file = reader.prepare_for_claude(image_path)
        print(f"✓ Request prepared: {request_file}")
        
        # Create test script
        script_path = reader.create_test_script()
        print(f"✓ Test script created: {script_path}")
        
        print("\n" + "-"*50)
        print("NEXT STEPS:")
        print("-"*50)
        print("\n1. Quick test with Claude:")
        print(f"   claude 'What temperature is shown in {image_path}?'")
        
        print("\n2. Detailed analysis:")
        print(f"   claude 'Analyze the thermostat display in {image_path}. Extract the temperature, mode if visible, and rate your confidence.'")
        
        print("\n3. Use the test script:")
        print(f"   ./experimental/test_vision_reading.sh")
        
        print("\n4. For integration, the image is always available at:")
        print(f"   experimental/vision_captures/latest.jpg")
        
    else:
        print("✗ Failed to capture display")
        print("  Make sure the thermostat server is running")

if __name__ == "__main__":
    main()