#!/usr/bin/env python3
"""
Comprehensive test of vision detection logic
"""
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, '/home/jason/smart-thermostat')

print("VISION DETECTION LOGIC TEST")
print("="*60)

# Test 1: Check vision_integration module state
print("\n1. CHECKING VISION_INTEGRATION MODULE:")
print("-"*40)
try:
    from vision_integration import (
        get_claude_temperature, 
        get_vision_confidence,
        last_claude_time,
        last_claude_reading
    )
    
    print(f"Last Claude reading: {last_claude_reading}")
    print(f"Last Claude time: {last_claude_time}")
    
    if last_claude_time:
        age = (datetime.now() - last_claude_time).total_seconds()
        print(f"Age of last reading: {age:.0f} seconds ({age/60:.1f} minutes)")
    
    confidence = get_vision_confidence()
    print(f"Current confidence: {confidence}")
    
except Exception as e:
    print(f"ERROR loading vision_integration: {e}")

# Test 2: Check what the endpoint returns
print("\n\n2. CHECKING /vision_temperature_data ENDPOINT:")
print("-"*40)
try:
    import requests
    response = requests.get("http://blade:5000/vision_temperature_data")
    data = response.json()
    
    print(f"Current temp: {data.get('current_temp')}")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Last update: {data.get('last_update')}")
    
    if data.get('last_update'):
        last_time = datetime.fromisoformat(data['last_update'].replace('Z', '+00:00') if 'Z' in data['last_update'] else data['last_update'])
        age = (datetime.now() - last_time).total_seconds()
        print(f"Update age: {age:.0f} seconds")
        print(f"Should be STALE (>300s)? {age > 300}")
    
    print(f"Number of history points: {len(data.get('temperatures', []))}")
    
except Exception as e:
    print(f"ERROR calling endpoint: {e}")

# Test 3: Test confidence calculation directly
print("\n\n3. TESTING CONFIDENCE CALCULATION:")
print("-"*40)
try:
    # Temporarily set different times to test confidence
    import vision_integration
    
    # Test with no data
    vision_integration.last_claude_time = None
    conf = vision_integration.get_vision_confidence()
    print(f"No data: {conf} (expected: NO_DATA)")
    
    # Test with recent data (10 seconds)
    vision_integration.last_claude_time = datetime.now() - timedelta(seconds=10)
    conf = vision_integration.get_vision_confidence()
    print(f"10 seconds old: {conf} (expected: HIGH)")
    
    # Test with medium age (45 seconds)
    vision_integration.last_claude_time = datetime.now() - timedelta(seconds=45)
    conf = vision_integration.get_vision_confidence()
    print(f"45 seconds old: {conf} (expected: MEDIUM)")
    
    # Test with old data (200 seconds)
    vision_integration.last_claude_time = datetime.now() - timedelta(seconds=200)
    conf = vision_integration.get_vision_confidence()
    print(f"200 seconds old: {conf} (expected: LOW)")
    
    # Test with stale data (400 seconds)
    vision_integration.last_claude_time = datetime.now() - timedelta(seconds=400)
    conf = vision_integration.get_vision_confidence()
    print(f"400 seconds old: {conf} (expected: STALE)")
    
except Exception as e:
    print(f"ERROR testing confidence: {e}")

# Test 4: Check if Claude is actually being called
print("\n\n4. TESTING CLAUDE CALL:")
print("-"*40)
try:
    # Create a test image
    test_image = "experimental/test_vision_check.jpg"
    
    # Try to capture current image
    import requests
    response = requests.get('http://blade:5000/video_feed', stream=True, timeout=5)
    if response.status_code == 200:
        bytes_data = bytes()
        for chunk in response.iter_content(chunk_size=1024):
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg_data = bytes_data[a:b+2]
                os.makedirs('experimental', exist_ok=True)
                with open(test_image, 'wb') as f:
                    f.write(jpg_data)
                print(f"Captured test image: {test_image}")
                break
    
    # Force a fresh Claude call by clearing cache
    vision_integration.last_claude_time = None
    vision_integration.last_claude_reading = None
    
    print("\nCalling get_claude_temperature (watch for [CLAUDE CMD] output):")
    print("-"*40)
    
    temp = get_claude_temperature(test_image)
    
    print("-"*40)
    print(f"Result: {temp}°F")
    print(f"Confidence after call: {get_vision_confidence()}")
    
except Exception as e:
    print(f"ERROR testing Claude call: {e}")

# Test 5: Check the full flow
print("\n\n5. TESTING FULL FLOW:")
print("-"*40)
try:
    # Clear the cache to force fresh detection
    vision_integration.last_claude_time = None
    
    # Request the annotated image (this should trigger Claude)
    print("Requesting /vision_annotated_image...")
    response = requests.get("http://blade:5000/vision_annotated_image", timeout=30)
    print(f"Response status: {response.status_code}")
    
    # Check what the data endpoint says now
    print("\nChecking data after image request...")
    response = requests.get("http://blade:5000/vision_temperature_data")
    data = response.json()
    print(f"Current temp: {data.get('current_temp')}")
    print(f"Confidence: {data.get('confidence')}")
    
except Exception as e:
    print(f"ERROR in full flow test: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("\nKey issues to check:")
print("1. Is last_claude_time being set properly?")
print("2. Is the confidence calculation working?")
print("3. Is Claude actually being called?")
print("4. Is the endpoint using the right confidence value?")