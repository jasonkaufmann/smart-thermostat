#!/usr/bin/env python3
# This shows the fix needed for the /set_schedule endpoint

# The current endpoint expects:
# {
#   "time": "14:30",
#   "temperature": 72,
#   "mode": "cool",
#   "enabled": true
# }

# But the frontend is sending:
# {
#   "time": "14:30", 
#   "temperature": 72,
#   "mode": "cool",
#   "days_of_week": "daily",
#   "enabled": true
# }

# The fix is to update the /set_schedule endpoint to use the new scheduler system:

def set_schedule_fixed():
    """Fixed version that uses the new scheduler system"""
    data = request.get_json()
    
    if not data:
        logging.error("Invalid data received")
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    
    # Extract data from the request
    time_str = data.get('time')
    temperature = data.get('temperature')
    mode = data.get('mode')  # Don't call .lower() on None
    days_of_week = data.get('days_of_week', 'daily')  # Default to daily
    enabled = data.get('enabled', True)
    
    # Validate data
    if not all([time_str, temperature is not None, mode]):
        logging.error("Missing required fields in the request")
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    try:
        # Use the new scheduler system
        schedule_id = scheduler.create_schedule(
            time_str=time_str,
            temperature=int(temperature),
            mode=mode.lower(),
            days_of_week=days_of_week,
            enabled=enabled
        )
        
        logging.info(f"Created schedule {schedule_id}: {time_str}, {temperature}°F, {mode}, {days_of_week}")
        return jsonify({
            "status": "success", 
            "message": "Schedule created successfully",
            "schedule_id": schedule_id
        }), 200
        
    except SchedulerError as e:
        logging.error(f"Scheduler error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Unexpected error creating schedule: {e}")
        return jsonify({"status": "error", "message": "Failed to create schedule"}), 500