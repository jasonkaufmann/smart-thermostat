#!/usr/bin/env python3
"""
Specialized OCR for seven-segment displays using template matching
"""
import cv2
import numpy as np
import os
from datetime import datetime

def create_seven_segment_templates():
    """Create templates for seven-segment digits 0-9"""
    # Define seven-segment patterns (which segments are on for each digit)
    # Segments: top, top-right, bottom-right, bottom, bottom-left, top-left, middle
    patterns = {
        '0': [1, 1, 1, 1, 1, 1, 0],
        '1': [0, 1, 1, 0, 0, 0, 0],
        '2': [1, 1, 0, 1, 1, 0, 1],
        '3': [1, 1, 1, 1, 0, 0, 1],
        '4': [0, 1, 1, 0, 0, 1, 1],
        '5': [1, 0, 1, 1, 0, 1, 1],
        '6': [1, 0, 1, 1, 1, 1, 1],
        '7': [1, 1, 1, 0, 0, 0, 0],
        '8': [1, 1, 1, 1, 1, 1, 1],
        '9': [1, 1, 1, 1, 0, 1, 1],
    }
    
    return patterns

def preprocess_for_seven_segment(image):
    """Preprocess image specifically for seven-segment display recognition"""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(blurred)
    
    # Try to isolate the bright segments
    # Since it's light digits on dark background
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Clean up with morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return enhanced, binary, cleaned

def find_digit_contours(binary_image):
    """Find contours that could be individual digits"""
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by size and aspect ratio
    digit_contours = []
    image_height = binary_image.shape[0]
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h)
        area = cv2.contourArea(contour)
        
        # Seven-segment digits are typically taller than wide
        # and have a minimum size
        if (0.3 < aspect_ratio < 0.8 and 
            h > image_height * 0.5 and 
            area > 100):
            digit_contours.append((x, y, w, h))
    
    # Sort by x-coordinate (left to right)
    digit_contours.sort(key=lambda c: c[0])
    
    return digit_contours

def extract_temperature_with_contours(image_path, save_debug=True):
    """Extract temperature by finding and analyzing digit contours"""
    image = cv2.imread(image_path)
    if image is None:
        return None
    
    # Focus on temperature display area
    height, width = image.shape[:2]
    roi = image[int(height*0.18):int(height*0.42), 
                int(width*0.32):int(width*0.68)]
    
    # Preprocess
    enhanced, binary, cleaned = preprocess_for_seven_segment(roi)
    
    # Find digit contours
    digit_contours = find_digit_contours(cleaned)
    
    if save_debug:
        debug_dir = "experimental/debug_images/seven_segment"
        os.makedirs(debug_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save preprocessing steps
        cv2.imwrite(f"{debug_dir}/{timestamp}_roi.jpg", roi)
        cv2.imwrite(f"{debug_dir}/{timestamp}_enhanced.jpg", enhanced)
        cv2.imwrite(f"{debug_dir}/{timestamp}_binary.jpg", binary)
        cv2.imwrite(f"{debug_dir}/{timestamp}_cleaned.jpg", cleaned)
        
        # Draw contours
        contour_img = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
        for x, y, w, h in digit_contours:
            cv2.rectangle(contour_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imwrite(f"{debug_dir}/{timestamp}_contours.jpg", contour_img)
    
    print(f"Found {len(digit_contours)} potential digits")
    
    # Try OCR on individual digits
    digits = []
    for x, y, w, h in digit_contours[:2]:  # Focus on first two digits
        digit_roi = cleaned[y:y+h, x:x+w]
        
        # Make digit image larger for better OCR
        scale_factor = 3
        digit_large = cv2.resize(digit_roi, (w*scale_factor, h*scale_factor), 
                               interpolation=cv2.INTER_CUBIC)
        
        # Try OCR
        try:
            import pytesseract
            config = '--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789'  # PSM 10 = single character
            text = pytesseract.image_to_string(digit_large, config=config).strip()
            if text and text.isdigit():
                digits.append(text)
                print(f"Detected digit: {text}")
        except:
            pass
    
    if len(digits) >= 2:
        temperature = int(''.join(digits[:2]))
        if 50 <= temperature <= 90:
            return temperature
    
    return None

def analyze_with_edge_detection(image_path):
    """Alternative approach using edge detection"""
    image = cv2.imread(image_path)
    if image is None:
        return None
    
    # Focus on temperature area
    height, width = image.shape[:2]
    roi = image[int(height*0.18):int(height*0.42), 
                int(width*0.32):int(width*0.68)]
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours from edges
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create mask from significant contours
    mask = np.zeros_like(gray)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 50:  # Filter small contours
            cv2.drawContours(mask, [contour], -1, 255, -1)
    
    # Apply mask to original
    result = cv2.bitwise_and(gray, gray, mask=mask)
    
    # Save debug images
    debug_dir = "experimental/debug_images/seven_segment"
    os.makedirs(debug_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(f"{debug_dir}/{timestamp}_edges.jpg", edges)
    cv2.imwrite(f"{debug_dir}/{timestamp}_mask.jpg", mask)
    cv2.imwrite(f"{debug_dir}/{timestamp}_result.jpg", result)
    
    return result

def test_seven_segment_ocr():
    """Test the seven-segment OCR approach"""
    latest = "experimental/captured_frames/latest.jpg"
    
    if not os.path.exists(latest):
        print(f"No image found at {latest}")
        return
    
    print("Testing seven-segment OCR approach...")
    print("-" * 50)
    
    # Test contour-based approach
    temperature = extract_temperature_with_contours(latest)
    if temperature:
        print(f"\nDetected temperature: {temperature}°F")
    else:
        print("\nCould not detect temperature")
    
    # Test edge detection approach
    print("\nTrying edge detection approach...")
    analyze_with_edge_detection(latest)
    
    print(f"\nDebug images saved to experimental/debug_images/seven_segment/")

if __name__ == "__main__":
    test_seven_segment_ocr()