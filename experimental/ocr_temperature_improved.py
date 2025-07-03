#!/usr/bin/env python3
"""
Improved OCR temperature detection with region of interest (ROI) focus
"""
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import os

def find_temperature_region(image):
    """Find the region containing the temperature display"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # The temperature display appears to be in the center-upper portion
    # Based on the image, let's focus on that area
    height, width = gray.shape
    
    # Define ROI - adjust these values based on your thermostat
    roi_y_start = int(height * 0.15)  # Start 15% from top
    roi_y_end = int(height * 0.55)    # End 55% from top
    roi_x_start = int(width * 0.25)   # Start 25% from left
    roi_x_end = int(width * 0.75)     # End 75% from left
    
    roi = gray[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
    
    return roi, (roi_x_start, roi_y_start, roi_x_end, roi_y_end)

def preprocess_lcd_display(roi):
    """Preprocessing specifically for LCD/LED displays"""
    # Apply bilateral filter to reduce noise while keeping edges sharp
    filtered = cv2.bilateralFilter(roi, 9, 75, 75)
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(filtered)
    
    # Apply threshold with different methods
    _, binary1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Try adaptive threshold as well
    binary2 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 15, 10)
    
    # Morphological operations to clean up
    kernel = np.ones((2,2), np.uint8)
    cleaned1 = cv2.morphologyEx(binary1, cv2.MORPH_CLOSE, kernel)
    cleaned2 = cv2.morphologyEx(binary2, cv2.MORPH_CLOSE, kernel)
    
    return enhanced, cleaned1, cleaned2

def extract_temperature_from_roi(roi_image, debug_name=""):
    """Extract temperature from ROI using multiple OCR configurations"""
    results = []
    
    # Different Tesseract configurations to try
    configs = [
        # Single text line
        r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',
        # Single word
        r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',
        # Sparse text
        r'--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789',
        # Single uniform block
        r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789',
    ]
    
    for i, config in enumerate(configs):
        try:
            text = pytesseract.image_to_string(roi_image, config=config).strip()
            if text:
                # Look for 2-3 digit numbers
                numbers = re.findall(r'\d{2,3}', text)
                if numbers:
                    # Filter reasonable temperature values (50-90°F)
                    valid_temps = [int(n) for n in numbers if 50 <= int(n) <= 90]
                    if valid_temps:
                        results.append({
                            'config': f'PSM{config.split("psm")[1].split()[0]}',
                            'temperature': valid_temps[0],
                            'raw_text': text
                        })
        except Exception as e:
            pass
    
    return results

def analyze_thermostat_image(image_path):
    """Comprehensive analysis focusing on temperature extraction"""
    print(f"\nAnalyzing: {image_path}")
    print("-" * 60)
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print("Failed to load image")
        return None
    
    # Find temperature region
    roi, (x1, y1, x2, y2) = find_temperature_region(image)
    
    # Save ROI for debugging
    debug_dir = "experimental/debug_images"
    os.makedirs(debug_dir, exist_ok=True)
    base_name = os.path.basename(image_path).split('.')[0]
    
    cv2.imwrite(f"{debug_dir}/{base_name}_roi.jpg", roi)
    
    # Draw ROI on original image
    image_with_roi = image.copy()
    cv2.rectangle(image_with_roi, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(image_with_roi, "ROI", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                0.9, (0, 255, 0), 2)
    cv2.imwrite(f"{debug_dir}/{base_name}_roi_marked.jpg", image_with_roi)
    
    # Apply preprocessing
    enhanced, binary1, binary2 = preprocess_lcd_display(roi)
    
    # Save preprocessed images
    cv2.imwrite(f"{debug_dir}/{base_name}_enhanced.jpg", enhanced)
    cv2.imwrite(f"{debug_dir}/{base_name}_binary1.jpg", binary1)
    cv2.imwrite(f"{debug_dir}/{base_name}_binary2.jpg", binary2)
    
    # Try OCR on different preprocessed versions
    all_results = []
    
    print("\nOCR Results:")
    print("-" * 40)
    
    # Original ROI
    results = extract_temperature_from_roi(roi, "original")
    if results:
        print(f"Original ROI: {results}")
        all_results.extend(results)
    
    # Enhanced
    results = extract_temperature_from_roi(enhanced, "enhanced")
    if results:
        print(f"Enhanced: {results}")
        all_results.extend(results)
    
    # Binary versions
    results = extract_temperature_from_roi(binary1, "binary1")
    if results:
        print(f"Binary1 (OTSU): {results}")
        all_results.extend(results)
    
    results = extract_temperature_from_roi(binary2, "binary2")
    if results:
        print(f"Binary2 (Adaptive): {results}")
        all_results.extend(results)
    
    # Find most common temperature reading
    if all_results:
        temps = [r['temperature'] for r in all_results]
        most_common = max(set(temps), key=temps.count)
        confidence = temps.count(most_common) / len(temps)
        
        print(f"\nMost likely temperature: {most_common}°F")
        print(f"Confidence: {confidence*100:.1f}% ({temps.count(most_common)}/{len(temps)} detections)")
        
        return {
            'temperature': most_common,
            'confidence': confidence,
            'all_detections': temps
        }
    else:
        print("\nNo temperature detected")
        return None

def test_on_latest_capture():
    """Test on the latest captured image"""
    latest_path = "experimental/captured_frames/latest.jpg"
    
    if os.path.exists(latest_path):
        result = analyze_thermostat_image(latest_path)
        return result
    else:
        print(f"No image found at {latest_path}")
        return None

if __name__ == "__main__":
    test_on_latest_capture()