#!/usr/bin/env python3
"""Direct test of Claude vision calls"""
import sys
import os
sys.path.insert(0, '/home/jason/smart-thermostat')

# First capture an image
import requests
from datetime import datetime

print("1. Capturing current thermostat image...")
response = requests.get('http://blade:5000/video_feed', stream=True, timeout=10)
if response.status_code == 200:
    bytes_data = bytes()
    for chunk in response.iter_content(chunk_size=1024):
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')
        if a != -1 and b != -1:
            jpg_data = bytes_data[a:b+2]
            test_image = f'experimental/test_claude_{datetime.now().strftime("%H%M%S")}.jpg'
            os.makedirs('experimental', exist_ok=True)
            with open(test_image, 'wb') as f:
                f.write(jpg_data)
            print(f"   Saved: {test_image}")
            break

print("\n2. Testing Claude vision call...")
from vision_integration import get_claude_temperature

print(f"   Calling get_claude_temperature('{test_image}')")
print("   Watch for [CLAUDE CMD] output below:")
print("-"*60)

temp = get_claude_temperature(test_image)

print("-"*60)
print(f"\n   Result: {temp}°F")

# Check if the function is using cache
from vision_integration import last_claude_time, last_claude_reading
if last_claude_time:
    print(f"\n3. Cache info:")
    print(f"   Last reading: {last_claude_reading}°F")
    print(f"   Last time: {last_claude_time}")
    print(f"   Seconds ago: {(datetime.now() - last_claude_time).total_seconds()}")
    print("   (Claude is called only if >30 seconds have passed)")