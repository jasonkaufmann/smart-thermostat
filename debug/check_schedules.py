#!/usr/bin/env python3
import sqlite3
import datetime

# Connect to the database
conn = sqlite3.connect('thermostat_schedules.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Most Recent Scheduled Events ===\n")

# Get all schedules ordered by next_execution
cursor.execute('''
    SELECT * FROM schedules 
    ORDER BY next_execution DESC 
    LIMIT 10
''')

schedules = cursor.fetchall()

if schedules:
    for schedule in schedules:
        print(f"ID: {schedule['id']}")
        print(f"Time: {schedule['time']}")
        print(f"Temperature: {schedule['temperature']}°F")
        print(f"Mode: {schedule['mode']}")
        print(f"Enabled: {'Yes' if schedule['enabled'] else 'No'}")
        print(f"Days: {schedule['days_of_week']}")
        print(f"Next Execution: {schedule['next_execution']}")
        print(f"Last Executed: {schedule['last_executed']}")
        print(f"Created: {schedule['created_at']}")
        print("-" * 50)
else:
    print("No schedules found in the database.")

print("\n=== Recent Execution History ===\n")

# Get recent execution history
cursor.execute('''
    SELECT eh.*, s.time, s.temperature as scheduled_temp, s.mode as scheduled_mode
    FROM execution_history eh
    JOIN schedules s ON eh.schedule_id = s.id
    ORDER BY eh.executed_at DESC
    LIMIT 10
''')

history = cursor.fetchall()

if history:
    for entry in history:
        print(f"Schedule Time: {entry['time']}")
        print(f"Executed At: {entry['executed_at']}")
        print(f"Success: {'Yes' if entry['success'] else 'No'}")
        print(f"Temperature: {entry['temperature']}°F (scheduled: {entry['scheduled_temp']}°F)")
        print(f"Mode: {entry['mode']} (scheduled: {entry['scheduled_mode']})")
        if entry['error_message']:
            print(f"Error: {entry['error_message']}")
        print("-" * 50)
else:
    print("No execution history found.")

conn.close()