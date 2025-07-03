#!/usr/bin/env python3
"""
Visual analysis tool to help identify the best region and preprocessing for OCR
"""
import cv2
import numpy as np
import pytesseract
import os

def interactive_roi_selection(image_path):
    """Help identify the exact region where temperature is displayed"""
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load {image_path}")
        return
    
    height, width = image.shape[:2]
    
    print(f"Image dimensions: {width}x{height}")
    
    # Based on the captured image, the temperature seems to be:
    # - In the upper-middle portion
    # - Large seven-segment display
    
    # Let's try different ROI candidates
    roi_candidates = [
        # (name, y_start_ratio, y_end_ratio, x_start_ratio, x_end_ratio)
        ("Full temperature area", 0.15, 0.45, 0.30, 0.70),
        ("Tight digits only", 0.20, 0.40, 0.35, 0.65),
        ("Upper center", 0.10, 0.35, 0.25, 0.75),
        ("Middle third", 0.15, 0.50, 0.33, 0.66),
    ]
    
    debug_dir = "experimental/debug_images/roi_analysis"
    os.makedirs(debug_dir, exist_ok=True)
    
    results = []
    
    for name, y1_r, y2_r, x1_r, x2_r in roi_candidates:
        y1 = int(height * y1_r)
        y2 = int(height * y2_r)
        x1 = int(width * x1_r)
        x2 = int(width * x2_r)
        
        roi = image[y1:y2, x1:x2]
        
        # Save ROI
        roi_path = f"{debug_dir}/roi_{name.replace(' ', '_')}.jpg"
        cv2.imwrite(roi_path, roi)
        
        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Try multiple preprocessing methods
        preprocessing_results = []
        
        # Method 1: Simple threshold
        _, thresh1 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        cv2.imwrite(f"{debug_dir}/roi_{name.replace(' ', '_')}_thresh.jpg", thresh1)
        
        # Method 2: OTSU threshold
        _, thresh2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(f"{debug_dir}/roi_{name.replace(' ', '_')}_otsu.jpg", thresh2)
        
        # Method 3: Inverted
        inverted = cv2.bitwise_not(gray)
        _, thresh3 = cv2.threshold(inverted, 127, 255, cv2.THRESH_BINARY)
        cv2.imwrite(f"{debug_dir}/roi_{name.replace(' ', '_')}_inverted.jpg", thresh3)
        
        # Try OCR on each
        for method_name, processed in [("threshold", thresh1), ("otsu", thresh2), ("inverted", thresh3)]:
            try:
                # Try different PSM modes
                for psm in [7, 8, 13]:  # 7=single line, 8=single word, 13=raw line
                    config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=0123456789'
                    text = pytesseract.image_to_string(processed, config=config).strip()
                    
                    if text and text.isdigit() and 50 <= int(text) <= 90:
                        preprocessing_results.append({
                            'method': method_name,
                            'psm': psm,
                            'text': text,
                            'value': int(text)
                        })
            except:
                pass
        
        results.append({
            'roi_name': name,
            'bounds': (x1, y1, x2, y2),
            'detections': preprocessing_results
        })
        
        print(f"\nROI: {name}")
        print(f"  Bounds: x={x1}-{x2}, y={y1}-{y2}")
        print(f"  Size: {x2-x1}x{y2-y1}")
        if preprocessing_results:
            print(f"  Detections: {preprocessing_results}")
        else:
            print("  No valid temperature detected")
    
    # Create a summary image showing all ROIs
    summary = image.copy()
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    
    for i, (name, y1_r, y2_r, x1_r, x2_r) in enumerate(roi_candidates):
        y1 = int(height * y1_r)
        y2 = int(height * y2_r)
        x1 = int(width * x1_r)
        x2 = int(width * x2_r)
        
        color = colors[i % len(colors)]
        cv2.rectangle(summary, (x1, y1), (x2, y2), color, 2)
        cv2.putText(summary, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, color, 1)
    
    cv2.imwrite(f"{debug_dir}/all_rois.jpg", summary)
    print(f"\nSaved analysis images to {debug_dir}/")
    
    return results

def analyze_digit_characteristics(image_path):
    """Analyze the characteristics of the seven-segment display"""
    image = cv2.imread(image_path)
    if image is None:
        return
    
    # Focus on the temperature display area
    height, width = image.shape[:2]
    roi = image[int(height*0.20):int(height*0.40), 
                int(width*0.35):int(width*0.65)]
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Analyze brightness distribution
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)
    
    print(f"\nDisplay Characteristics:")
    print(f"  Mean brightness: {mean_brightness:.1f}")
    print(f"  Std deviation: {std_brightness:.1f}")
    
    # Check if display is light-on-dark or dark-on-light
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    dark_pixels = np.sum(hist[:128])
    light_pixels = np.sum(hist[128:])
    
    if dark_pixels > light_pixels:
        print("  Display type: Light digits on dark background")
    else:
        print("  Display type: Dark digits on light background")
    
    return gray, mean_brightness > 128

if __name__ == "__main__":
    latest = "experimental/captured_frames/latest.jpg"
    
    if os.path.exists(latest):
        print("Analyzing display characteristics...")
        analyze_digit_characteristics(latest)
        
        print("\n" + "="*60)
        print("Testing different ROI configurations...")
        interactive_roi_selection(latest)
    else:
        print(f"No image found at {latest}")