import cv2
import pytesseract
import easyocr
import re
import time
import subprocess
from google.cloud import vision
import os

# Set up environment for Google Cloud
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/jason/spry-dispatcher-431803-j9-a4231b20a967.json'

# Initialize Google Vision client
client = vision.ImageAnnotatorClient()

# Function to process the image and extract numbers
def process_image():
    # Load the image
    image = cv2.imread('latest_photo.jpg')  # Ensure correct path to the image

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Improve contrast via histogram equalization
    equ = cv2.equalizeHist(gray)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(equ, (5, 5), 0)

    # Define the region of interest (ROI) for cropping
    x, y, w, h = 200, 100, 500, 500  # Adjust these coordinates as needed
    cropped = blurred[y:y+h, x:x+w]

    # Save the pre-OCR image for review
    cv2.imwrite('pre_ocr_image.jpg', cropped)  # Saves the cropped image

    # Use Google Cloud Vision
    content = cv2.imencode('.jpg', cropped)[1].tobytes()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    google_text = ''.join([re.sub(r'\D', '', text.description) for text in texts])

    # Keep only the last two digits if four or more are detected
    if len(google_text) >= 4:
        detected_number = google_text[-2:]
    elif len(google_text) >= 2:
        detected_number = google_text[:2]
    else:
        detected_number = ""

    print("Detected numbers by Google Vision:", detected_number if texts else "No text found")
    return detected_number

# Function to transfer the detected number via SCP
def transfer_number(number):
    if 50 <= int(number) <= 99:
        # Write the number to a temporary file
        with open('temp_number.txt', 'w') as f:
            f.write(number)

        # Use SCP to transfer the number to the remote server
        command = "scp -o StrictHostKeyChecking=no temp_number.txt 10.0.0.54:/home/jason/smart-thermostat/temp.txt"
        subprocess.run(command, shell=True)
        print(f"Transferred number {number} to remote server.")

        # Remove the temporary file
        os.remove('temp_number.txt')
    else:
        print(f"Number {number} is not valid.")

# Main loop to run every 30 seconds
while True:
    detected_number = process_image()
    if detected_number.isdigit():
        transfer_number(detected_number)
    else:
        print("No valid number detected.")
    
    # Wait for 30 seconds
    time.sleep(12)
