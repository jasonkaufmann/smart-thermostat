#!/usr/bin/env python3
import json
import os
from datetime import datetime

# Create a current timestamp
now = datetime.utcnow()

# Update the vision state file with current time
state = {
    "temperature": 76,  # Keep the last known temperature
    "timestamp": now.isoformat(),
    "confidence": "STALE"  # Mark as stale since it's old
}

# Write to state file
os.makedirs("experimental", exist_ok=True)
with open("experimental/vision_state.json", "w") as f:
    json.dump(state, f)

print(f"Updated vision state with current timestamp: {state['timestamp']}")
print("This will show the correct elapsed time, but marked as STALE")