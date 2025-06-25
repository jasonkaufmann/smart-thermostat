#!/usr/bin/env python3
"""
Migration script to convert existing JSON schedules to SQLite database
"""

import json
import os
import sys
from scheduler import ThermostatScheduler, init_database

def migrate_schedules():
    """Migrate schedules from JSON file to SQLite database"""
    json_file = 'scheduled_events.json'
    
    # Initialize the database
    print("Initializing database...")
    init_database()
    
    # Check if JSON file exists
    if not os.path.exists(json_file):
        print(f"No {json_file} found. Nothing to migrate.")
        return
    
    # Load existing schedules
    try:
        with open(json_file, 'r') as f:
            schedules = json.load(f)
        print(f"Found {len(schedules)} schedules to migrate")
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return
    
    # Create dummy callbacks for scheduler
    dummy_temp_callback = lambda temp: True
    dummy_mode_callback = lambda mode: True
    
    # Initialize scheduler
    scheduler = ThermostatScheduler(dummy_temp_callback, dummy_mode_callback)
    
    # Migrate each schedule
    migrated = 0
    failed = 0
    
    for schedule in schedules:
        try:
            # Extract schedule data
            time_str = schedule.get('time', '')
            temperature = schedule.get('temperature', 70)
            mode = schedule.get('mode', 'off').lower()
            enabled = schedule.get('enabled', True)
            
            # Create new schedule in database
            schedule_id = scheduler.create_schedule(
                time_str=time_str,
                temperature=temperature,
                mode=mode,
                days_of_week='daily',  # Default to daily since old format didn't have this
                enabled=enabled
            )
            
            print(f"✓ Migrated schedule: {time_str} - {temperature}°F {mode.upper()}")
            migrated += 1
            
        except Exception as e:
            print(f"✗ Failed to migrate schedule: {e}")
            failed += 1
    
    print(f"\nMigration complete!")
    print(f"Successfully migrated: {migrated}")
    print(f"Failed: {failed}")
    
    if migrated > 0:
        # Backup the old JSON file
        backup_file = json_file + '.backup'
        os.rename(json_file, backup_file)
        print(f"\nOld schedule file backed up to: {backup_file}")
        print("You can safely delete this file once you've verified the migration.")

if __name__ == "__main__":
    print("Smart Thermostat Schedule Migration Tool")
    print("=" * 40)
    
    response = input("This will migrate your schedules from JSON to SQLite. Continue? (y/n): ")
    if response.lower() == 'y':
        migrate_schedules()
    else:
        print("Migration cancelled.")