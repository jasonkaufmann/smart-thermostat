#!/usr/bin/env python3
"""Test script to see actual Claude commands being executed"""
import requests
import time

print("Testing Vision Commands - Watch for [CLAUDE CMD] output")
print("="*60)

# Test 1: Direct vision integration test
print("\n1. Testing vision_integration module directly...")
try:
    import os
    os.chdir('/home/jason/smart-thermostat')
    from vision_integration import get_claude_temperature
    
    # Create a test image
    test_image = "experimental/test_vision_debug.jpg"
    if os.path.exists(test_image):
        print(f"   Calling get_claude_temperature({test_image})")
        temp = get_claude_temperature(test_image)
        print(f"   Result: {temp}°F")
    else:
        print("   No test image found")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Hit the vision endpoint
print("\n2. Requesting vision annotated image from web server...")
print("   (This should trigger Claude commands)")
try:
    response = requests.get("http://blade:5000/vision_annotated_image", timeout=30)
    print(f"   Response status: {response.status_code}")
    print("   Check console output above for [CLAUDE CMD] lines")
except Exception as e:
    print(f"   Error: {e}")

print("\n3. Checking if images are being created...")
import glob
temp_images = glob.glob("/home/jason/smart-thermostat/experimental/temp_vision_*.jpg")
print(f"   Found {len(temp_images)} temp vision images")
if temp_images:
    print(f"   Latest: {sorted(temp_images)[-1]}")

print("\n" + "="*60)
print("If you don't see [CLAUDE CMD] output above, Claude is not being called!")
print("Check the thermostat service logs with:")
print("  sudo journalctl -u thermostat -f")