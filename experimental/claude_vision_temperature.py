#!/usr/bin/env python3
"""
Use Claude's vision capabilities to read temperature from thermostat display
"""
import requests
import base64
import json
import os
from datetime import datetime
import sys

def capture_latest_frame():
    """Capture the latest frame from the thermostat"""
    try:
        # Try the video feed endpoint
        response = requests.get("http://blade:5000/video_feed", stream=True, timeout=10)
        
        if response.status_code == 200:
            bytes_data = bytes()
            for chunk in response.iter_content(chunk_size=1024):
                bytes_data += chunk
                # Look for JPEG markers
                a = bytes_data.find(b'\xff\xd8')  # JPEG start
                b = bytes_data.find(b'\xff\xd9')  # JPEG end
                
                if a != -1 and b != -1:
                    jpg_data = bytes_data[a:b+2]
                    
                    # Save the image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"experimental/claude_captures/frame_{timestamp}.jpg"
                    os.makedirs("experimental/claude_captures", exist_ok=True)
                    
                    with open(filename, 'wb') as f:
                        f.write(jpg_data)
                    
                    print(f"Captured frame: {filename}")
                    return filename, jpg_data
    except Exception as e:
        print(f"Error capturing frame: {e}")
    
    return None, None

def encode_image_base64(image_path):
    """Encode image to base64 for API calls"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def create_claude_prompt(image_path):
    """Create a prompt for Claude to read the temperature"""
    # This function prepares the image and prompt for Claude
    # In actual use, this would be sent to Claude's API
    
    prompt = """Please look at this thermostat display image and tell me:
1. What temperature is shown on the display? (just the number)
2. Is the display showing any other information like mode (HEAT/COOL/OFF)?
3. How confident are you in your reading (high/medium/low)?

Please format your response as:
Temperature: [number]
Mode: [mode if visible]
Confidence: [high/medium/low]"""
    
    return {
        "prompt": prompt,
        "image_path": image_path,
        "timestamp": datetime.now().isoformat()
    }

def save_analysis_request(image_path):
    """Save the analysis request for manual processing"""
    request_data = create_claude_prompt(image_path)
    
    # Save request data
    requests_dir = "experimental/claude_requests"
    os.makedirs(requests_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    request_file = f"{requests_dir}/request_{timestamp}.json"
    
    with open(request_file, 'w') as f:
        json.dump(request_data, f, indent=2)
    
    print(f"\nAnalysis request saved to: {request_file}")
    print(f"Image saved to: {image_path}")
    
    return request_file

def process_with_claude_cli():
    """Instructions for processing with Claude Code CLI"""
    print("\n" + "="*60)
    print("INSTRUCTIONS FOR CLAUDE VISION ANALYSIS")
    print("="*60)
    
    print("\nTo analyze the thermostat image with Claude:")
    print("\n1. The captured image has been saved to the experimental/claude_captures/ folder")
    print("\n2. You can ask Claude to analyze it by running:")
    print("   claude 'Please look at the thermostat image at experimental/claude_captures/[latest_file].jpg and tell me what temperature is displayed'")
    print("\n3. Or for a more detailed analysis:")
    print("   claude 'Analyze the seven-segment display in experimental/claude_captures/[latest_file].jpg. What temperature is shown? Also note if you can see the mode (HEAT/COOL/OFF) and how confident you are in the reading.'")
    
def main():
    """Main function to capture and prepare for Claude analysis"""
    print("Capturing thermostat display for Claude vision analysis...")
    
    # Capture frame
    image_path, image_data = capture_latest_frame()
    
    if image_path:
        # Save analysis request
        request_file = save_analysis_request(image_path)
        
        # Show instructions
        process_with_claude_cli()
        
        # Also create a simple script to check the latest capture
        latest_link = "experimental/claude_captures/latest.jpg"
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(os.path.basename(image_path), latest_link)
        
        print(f"\nLatest capture linked to: {latest_link}")
        
    else:
        print("Failed to capture frame from thermostat")
        sys.exit(1)

if __name__ == "__main__":
    main()