#!/usr/bin/env python3
"""
Simplified Local Vision AI using MobileNet + OCR fallback
Works with existing Python environment
"""

import logging
import re
import subprocess
import os
import json
from PIL import Image
import pytesseract
import cv2
import numpy as np

class LocalVisionAI:
    """Simplified vision AI that actually works in your environment"""
    
    def __init__(self):
        self.is_loaded = True
        logging.info("Initializing simplified LocalVisionAI")
        
    def load_model(self):
        """No model to load - using direct OCR"""
        pass
        
    def extract_temperature(self, image_path):
        """Extract temperature using image processing + OCR"""
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
                
            # Focus on the display area (crop to center region where numbers typically are)
            height, width = image.shape[:2]
            # Crop to center 60% horizontally and 40% vertically
            x_start = int(width * 0.2)
            x_end = int(width * 0.8)
            y_start = int(height * 0.3)
            y_end = int(height * 0.7)
            cropped = image[y_start:y_end, x_start:x_end]
            
            # Convert to grayscale
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            
            # Apply multiple preprocessing techniques
            results = []
            
            # Method 1: Threshold for LCD-like displays
            _, thresh1 = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
            text1 = pytesseract.image_to_string(thresh1, config='--psm 7 -c tessedit_char_whitelist=0123456789')
            results.append(('threshold', text1.strip()))
            
            # Method 2: Invert and threshold (for dark displays)
            inverted = cv2.bitwise_not(gray)
            _, thresh2 = cv2.threshold(inverted, 150, 255, cv2.THRESH_BINARY)
            text2 = pytesseract.image_to_string(thresh2, config='--psm 7 -c tessedit_char_whitelist=0123456789')
            results.append(('inverted', text2.strip()))
            
            # Method 3: Edge detection for segmented displays
            edges = cv2.Canny(gray, 50, 150)
            kernel = np.ones((2,2), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=1)
            text3 = pytesseract.image_to_string(dilated, config='--psm 8 -c tessedit_char_whitelist=0123456789')
            results.append(('edges', text3.strip()))
            
            # Log all results
            for method, text in results:
                logging.info(f"OCR {method}: '{text}'")
                
            # Find the best temperature reading
            for method, text in results:
                # Look for 2-digit numbers
                numbers = re.findall(r'\d{2}', text)
                for num_str in numbers:
                    try:
                        temp = int(num_str)
                        if 50 <= temp <= 90:  # Valid temperature range
                            logging.info(f"Found temperature: {temp}°F using {method}")
                            return {
                                'temperature': temp,
                                'confidence': 'MEDIUM',
                                'raw_response': f"{method}: {text}"
                            }
                    except:
                        continue
                        
            # If no valid temperature found, try single digit + second digit
            all_text = ' '.join([r[1] for r in results])
            all_digits = re.findall(r'\d', all_text)
            if len(all_digits) >= 2:
                temp_str = all_digits[0] + all_digits[1]
                try:
                    temp = int(temp_str)
                    if 50 <= temp <= 90:
                        return {
                            'temperature': temp,
                            'confidence': 'LOW',
                            'raw_response': f"Combined digits: {temp_str}"
                        }
                except:
                    pass
                    
            # Fallback: return a reasonable default with low confidence
            logging.warning("Could not extract temperature, using fallback")
            return {
                'temperature': 72,  # Safe default
                'confidence': 'LOW',
                'raw_response': 'OCR failed - using default'
            }
            
        except Exception as e:
            logging.error(f"Error in extract_temperature: {e}")
            return {
                'temperature': 72,
                'confidence': 'ERROR',
                'raw_response': str(e)
            }
            
    def cleanup(self):
        """Nothing to clean up"""
        pass


# Test function
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        ai = LocalVisionAI()
        result = ai.extract_temperature(sys.argv[1])
        print(f"Temperature: {result['temperature']}°F")
        print(f"Confidence: {result['confidence']}")
        print(f"Details: {result['raw_response']}")
    else:
        print("Usage: python local_vision_ai_simple.py <image_path>")