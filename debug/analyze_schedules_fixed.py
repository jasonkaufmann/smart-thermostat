#!/usr/bin/env python3
import sqlite3
import datetime
import pytz

# Connect to the database
conn = sqlite3.connect('thermostat_schedules.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all schedules
cursor.execute('SELECT * FROM schedules ORDER BY time')
schedules = cursor.fetchall()

print("=== All Schedules (Times are in PST/PDT) ===\n")
print(f"{'Time':<6} {'Temp':<5} {'Mode':<6} {'Enabled':<8}")
print("-" * 30)

for schedule in schedules:
    enabled = 'Yes' if schedule['enabled'] else 'No'
    print(f"{schedule['time']:<6} {schedule['temperature']:<5} {schedule['mode']:<6} {enabled:<8}")

print("\n=== Key Finding: All schedules are executing exactly 7 hours late! ===")
print("\nScheduled Time -> Actual Execution Time:")
print("06:00 (6 AM)  -> 13:00 (1 PM)")
print("09:30 (9:30 AM) -> 16:30 (4:30 PM)")
print("12:30 (12:30 PM) -> 19:30 (7:30 PM)")
print("16:00 (4 PM) -> 23:00 (11 PM)")
print("21:00 (9 PM) -> 04:00 (4 AM next day)")
print("23:00 (11 PM) -> 06:00 (6 AM next day)")

print("\n=== Timezone Analysis ===")

# Check system and timezone info
import time
import os

print(f"System timezone (TZ env): {os.environ.get('TZ', 'Not set')}")
print(f"System time: {datetime.datetime.now()}")
print(f"UTC time: {datetime.datetime.utcnow()}")

# Check PDT time
pdt = pytz.timezone('US/Pacific')
pdt_now = datetime.datetime.now(pdt)
print(f"PDT time: {pdt_now.strftime('%Y-%m-%d %H:%M:%S %Z (UTC%z)')}")

# Calculate offset
local_now = datetime.datetime.now()
utc_now = datetime.datetime.utcnow()
offset_seconds = (local_now - utc_now).total_seconds()
offset_hours = round(offset_seconds / 3600)
print(f"\nSystem clock offset from UTC: {offset_hours:+d} hours")

print("\n=== Diagnosis ===")
print("The 7-hour delay indicates the scheduler is running with UTC time")
print("while the schedules are configured for PDT (UTC-7).")
print("\nDuring summer (PDT), Pacific Time is UTC-7")
print("So when a schedule is set for 6:00 AM PDT,")
print("it executes at 6:00 AM UTC, which is 1:00 PM PDT (7 hours later)")

print("\n=== Solution ===")
print("The scheduler needs to be timezone-aware and execute schedules")
print("in Pacific Time rather than UTC.")

# Let's check how the scheduler determines execution times
print("\n=== Checking scheduler.py timezone configuration ===")
with open('scheduler.py', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[15:25], 15):  # Check around line 20
        if 'timezone' in line.lower() or 'LOCAL_TIMEZONE' in line:
            print(f"Line {i}: {line.strip()}")

conn.close()