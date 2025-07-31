#!/usr/bin/env python3
"""
Simple vision state updater that just keeps the timestamp current
This is a temporary fix while the main vision service is being debugged
"""

import json
import time
from datetime import datetime
import os

def update_vision_state():
    """Update the vision state file with current timestamp"""
    state_file = "experimental/vision_state.json"
    
    # Read the last known temperature
    try:
        with open(state_file, 'r') as f:
            data = json.load(f)
            last_temp = data.get('temperature', 76)
    except:
        last_temp = 76
    
    # Update with current timestamp
    state = {
        "temperature": last_temp,
        "timestamp": datetime.utcnow().isoformat(),
        "confidence": "STALE"
    }
    
    # Write the update
    os.makedirs("experimental", exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(state, f)
    
    print(f"Updated vision state at {state['timestamp']}")

def main():
    """Main loop - update every 30 seconds"""
    print("Simple vision updater started - updates every 30 seconds")
    
    while True:
        try:
            update_vision_state()
        except Exception as e:
            print(f"Error updating vision state: {e}")
        
        # Wait 30 seconds
        time.sleep(30)

if __name__ == "__main__":
    main()