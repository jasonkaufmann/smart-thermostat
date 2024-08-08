import cv2
import pytesseract
import easyocr
import re
import time
import subprocess
from google.cloud import vision
import os
import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Set up environment for Google Cloud
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/jason/spry-dispatcher-431803-j9-a4231b20a967.json'

def process_image(frame):
    """
    Processes the image and extracts numbers.

    Parameters:
    - frame: The image frame to process.
    
    Returns:
    - int: The extracted number or an indication of processing.
    """

    # Save the pre-OCR image for review
    cv2.imwrite('latest_photo.jpg', frame)  # Saves the cropped image
    
    # Convert the image to grayscale
    # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Improve contrast via histogram equalization
    # equ = cv2.equalizeHist(frame)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)

    # Define the region of interest (ROI) for cropping
    x, y, w, h = 165, 180, 250, 200  # Adjust these coordinates as needed
    cropped = blurred[y:y+h, x:x+w]

    # Save the pre-OCR image for review
    cv2.imwrite('pre_ocr_image.jpg', cropped)  # Saves the cropped image

    # Use Google Cloud Vision with a timeout
    content = cv2.imencode('.jpg', cropped)[1].tobytes()
    image = vision.Image(content=content)

    return 1

def main(use_old):
    """
    Main function to handle video capture and processing.

    Parameters:
    - use_old: Boolean indicating whether to use the old image.
    """

    transfer_count = 0  # Initialize transfer counter

    # Check if we should use the old image
    if use_old:
        # Load the existing latest photo
        print("Using the old latest_photo.jpg")
        frame = cv2.imread('latest_photo.jpg')
        if frame is None:
            print("Error: Could not load latest_photo.jpg. Exiting...")
            return
        detected_number = process_image(frame)
    else:
        # Initialize video capture from the stream
        cap = cv2.VideoCapture('http://10.0.0.54:5001/video_feed')

        # Main loop to process video frames
        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            
            if not ret:
                print("Failed to grab frame. Exiting...")
                break

            detected_number = process_image(frame)
            # Wait for 12 seconds
            time.sleep(12)

        # Release the video capture object
        cap.release()

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Process video stream and extract numbers.')
    parser.add_argument('--use-old', action='store_true', help='Use the old latest_photo image')
    args = parser.parse_args()

    # Call the main function with the command-line argument
    main(args.use_old)
