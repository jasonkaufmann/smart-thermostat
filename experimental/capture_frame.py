#!/usr/bin/env python3
"""
Capture frame from thermostat camera feed for image recognition experiments
"""
import requests
import cv2
import numpy as np
from datetime import datetime
import os

def capture_frame_from_feed(url="http://blade:5000/video_feed", save_path="experimental/captured_frames"):
    """Capture a single frame from the video feed"""
    
    # Create directory if it doesn't exist
    os.makedirs(save_path, exist_ok=True)
    
    try:
        # Get frame from video feed
        response = requests.get(url, stream=True, timeout=10)
        
        if response.status_code == 200:
            # Read the MJPEG stream to get a single frame
            bytes_data = bytes()
            for chunk in response.iter_content(chunk_size=1024):
                bytes_data += chunk
                # Look for JPEG markers
                a = bytes_data.find(b'\xff\xd8')  # JPEG start
                b = bytes_data.find(b'\xff\xd9')  # JPEG end
                
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    
                    # Convert to numpy array and decode
                    nparr = np.frombuffer(jpg, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Save the frame
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{save_path}/frame_{timestamp}.jpg"
                        cv2.imwrite(filename, frame)
                        print(f"Frame saved: {filename}")
                        
                        # Also save as latest.jpg for easy access
                        cv2.imwrite(f"{save_path}/latest.jpg", frame)
                        
                        return filename, frame
                    break
        else:
            print(f"Failed to connect to video feed: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"Error capturing frame: {e}")
        return None, None

def get_latest_image_from_endpoint(url="http://blade:5000/latest_image", save_path="experimental/captured_frames"):
    """Get the latest image from the direct endpoint"""
    
    os.makedirs(save_path, exist_ok=True)
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{save_path}/endpoint_{timestamp}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            # Also save as latest_endpoint.jpg
            with open(f"{save_path}/latest_endpoint.jpg", 'wb') as f:
                f.write(response.content)
                
            print(f"Image saved from endpoint: {filename}")
            
            # Load with OpenCV for processing
            nparr = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return filename, frame
        else:
            print(f"Failed to get image from endpoint: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"Error getting image from endpoint: {e}")
        return None, None

if __name__ == "__main__":
    print("Attempting to capture frame from video feed...")
    filename1, frame1 = capture_frame_from_feed()
    
    print("\nAttempting to get image from endpoint...")
    filename2, frame2 = get_latest_image_from_endpoint()
    
    if frame1 is not None:
        print(f"\nVideo feed frame shape: {frame1.shape}")
        print(f"Video feed frame dtype: {frame1.dtype}")
    
    if frame2 is not None:
        print(f"\nEndpoint image shape: {frame2.shape}")
        print(f"Endpoint image dtype: {frame2.dtype}")