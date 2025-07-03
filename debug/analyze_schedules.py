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

print("=== All Schedules ===\n")
print(f"{'Time':<6} {'Temp':<5} {'Mode':<6} {'Enabled':<8} {'Last Executed':<20} {'Next Execution':<20}")
print("-" * 85)

for schedule in schedules:
    enabled = 'Yes' if schedule['enabled'] else 'No'
    last_exec = schedule['last_executed'] or 'Never'
    next_exec = schedule['next_execution'] or 'Not set'
    print(f"{schedule['time']:<6} {schedule['temperature']:<5} {schedule['mode']:<6} {enabled:<8} {last_exec:<20} {next_exec:<20}")

print("\n=== Execution Time Analysis ===\n")

# Analyze execution times vs scheduled times
cursor.execute('''
    SELECT s.time as scheduled_time, eh.executed_at, s.mode, s.temperature
    FROM execution_history eh
    JOIN schedules s ON eh.schedule_id = s.id
    WHERE eh.success = 1
    ORDER BY eh.executed_at DESC
    LIMIT 20
''')

executions = cursor.fetchall()

print(f"{'Scheduled':<10} {'Executed At':<20} {'Execution Time':<10} {'Difference':<15} {'Mode':<6}")
print("-" * 75)

pst = pytz.timezone('US/Pacific')

for exec in executions:
    scheduled_time = exec['scheduled_time']
    executed_at = exec['executed_at']
    
    # Parse the execution timestamp
    try:
        exec_dt = datetime.datetime.strptime(executed_at, '%Y-%m-%d %H:%M:%S')
        exec_time = exec_dt.strftime('%H:%M')
        
        # Calculate the difference
        sched_hour, sched_min = map(int, scheduled_time.split(':'))
        exec_hour, exec_min = exec_dt.hour, exec_dt.minute
        
        # Calculate time difference in minutes
        sched_minutes = sched_hour * 60 + sched_min
        exec_minutes = exec_hour * 60 + exec_min
        
        diff_minutes = exec_minutes - sched_minutes
        
        # Handle day boundary
        if diff_minutes < -720:  # More than 12 hours negative
            diff_minutes += 1440  # Add 24 hours
        elif diff_minutes > 720:  # More than 12 hours positive
            diff_minutes -= 1440  # Subtract 24 hours
        
        diff_hours = diff_minutes // 60
        diff_mins = abs(diff_minutes) % 60
        
        if diff_minutes != 0:
            diff_str = f"{diff_hours:+d}h {diff_mins}m"
        else:
            diff_str = "On time"
        
        print(f"{scheduled_time:<10} {executed_at:<20} {exec_time:<10} {diff_str:<15} {exec['mode']:<6}")
    except Exception as e:
        print(f"Error parsing {executed_at}: {e}")

print("\n=== Pattern Analysis ===\n")

# Check if there's a consistent offset
cursor.execute('''
    SELECT s.time as scheduled_time, 
           TIME(eh.executed_at) as exec_time,
           s.id
    FROM execution_history eh
    JOIN schedules s ON eh.schedule_id = s.id
    WHERE eh.success = 1
    ORDER BY eh.executed_at DESC
    LIMIT 50
''')

time_diffs = []
for row in cursor.fetchall():
    sched_hour, sched_min = map(int, row['scheduled_time'].split(':'))
    exec_hour, exec_min = map(int, row['exec_time'].split(':'))
    
    sched_minutes = sched_hour * 60 + sched_min
    exec_minutes = exec_hour * 60 + exec_min
    
    diff = exec_minutes - sched_minutes
    if diff < -720:
        diff += 1440
    elif diff > 720:
        diff -= 1440
    
    time_diffs.append(diff)

if time_diffs:
    avg_diff = sum(time_diffs) / len(time_diffs)
    print(f"Average time difference: {avg_diff/60:.1f} hours ({avg_diff:.0f} minutes)")
    
    # Check for consistent offset
    consistent_7h = all(410 <= d <= 430 for d in time_diffs)  # 7 hours ± 10 minutes
    if consistent_7h:
        print("⚠️  All executions are approximately 7 hours late!")
        print("This suggests a UTC vs PST timezone issue (UTC is 7-8 hours ahead of PST)")

print("\n=== Current Time Information ===")
print(f"System time: {datetime.datetime.now()}")
print(f"UTC time: {datetime.datetime.utcnow()}")

# Check if we're in DST
pst_now = datetime.datetime.now(pst)
is_dst = bool(pst_now.dst())
print(f"PST/PDT time: {pst_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Currently in {'PDT (UTC-7)' if is_dst else 'PST (UTC-8)'}")

conn.close()