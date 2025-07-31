#!/usr/bin/env python3
"""
Local Vision AI Module that uses Docker container
"""

import logging
import requests
import subprocess
import time
import os

class LocalVisionAI:
    """Docker-based vision AI for reading thermostat temperatures"""
    
    def __init__(self, container_name="llava-vision", port=8000):
        """
        Initialize the Docker-based vision AI
        
        Args:
            container_name: Name of the Docker container
            port: Port where the service runs
        """
        self.container_name = container_name
        self.port = port
        self.service_url = f"http://localhost:{port}"
        self.is_loaded = False
        
        logging.info(f"Initializing Docker-based LocalVisionAI on port {port}")
        
    def load_model(self):
        """Ensure Docker container is running"""
        try:
            # Check if container is already running
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={self.container_name}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                logging.info("Docker container already running")
                self.is_loaded = True
                return
                
            # Check if container exists but is stopped
            result = subprocess.run(
                ["docker", "ps", "-aq", "-f", f"name={self.container_name}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                logging.info("Starting existing Docker container")
                subprocess.run(["docker", "start", self.container_name], check=True)
            else:
                logging.info("Building and starting new Docker container")
                # Build the image
                subprocess.run(
                    ["docker", "build", "-f", "Dockerfile.llava", "-t", "llava-vision:latest", "."],
                    check=True
                )
                
                # Run the container
                subprocess.run([
                    "docker", "run", "-d",
                    "--name", self.container_name,
                    "-p", f"{self.port}:8000",
                    "llava-vision:latest"
                ], check=True)
            
            # Wait for service to be ready
            logging.info("Waiting for LLaVA service to be ready...")
            for i in range(60):  # Wait up to 60 seconds
                try:
                    response = requests.get(f"{self.service_url}/health", timeout=2)
                    if response.status_code == 200:
                        health = response.json()
                        if health.get('model_loaded'):
                            logging.info("LLaVA service is ready")
                            self.is_loaded = True
                            return
                except:
                    pass
                time.sleep(1)
                
            raise Exception("LLaVA service failed to start")
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Docker command failed: {e}")
            raise
        except Exception as e:
            logging.error(f"Failed to start Docker container: {e}")
            raise
            
    def extract_temperature(self, image_path):
        """
        Extract temperature from thermostat image
        
        Args:
            image_path: Path to the thermostat image
            
        Returns:
            dict: {'temperature': int, 'confidence': str, 'raw_response': str}
        """
        if not self.is_loaded:
            self.load_model()
            
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
                
            # Send to Docker service
            response = requests.post(
                f"{self.service_url}/extract_temperature",
                data=image_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Service returned status {response.status_code}")
                return {
                    'temperature': None,
                    'confidence': 'ERROR',
                    'raw_response': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logging.error(f"Error extracting temperature: {e}")
            return {
                'temperature': None,
                'confidence': 'ERROR',
                'raw_response': str(e)
            }
            
    def cleanup(self):
        """Stop the Docker container"""
        try:
            subprocess.run(["docker", "stop", self.container_name], check=True)
            logging.info("Docker container stopped")
        except:
            pass
        self.is_loaded = False


def test_docker_vision_ai(image_path):
    """Test function for the Docker-based vision AI"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize and test the vision AI
        vision_ai = LocalVisionAI()
        result = vision_ai.extract_temperature(image_path)
        
        print(f"Temperature: {result['temperature']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Raw response: {result['raw_response']}")
        
        # Don't cleanup during test so container stays running
        # vision_ai.cleanup()
        return result
        
    except Exception as e:
        print(f"Test failed: {e}")
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_docker_vision_ai(sys.argv[1])
    else:
        print("Usage: python local_vision_ai_docker.py <image_path>")