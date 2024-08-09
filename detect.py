import cv2
import numpy as np
import easyocr
import os
import warnings
import time

# Suppress warnings
warnings.filterwarnings("ignore")

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

# Setup retry mechanism for video capture
max_retries = 5
retry_delay = 2  # seconds
success = False

while not success and max_retries > 0:
    cap = cv2.VideoCapture('http://10.0.0.54:5001/video_feed')
    if not cap.isOpened():
        print("Unable to connect to camera. Retrying in {} seconds...".format(retry_delay))
        max_retries -= 1
        time.sleep(retry_delay)
    else:
        success = True

if not success:
    print("Failed to connect to the video stream after several attempts.")
    exit(1)

counter = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame from video stream. Exiting...")
        break

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)

    # Define the region of interest (ROI) for cropping
    x, y, w, h = 200, 200, 250, 200  # Adjust these coordinates as needed
    img = blurred[y:y+h, x:x+w]

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("gray.jpg", gray)

    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    cv2.imwrite("binary.jpg", binary)

    # Define a kernel for morphological operations
    kernel = np.ones((5, 5), np.uint8)

    # Apply morphological operations to clean the binary image
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    cv2.imwrite("cleaned.jpg", cleaned)

    # Close gaps in contours by dilating and then eroding the cleaned image
    dilated = cv2.dilate(cleaned, kernel, iterations=4)  # Dilate to close gaps
    eroded = cv2.erode(dilated, kernel, iterations=2)  # Erode to restore size

    cv2.imwrite("eroded.jpg", eroded)

    # Perform OCR
    results = reader.readtext(eroded, detail=0)  # Get only text
    extracted_text = ''.join(results)
    print(f"Extracted text: {extracted_text}")

    # Validate and process OCR result
    if extracted_text.isdigit() and len(extracted_text) == 2:
        value = int(extracted_text)
        if 60 <= value <= 80:
            # Save the valid number to temp.txt
            with open("temp.txt", "w") as file:
                file.write(extracted_text)
            
            # SCP the file to another server
            os.system("scp temp.txt jason@10.0.0.54:/home/jason/smart-thermostat")
            print("File transferred successfully.")
        else:
            print("Detected number is not within the range 50-80.")
    else:
        print("Detected text is not a two-digit number.")
    
    counter += 1
    print(f"Processed frame {counter}")
    time.sleep(4)
