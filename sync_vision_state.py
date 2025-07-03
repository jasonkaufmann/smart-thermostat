#!/usr/bin/env python3
"""
Sync vision database readings to the state file used by the web interface
"""
import sqlite3
import json
import os
from datetime import datetime
import time

STATE_FILE = "experimental/vision_state.json"
DB_FILE = "vision_temperatures.db"

def sync_vision_state():
    """Read latest from database and update state file"""
    try:
        # Connect to database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get latest reading
        cursor.execute('''
            SELECT * FROM vision_readings 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        
        latest = cursor.fetchone()
        conn.close()
        
        if latest:
            # Parse timestamp - database uses format like '2025-07-03 01:15:48'
            timestamp_str = latest['timestamp']
            # Convert to ISO format for consistency
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            # Save to state file
            state = {
                "temperature": latest['temperature'],
                "timestamp": timestamp.isoformat(),
                "confidence": latest['confidence']
            }
            
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f)
            
            print(f"Updated state: {state}")
            return True
        else:
            print("No readings found in database")
            return False
            
    except Exception as e:
        print(f"Error syncing vision state: {e}")
        return False

if __name__ == "__main__":
    # Run once
    if sync_vision_state():
        print("Vision state synced successfully")
    else:
        print("Failed to sync vision state")