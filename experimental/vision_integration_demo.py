#!/usr/bin/env python3
"""
Demo of how Claude vision could be integrated for temperature reading
"""
import os
import json
import requests
from datetime import datetime

class ClaudeVisionTemperatureReader:
    def __init__(self):
        self.last_reading = None
        self.last_reading_time = None
        self.confidence_threshold = "medium"  # minimum confidence to accept reading
        
    def capture_and_analyze(self):
        """Capture display and get Claude's reading"""
        # First capture the image
        print("Capturing thermostat display...")
        
        try:
            response = requests.get("http://blade:5000/video_feed", stream=True, timeout=10)
            if response.status_code == 200:
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        jpg_data = bytes_data[a:b+2]
                        
                        # Save for analysis
                        capture_dir = "experimental/vision_readings"
                        os.makedirs(capture_dir, exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_path = f"{capture_dir}/reading_{timestamp}.jpg"
                        
                        with open(image_path, 'wb') as f:
                            f.write(jpg_data)
                        
                        print(f"✓ Captured: {image_path}")
                        
                        # In a real implementation, this would call Claude's API
                        # For demo, we'll simulate the response
                        return self.simulate_claude_analysis(image_path)
                        
        except Exception as e:
            print(f"Error capturing: {e}")
            return None
    
    def simulate_claude_analysis(self, image_path):
        """Simulate what Claude's analysis would return"""
        # In reality, this would make an API call to Claude
        # For this demo, we'll return a structured response
        
        analysis = {
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "temperature": 77,  # Claude read this from the image
            "mode": "unknown",  # Couldn't determine from this view
            "confidence": "high",
            "raw_response": "TEMP: 77\nMODE: unknown\nCONFIDENCE: high",
            "additional_observations": [
                "Seven-segment LCD display",
                "Fan Auto indicator visible",
                "Display appears clear and readable"
            ]
        }
        
        # Save the analysis
        analysis_path = image_path.replace('.jpg', '_analysis.json')
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return analysis
    
    def get_temperature_reading(self):
        """Get temperature reading with confidence check"""
        analysis = self.capture_and_analyze()
        
        if analysis and analysis['confidence'] in ['high', 'medium']:
            self.last_reading = analysis['temperature']
            self.last_reading_time = datetime.now()
            
            return {
                "success": True,
                "temperature": analysis['temperature'],
                "confidence": analysis['confidence'],
                "timestamp": self.last_reading_time.isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Low confidence or failed to read",
                "last_known": self.last_reading,
                "last_known_time": self.last_reading_time.isoformat() if self.last_reading_time else None
            }
    
    def compare_with_sensor(self, sensor_temp):
        """Compare vision reading with sensor reading"""
        vision_result = self.get_temperature_reading()
        
        if vision_result['success']:
            vision_temp = vision_result['temperature']
            difference = abs(vision_temp - sensor_temp)
            
            comparison = {
                "vision_temperature": vision_temp,
                "sensor_temperature": sensor_temp,
                "difference": difference,
                "match": difference <= 2,  # Within 2 degrees
                "confidence": vision_result['confidence'],
                "timestamp": datetime.now().isoformat()
            }
            
            # Log comparison
            log_dir = "experimental/vision_logs"
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = f"{log_dir}/comparisons.jsonl"
            with open(log_file, 'a') as f:
                f.write(json.dumps(comparison) + '\n')
            
            return comparison
        else:
            return {
                "error": "Failed to get vision reading",
                "sensor_temperature": sensor_temp
            }

def demo_vision_integration():
    """Demonstrate the vision integration"""
    print("Claude Vision Temperature Reader Demo")
    print("="*60)
    
    reader = ClaudeVisionTemperatureReader()
    
    # Get a temperature reading
    print("\n1. Getting temperature reading via vision...")
    result = reader.get_temperature_reading()
    
    if result['success']:
        print(f"✓ Temperature: {result['temperature']}°F")
        print(f"✓ Confidence: {result['confidence']}")
        print(f"✓ Timestamp: {result['timestamp']}")
    else:
        print(f"✗ Failed: {result['error']}")
    
    # Compare with sensor (simulated)
    print("\n2. Comparing with sensor reading...")
    sensor_temp = 76  # Simulated sensor reading
    comparison = reader.compare_with_sensor(sensor_temp)
    
    if 'error' not in comparison:
        print(f"✓ Vision: {comparison['vision_temperature']}°F")
        print(f"✓ Sensor: {comparison['sensor_temperature']}°F") 
        print(f"✓ Difference: {comparison['difference']}°F")
        print(f"✓ Match: {'Yes' if comparison['match'] else 'No'}")
    
    print("\n3. Integration points:")
    print("- Regular vision checks (every 5-10 minutes)")
    print("- Validation when sensor readings change suddenly")
    print("- Backup when sensor communication fails")
    print("- Calibration data collection")
    
    print("\n4. Files created:")
    print("- experimental/vision_readings/ - Captured images")
    print("- experimental/vision_logs/ - Comparison logs")

if __name__ == "__main__":
    demo_vision_integration()