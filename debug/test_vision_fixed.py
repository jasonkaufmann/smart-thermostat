#!/usr/bin/env python3
"""
Test the fixed vision detection
"""
import sys
import os
import requests
import time

sys.path.insert(0, '/home/jason/smart-thermostat')

print("TESTING FIXED VISION DETECTION")
print("="*60)

# Test 1: Clear any existing state
print("\n1. Clearing old state...")
state_file = "experimental/vision_state.json"
if os.path.exists(state_file):
    os.remove(state_file)
    print("Cleared old state file")

# Test 2: Check initial state
print("\n2. Initial state check:")
response = requests.get("http://blade:5000/vision_temperature_data")
data = response.json()
print(f"Temperature: {data.get('current_temp')}")
print(f"Confidence: {data.get('confidence')}")
print("(Should be None/NO_DATA)")

# Test 3: Trigger a Claude reading
print("\n3. Triggering Claude reading via annotated image...")
response = requests.get("http://blade:5000/vision_annotated_image", timeout=30)
print(f"Image request status: {response.status_code}")

# Wait a moment for processing
time.sleep(1)

# Test 4: Check state after Claude reading
print("\n4. State after Claude reading:")
response = requests.get("http://blade:5000/vision_temperature_data")
data = response.json()
print(f"Temperature: {data.get('current_temp')}")
print(f"Confidence: {data.get('confidence')}")
print("(Should show actual temp with HIGH confidence)")

# Test 5: Check the state file
print("\n5. Checking state file:")
if os.path.exists(state_file):
    import json
    with open(state_file, 'r') as f:
        state = json.load(f)
    print(f"State file contents: {json.dumps(state, indent=2)}")
else:
    print("No state file found!")

# Test 6: Simulate stale data
print("\n6. Simulating stale data...")
if os.path.exists(state_file):
    from datetime import datetime, timedelta
    # Make the timestamp 10 minutes old
    old_time = (datetime.now() - timedelta(minutes=10)).isoformat()
    state['timestamp'] = old_time
    with open(state_file, 'w') as f:
        json.dump(state, f)
    print("Set timestamp to 10 minutes ago")

# Test 7: Check stale confidence
print("\n7. Checking stale data handling:")
response = requests.get("http://blade:5000/vision_temperature_data")
data = response.json()
print(f"Temperature: {data.get('current_temp')}")
print(f"Confidence: {data.get('confidence')}")
print("(Should show temp with STALE confidence)")

print("\n" + "="*60)
print("TEST COMPLETE")