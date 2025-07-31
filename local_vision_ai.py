#!/usr/bin/env python3
"""
Local Vision AI Module using EasyOCR + AI reasoning for Temperature Reading
Replaces Claude API calls with local OCR + validation
"""

import logging
import re
import cv2
import numpy as np
from PIL import Image
import subprocess
import os

class LocalVisionAI:
    """Local OCR-based vision AI for reading thermostat temperatures"""
    
    def __init__(self, ocr_method="easyocr"):
        """
        Initialize the local vision AI
        
        Args:
            ocr_method: OCR method to use ('easyocr', 'tesseract')
        """
        self.ocr_method = ocr_method
        self.is_loaded = False
        
        logging.info(f"Initializing LocalVisionAI with OCR method: {ocr_method}")
        
    def load_model(self):
        """Load/initialize the OCR system"""
        try:
            if self.ocr_method == "easyocr":
                try:
                    import easyocr
                    self.reader = easyocr.Reader(['en'])
                    logging.info("EasyOCR initialized successfully")
                except ImportError:
                    logging.warning("EasyOCR not available, falling back to tesseract")
                    self.ocr_method = "tesseract"
                    
            if self.ocr_method == "tesseract":
                # Check if tesseract is available
                result = subprocess.run(['which', 'tesseract'], capture_output=True)
                if result.returncode != 0:
                    raise Exception("Tesseract not found")
                logging.info("Tesseract OCR initialized successfully")
                
            self.is_loaded = True
            
        except Exception as e:
            logging.error(f"Failed to initialize OCR: {e}")
            self.is_loaded = False
            raise
            
    def extract_temperature(self, image_path):
        """
        Extract temperature from thermostat image using OCR
        
        Args:
            image_path: Path to the thermostat image
            
        Returns:
            dict: {'temperature': int, 'confidence': str, 'raw_response': str}
        """
        if not self.is_loaded:
            self.load_model()
            
        try:
            # Try multiple preprocessing approaches
            processed_images = self._preprocess_image_multiple(image_path)
            
            best_result = None
            best_confidence = 'LOW'
            
            # Try OCR on each processed image
            for name, processed_image in processed_images:
                try:
                    if self.ocr_method == "easyocr":
                        results = self.reader.readtext(processed_image)
                        raw_text = " ".join([result[1] for result in results])
                    else:  # tesseract
                        import pytesseract
                        raw_text = pytesseract.image_to_string(processed_image, config='--psm 6 -c tessedit_char_whitelist=0123456789')
                    
                    logging.info(f"OCR text from {name}: '{raw_text}'")
                    
                    # Parse temperature from this approach
                    result = self._parse_temperature_response(raw_text)
                    
                    # Keep the best result
                    if result['temperature'] is not None and (best_result is None or result['confidence'] == 'HIGH'):
                        best_result = result
                        best_result['raw_response'] = f"{name}: {raw_text}"
                        best_confidence = result['confidence']
                        
                        # If we got a high confidence result, stop trying
                        if result['confidence'] == 'HIGH':
                            break
                            
                except Exception as e:
                    logging.warning(f"OCR failed for {name}: {e}")
                    continue
            
            # Return best result or a failure result
            if best_result:
                return best_result
            else:
                return {
                    'temperature': None,
                    'confidence': 'LOW',
                    'raw_response': 'No temperature detected in any processed image'
                }
            
        except Exception as e:
            logging.error(f"Error extracting temperature: {e}")
            return {
                'temperature': None,
                'confidence': 'ERROR',
                'raw_response': str(e)
            }
            
    def _preprocess_image_multiple(self, image_path):
        """
        Preprocess image for better OCR accuracy
        
        Args:
            image_path: Path to the image
            
        Returns:
            list: List of (name, processed_image) tuples
        """
        # Load image
        image = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Try different preprocessing approaches
        processed_images = []
        
        # Approach 1: Basic preprocessing
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(('otsu', thresh1))
        
        # Approach 2: Adaptive threshold
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        processed_images.append(('adaptive', adaptive))
        
        # Approach 3: Simple threshold
        _, thresh2 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        processed_images.append(('simple', thresh2))
        
        # Resize all images for better OCR and save debug images
        final_images = []
        for name, img in processed_images:
            # Resize for better OCR (make it larger)
            height, width = img.shape
            resized = cv2.resize(img, (width * 4, height * 4), interpolation=cv2.INTER_CUBIC)
            final_images.append((name, resized))
            
            # Save debug image
            debug_path = f"/tmp/debug_{name}.jpg"
            cv2.imwrite(debug_path, resized)
            logging.info(f"Saved debug image: {debug_path}")
        
        return final_images
            
    def _parse_temperature_response(self, response):
        """
        Parse temperature from model response
        
        Args:
            response: Raw model response string
            
        Returns:
            dict: {'temperature': int, 'confidence': str}
        """
        # Clean the response
        response = response.strip().lower()
        
        # Try to extract numbers from the response
        numbers = re.findall(r'\b\d{1,2}\b', response)
        
        if not numbers:
            return {'temperature': None, 'confidence': 'LOW'}
            
        # Take the first reasonable temperature number
        for num_str in numbers:
            try:
                temp = int(num_str)
                if 50 <= temp <= 90:  # Valid thermostat range
                    # Determine confidence based on response clarity
                    confidence = self._assess_confidence(response, temp)
                    return {'temperature': temp, 'confidence': confidence}
            except ValueError:
                continue
                
        # If we found numbers but none in valid range
        if numbers:
            return {'temperature': None, 'confidence': 'LOW'}
            
        return {'temperature': None, 'confidence': 'LOW'}
        
    def _assess_confidence(self, response, temperature):
        """
        Assess confidence level based on response characteristics
        
        Args:
            response: Model response string
            temperature: Extracted temperature value
            
        Returns:
            str: Confidence level ('HIGH', 'MEDIUM', 'LOW')
        """
        response_lower = response.lower()
        
        # High confidence indicators
        high_confidence_patterns = [
            f'^{temperature}$',  # Just the number
            f'^{temperature}°',  # Number with degree symbol
            f'^{temperature}°f',  # Number with °F
            f'^{temperature} degrees',  # Number with "degrees"
        ]
        
        for pattern in high_confidence_patterns:
            if re.match(pattern, response_lower):
                return 'HIGH'
                
        # Medium confidence - number appears clearly but with some extra text
        if str(temperature) in response and len(response.split()) <= 3:
            return 'MEDIUM'
            
        # Low confidence - number found but response is unclear
        return 'LOW'
        
    def cleanup(self):
        """Clean up OCR resources"""
        if hasattr(self, 'reader'):
            del self.reader
            
        self.is_loaded = False
        logging.info("LocalVisionAI cleaned up")


def test_local_vision_ai(image_path):
    """Test function for the local vision AI"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize and test the vision AI
        vision_ai = LocalVisionAI()
        result = vision_ai.extract_temperature(image_path)
        
        print(f"Temperature: {result['temperature']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Raw response: {result['raw_response']}")
        
        vision_ai.cleanup()
        return result
        
    except Exception as e:
        print(f"Test failed: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_local_vision_ai(sys.argv[1])
    else:
        print("Usage: python local_vision_ai.py <image_path>")