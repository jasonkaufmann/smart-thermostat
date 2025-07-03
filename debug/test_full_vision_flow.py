#\!/usr/bin/env python3
"""
Test the full vision flow end-to-end
"""
import requests
import time
import json

print("Testing full vision flow...")
print("=" * 60)

# 1. Clear state
import os
state_file = "experimental/vision_state.json"
if os.path.exists(state_file):
    os.remove(state_file)
    print("1. Cleared state file")

# 2. Check initial state via API
print("\n2. Initial API state:")
response = requests.get("http://blade:5000/vision_temperature_data")
data = response.json()
print(f"Temperature: {data.get('current_temp')}")
print(f"Confidence: {data.get('confidence')}")

# 3. Trigger vision detection
print("\n3. Triggering vision detection...")
response = requests.get("http://blade:5000/vision_annotated_image", timeout=30)
print(f"Image request status: {response.status_code}")

# 4. Check state after detection
time.sleep(1)
print("\n4. API state after detection:")
response = requests.get("http://blade:5000/vision_temperature_data")
data = response.json()
print(f"Temperature: {data.get('current_temp')}")
print(f"Confidence: {data.get('confidence')}")
print(f"Last update: {data.get('last_update')}")

# 5. Check state file directly
print("\n5. State file check:")
if os.path.exists(state_file):
    with open(state_file, 'r') as f:
        state = json.load(f)
    print(f"State file: {json.dumps(state, indent=2)}")
else:
    print("No state file\!")

print("\n" + "=" * 60)