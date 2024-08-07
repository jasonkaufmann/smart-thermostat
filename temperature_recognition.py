import cv2
import pytesseract
import easyocr
import re
from google.cloud import vision
import io
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/jason/spry-dispatcher-431803-j9-a4231b20a967.json'
# Set the path to the tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Adjust based on your installation path

# Initialize Google Vision client
client = vision.ImageAnnotatorClient()

# Load the image
image = cv2.imread('latest_photo.jpg')  # Ensure correct path to the image

# Convert the image to grayscale
#gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Improve contrast via histogram equalization
#equ = cv2.equalizeHist(gray)

# Apply Gaussian blur to reduce noise
#blurred = cv2.GaussianBlur(equ, (5, 5), 0)

# Define the region of interest (ROI) for cropping
x, y, w, h = 600, 0, 500, 500  # Adjust these coordinates as needed
cropped = image[y:y+h, x:x+w]

# Save the pre-OCR image for review
cv2.imwrite('pre_ocr_image.jpg', cropped)  # Saves the cropped image

# Use Tesseract to extract text
text_tesseract = pytesseract.image_to_string(cropped, config='--psm 6 digits')
numeric_text_tesseract = re.sub(r'\D', '', text_tesseract)

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)
result_easyocr = reader.readtext(cropped)
numeric_text_easyocr = ''.join([re.sub(r'\D', '', str(res[1])) for res in result_easyocr])

# Use Google Cloud Vision
content = cv2.imencode('.jpg', cropped)[1].tobytes()
image = vision.Image(content=content)
response = client.text_detection(image=image)
texts = response.text_annotations
google_text = ''.join([re.sub(r'\D', '', text.description) for text in texts])

print("Detected numbers by Tesseract:", numeric_text_tesseract)
print("Detected numbers by EasyOCR:", numeric_text_easyocr)
print("Detected numbers by Google Vision:", google_text if texts else "No text found")
