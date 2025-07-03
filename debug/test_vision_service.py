#!/usr/bin/env python3
"""
Test script for the vision temperature service
"""

import time
import subprocess
import sys
from read_vision_temperature import get_vision_temperature, format_temperature_display

def test_service():
    print("Testing Vision Temperature Service...")
    print("-" * 50)
    
    # Start the service in the background
    print("Starting service...")
    service_process = subprocess.Popen(
        [sys.executable, "vision_temperature_service.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Give the service time to start and make initial reading
        print("Waiting for initial reading...")
        time.sleep(5)
        
        # Test reading the temperature
        print("\nReading temperature data:")
        for i in range(3):
            data = get_vision_temperature()
            print(f"\nAttempt {i+1}:")
            print(f"  Temperature: {data.get('temperature')}°F")
            print(f"  Confidence: {data.get('confidence')}")
            print(f"  Age: {data.get('age_seconds', 'N/A')} seconds")
            print(f"  Display: {format_temperature_display()}")
            
            if data.get('error'):
                print(f"  Error: {data['error']}")
            
            time.sleep(2)
            
    finally:
        # Stop the service
        print("\n\nStopping service...")
        service_process.terminate()
        service_process.wait(timeout=5)
        print("Service stopped")

if __name__ == "__main__":
    test_service()