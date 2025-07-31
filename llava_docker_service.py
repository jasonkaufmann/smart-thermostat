#!/usr/bin/env python3
"""
LLaVA Docker Service - Runs in container to provide vision AI
"""

import json
import logging
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import base64
from PIL import Image
import io
import torch
from transformers import LlavaForConditionalGeneration, AutoProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LLaVAModel:
    """Wrapper for LLaVA model"""
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cpu"
        
    def load_model(self):
        """Load LLaVA model"""
        logging.info("Loading LLaVA model... this may take a few minutes")
        
        # Use the smaller LLaVA model
        model_id = "llava-hf/llava-1.5-7b-hf"
        
        try:
            # Load processor and model
            self.processor = AutoProcessor.from_pretrained(model_id)
            self.model = LlavaForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            ).to(self.device)
            
            logging.info("LLaVA model loaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to load model: {e}")
            # Fallback to a smaller model if the main one fails
            try:
                logging.info("Trying alternative model...")
                model_id = "llava-hf/bakLlava-v1-hf"
                self.processor = AutoProcessor.from_pretrained(model_id)
                self.model = LlavaForConditionalGeneration.from_pretrained(
                    model_id,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True
                ).to(self.device)
                logging.info("Alternative model loaded successfully")
                return True
            except Exception as e2:
                logging.error(f"Failed to load alternative model: {e2}")
                return False
    
    def extract_temperature(self, image_bytes):
        """Extract temperature from image bytes"""
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Prepare prompt
            prompt = "USER: <image>\nWhat temperature number is shown on this thermostat display? Reply with just the number.\nASSISTANT:"
            
            # Process image and prompt
            inputs = self.processor(prompt, image, return_tensors="pt").to(self.device)
            
            # Generate response
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=20,
                    do_sample=False,
                    temperature=0.1
                )
            
            # Decode response
            response = self.processor.decode(output[0], skip_special_tokens=True)
            
            # Extract temperature from response
            if "ASSISTANT:" in response:
                response = response.split("ASSISTANT:")[-1].strip()
                
            logging.info(f"Model response: '{response}'")
            
            # Parse temperature
            import re
            numbers = re.findall(r'\b\d{1,2}\b', response)
            
            if numbers:
                for num_str in numbers:
                    temp = int(num_str)
                    if 50 <= temp <= 90:
                        return {
                            'temperature': temp,
                            'confidence': 'HIGH' if len(response.split()) <= 2 else 'MEDIUM',
                            'raw_response': response
                        }
                        
            return {
                'temperature': None,
                'confidence': 'LOW',
                'raw_response': response
            }
            
        except Exception as e:
            logging.error(f"Error extracting temperature: {e}")
            return {
                'temperature': None,
                'confidence': 'ERROR',
                'raw_response': str(e)
            }


# Global model instance
model = LLaVAModel()


class VisionHandler(BaseHTTPRequestHandler):
    """HTTP handler for vision requests"""
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/extract_temperature':
            try:
                # Get content length
                content_length = int(self.headers['Content-Length'])
                
                # Read image data
                image_data = self.rfile.read(content_length)
                
                # Extract temperature
                result = model.extract_temperature(image_data)
                
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                logging.error(f"Error handling request: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    'temperature': None,
                    'confidence': 'ERROR',
                    'raw_response': str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            health = {
                'status': 'healthy' if model.model is not None else 'loading',
                'model_loaded': model.model is not None
            }
            self.wfile.write(json.dumps(health).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
    def log_message(self, format, *args):
        """Override to use logging module"""
        logging.info(f"{self.address_string()} - {format % args}")


def main():
    """Main function"""
    # Load model
    if not model.load_model():
        logging.error("Failed to load model, exiting")
        sys.exit(1)
        
    # Start HTTP server
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, VisionHandler)
    
    logging.info("LLaVA service running on port 8000")
    httpd.serve_forever()


if __name__ == "__main__":
    main()