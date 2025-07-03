#\!/usr/bin/env python3
"""
Direct test of vision integration module
"""
import sys
sys.path.insert(0, '/home/jason/smart-thermostat')

from vision_integration import get_claude_temperature
import os

print("Testing vision integration directly...")
print("=" * 60)

# Test with the actual test image
test_image = "experimental/test_vision_check.jpg"

print(f"\n1. Testing get_claude_temperature with {test_image}")
result = get_claude_temperature(test_image)
print(f"Result: {result}°F")

# Check if state file was created
state_file = "experimental/vision_state.json"
print(f"\n2. Checking if state file exists: {state_file}")
if os.path.exists(state_file):
    print("State file exists\!")
    with open(state_file, 'r') as f:
        import json
        state = json.load(f)
    print(f"State contents: {json.dumps(state, indent=2)}")
else:
    print("State file NOT found\!")

# Check Claude log
log_file = "experimental/claude_vision_log.json"
print(f"\n3. Checking Claude log: {log_file}")
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        import json
        logs = json.load(f)
    print(f"Last log entry: {logs[-1] if logs else 'No entries'}")

print("\n" + "=" * 60)