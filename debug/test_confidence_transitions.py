#\!/usr/bin/env python3
"""
Test confidence transitions over time
"""
import sys
sys.path.insert(0, '/home/jason/smart-thermostat')
from vision_state import save_state, get_current_vision_data, calculate_confidence
from datetime import datetime, timedelta
import json

print("Testing confidence transitions...")
print("=" * 60)

# Test different time ranges
test_cases = [
    (0, "HIGH"),       # 0 seconds ago
    (25, "HIGH"),      # 25 seconds ago
    (45, "MEDIUM"),    # 45 seconds ago
    (90, "LOW"),       # 90 seconds ago
    (400, "STALE"),    # 400 seconds ago
]

for seconds_ago, expected in test_cases:
    # Create a timestamp from the past
    timestamp = datetime.now() - timedelta(seconds=seconds_ago)
    
    # Save state with this timestamp
    save_state(76, timestamp)
    
    # Get current data
    data = get_current_vision_data()
    
    print(f"\nTime: {seconds_ago}s ago")
    print(f"Expected: {expected}, Got: {data['confidence']}")
    print(f"✓ PASS" if data['confidence'] == expected else f"✗ FAIL")

print("\n" + "=" * 60)
print("All confidence transitions tested!")