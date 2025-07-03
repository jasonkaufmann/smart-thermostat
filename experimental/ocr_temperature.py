#!/usr/bin/env python3
"""
OCR-based temperature detection from thermostat display images
Tests different OCR approaches to extract temperature readings
"""
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import os

def preprocess_for_ocr(image, method="basic"):
    """Preprocess image for better OCR results"""
    
    if method == "basic":
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        return binary
    
    elif method == "adaptive":
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)
        
        return binary
    
    elif method == "enhanced":
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply OTSU thresholding
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.medianBlur(binary, 3)
        
        return denoised
    
    elif method == "inverted":
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Invert colors (white text on black background)
        inverted = cv2.bitwise_not(gray)
        
        # Apply threshold
        _, binary = cv2.threshold(inverted, 127, 255, cv2.THRESH_BINARY)
        
        return binary

def extract_temperature_tesseract(image, preprocessing="basic"):
    """Extract temperature using Tesseract OCR"""
    
    # Preprocess image
    processed = preprocess_for_ocr(image, preprocessing)
    
    # Configure Tesseract
    # PSM 7: Treat the image as a single text line
    # PSM 8: Treat the image as a single word
    # PSM 11: Sparse text. Find as much text as possible in no particular order
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.-°F'
    
    try:
        # Run OCR
        text = pytesseract.image_to_string(processed, config=custom_config)
        
        # Try to extract temperature pattern (e.g., "72", "72°", "72°F")
        temp_pattern = r'(\d{1,3})'
        matches = re.findall(temp_pattern, text)
        
        if matches:
            return int(matches[0]), text.strip()
        else:
            return None, text.strip()
            
    except Exception as e:
        print(f"OCR error: {e}")
        return None, ""

def detect_seven_segment_display(image):
    """Detect seven-segment display regions in the image"""
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours that might be digit segments
    digit_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filter by aspect ratio and size
        aspect_ratio = w / float(h)
        if 0.3 < aspect_ratio < 0.8 and h > 20:  # Typical digit proportions
            digit_regions.append((x, y, w, h))
    
    return digit_regions

def analyze_temperature_display(image_path):
    """Comprehensive analysis of temperature display"""
    
    print(f"\nAnalyzing image: {image_path}")
    print("-" * 50)
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print("Failed to load image")
        return
    
    print(f"Image shape: {image.shape}")
    
    results = {}
    
    # Try different preprocessing methods
    methods = ["basic", "adaptive", "enhanced", "inverted"]
    
    for method in methods:
        temp, raw_text = extract_temperature_tesseract(image, method)
        results[method] = {
            "temperature": temp,
            "raw_text": raw_text
        }
        print(f"\n{method.capitalize()} preprocessing:")
        print(f"  Detected temperature: {temp}")
        print(f"  Raw OCR text: '{raw_text}'")
    
    # Save preprocessed images for debugging
    debug_dir = "experimental/debug_images"
    os.makedirs(debug_dir, exist_ok=True)
    
    for method in methods:
        processed = preprocess_for_ocr(image, method)
        cv2.imwrite(f"{debug_dir}/{os.path.basename(image_path)}_{method}.jpg", processed)
    
    # Detect potential digit regions
    digit_regions = detect_seven_segment_display(image)
    print(f"\nDetected {len(digit_regions)} potential digit regions")
    
    # Draw bounding boxes on original image
    image_with_boxes = image.copy()
    for x, y, w, h in digit_regions:
        cv2.rectangle(image_with_boxes, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    cv2.imwrite(f"{debug_dir}/{os.path.basename(image_path)}_boxes.jpg", image_with_boxes)
    
    return results

if __name__ == "__main__":
    # Check if we have captured images
    captured_dir = "experimental/captured_frames"
    
    if os.path.exists(f"{captured_dir}/latest.jpg"):
        print("Analyzing video feed capture...")
        analyze_temperature_display(f"{captured_dir}/latest.jpg")
    
    if os.path.exists(f"{captured_dir}/latest_endpoint.jpg"):
        print("\n\nAnalyzing endpoint image...")
        analyze_temperature_display(f"{captured_dir}/latest_endpoint.jpg")
    
    if not os.path.exists(captured_dir) or len(os.listdir(captured_dir)) == 0:
        print("No captured images found. Please run capture_frame.py first.")