#!/usr/bin/env python3
from datetime import datetime
import pytz

# Check current time
pst = pytz.timezone('US/Pacific')
now_pst = datetime.now(pst)
now_utc = datetime.utcnow()

print(f"Current PST time: {now_pst}")
print(f"Current UTC time: {now_utc}")
print(f"Time difference: {(now_utc - now_pst.replace(tzinfo=None)).total_seconds() / 3600} hours")

# Check the timestamp format
timestamp_str = "2025-07-03T01:15:48"
parsed = datetime.fromisoformat(timestamp_str)
print(f"\nParsed timestamp: {parsed}")
print(f"Is this in the past? {parsed < datetime.now()}")

# Check vision state file
try:
    import json
    with open("experimental/vision_state.json", "r") as f:
        state = json.load(f)
        print(f"\nVision state: {state}")
except Exception as e:
    print(f"\nError reading vision state: {e}")