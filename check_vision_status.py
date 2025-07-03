#!/usr/bin/env python3
import sqlite3
import datetime
import time

# Connect to the vision database
conn = sqlite3.connect('vision_temperatures.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Vision Temperature Status ===\n")

# Get the most recent readings
cursor.execute('''
    SELECT * FROM temperature_readings 
    ORDER BY timestamp DESC 
    LIMIT 10
''')

readings = cursor.fetchall()

if readings:
    # Show the most recent reading
    latest = readings[0]
    timestamp = datetime.datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00'))
    now = datetime.datetime.now(datetime.timezone.utc)
    age = now - timestamp
    
    print(f"Latest Reading:")
    print(f"  Temperature: {latest['temperature']}°F")
    print(f"  Confidence: {latest['confidence']}")
    print(f"  Timestamp: {latest['timestamp']}")
    print(f"  Age: {age.total_seconds():.0f} seconds ({age.total_seconds()/60:.1f} minutes)")
    print(f"  Is Stale: {'YES' if age.total_seconds() > 300 else 'NO'} (stale after 5 minutes)")
    
    print("\n=== Recent History ===")
    for reading in readings[:5]:
        print(f"{reading['timestamp']}: {reading['temperature']}°F (confidence: {reading['confidence']})")
else:
    print("No temperature readings found in database!")

# Check for any error logs
cursor.execute('''
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE '%log%' OR name LIKE '%error%'
''')
log_tables = cursor.fetchall()

if log_tables:
    print(f"\nFound log tables: {[t['name'] for t in log_tables]}")

conn.close()

# Check if the vision service process is responding
print("\n=== Process Status ===")
import subprocess
try:
    result = subprocess.run(['pgrep', '-f', 'vision_temperature_service.py'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        pid = result.stdout.strip()
        print(f"Vision service is running (PID: {pid})")
        
        # Check process age
        stat_result = subprocess.run(['ps', '-o', 'etime=', '-p', pid], 
                                   capture_output=True, text=True)
        if stat_result.returncode == 0:
            print(f"Process uptime: {stat_result.stdout.strip()}")
    else:
        print("Vision service is NOT running!")
except Exception as e:
    print(f"Error checking process: {e}")