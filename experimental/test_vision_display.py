#!/usr/bin/env python3
"""
Quick test to show annotated image with detected temperature
"""
import cv2
import numpy as np
import requests
from datetime import datetime
import os

def capture_and_annotate():
    """Capture image and add temperature annotation"""
    print("Capturing thermostat display...")
    
    try:
        # Capture from thermostat
        response = requests.get("http://blade:5000/video_feed", stream=True, timeout=10)
        
        if response.status_code == 200:
            bytes_data = bytes()
            for chunk in response.iter_content(chunk_size=1024):
                bytes_data += chunk
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')
                
                if a != -1 and b != -1:
                    jpg_data = bytes_data[a:b+2]
                    
                    # Convert to image
                    nparr = np.frombuffer(jpg_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Simulated detection (in production, use Claude)
                    detected_temp = 77
                    
                    # Annotate image
                    height, width = image.shape[:2]
                    
                    # Add semi-transparent overlay
                    overlay = image.copy()
                    cv2.rectangle(overlay, (0, height-100), (width, height), 
                                 (0, 0, 0), -1)
                    image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
                    
                    # Add temperature text
                    temp_text = f"Detected Current Temp: {detected_temp}°F"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    
                    # Center the text
                    (text_width, _), _ = cv2.getTextSize(temp_text, font, 1, 2)
                    text_x = (width - text_width) // 2
                    
                    cv2.putText(image, temp_text, (text_x, height-40), 
                               font, 1, (0, 255, 0), 2)
                    
                    # Add confidence
                    cv2.putText(image, "Confidence: HIGH", (20, height-15), 
                               font, 0.5, (0, 255, 0), 1)
                    
                    # Add timestamp
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(image, timestamp, (width-200, height-15), 
                               font, 0.5, (255, 255, 255), 1)
                    
                    # Save annotated image
                    output_dir = "experimental/annotated_samples"
                    os.makedirs(output_dir, exist_ok=True)
                    
                    output_file = f"{output_dir}/annotated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.imwrite(output_file, image)
                    
                    print(f"✓ Saved annotated image: {output_file}")
                    print(f"✓ Detected temperature: {detected_temp}°F")
                    
                    return output_file
                    
    except Exception as e:
        print(f"Error: {e}")
        
    return None

if __name__ == "__main__":
    print("Vision Temperature Display Test")
    print("="*50)
    
    result = capture_and_annotate()
    
    if result:
        print("\nSuccess! Check the annotated image at:")
        print(f"  {result}")
        print("\nThis shows how the temperature will be displayed")
        print("below the thermostat image in the live monitor.")
    else:
        print("\nFailed to capture/annotate image")
        print("Make sure the thermostat server is running")