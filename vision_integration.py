"""
Vision integration module for reading temperature with Claude
"""
import subprocess
import json
import os
from datetime import datetime

# Global storage for Claude readings
claude_readings_file = "experimental/claude_vision_log.json"
last_claude_reading = None
last_claude_time = None

def get_claude_temperature(image_path):
    """Get temperature reading from Claude CLI"""
    global last_claude_reading, last_claude_time
    
    try:
        # Import shared state
        from vision_state import load_state, save_state
        
        # Check if we have a recent reading (within 5 seconds)
        # This prevents calling Claude too frequently
        state = load_state()
        if state and state.get('timestamp'):
            timestamp = datetime.fromisoformat(state['timestamp'])
            age = (datetime.now() - timestamp).total_seconds()
            if age < 5:
                print(f"[CLAUDE CACHE] Using cached reading: {state['temperature']}°F (age: {age:.1f}s)")
                return state['temperature']
        
        # Ask Claude to read the temperature
        prompt = f"Look at {image_path} - what temperature number is shown on this thermostat display? Reply with just the number."
        claude_path = '/home/jason/.nvm/versions/node/v18.20.8/bin/claude'
        
        # Log the command being executed
        cmd = [claude_path, prompt]
        print(f"[CLAUDE CMD] Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print(f"[CLAUDE RESULT] Return code: {result.returncode}")
        print(f"[CLAUDE STDOUT] {result.stdout}")
        if result.stderr:
            print(f"[CLAUDE STDERR] {result.stderr}")
        
        if result.returncode == 0:
            response = result.stdout.strip()
            try:
                temp = int(response.replace('°F', '').replace('°', '').strip())
                if 50 <= temp <= 90:
                    last_claude_reading = temp
                    last_claude_time = datetime.now()
                    
                    # Save to shared state
                    from vision_state import save_state
                    save_state(temp, datetime.now())
                    
                    # Log the reading
                    log_claude_reading(temp)
                    
                    return temp
            except ValueError:
                pass
    except Exception as e:
        print(f"Error getting Claude temperature: {e}")
    
    # Return last known reading or default
    return last_claude_reading if last_claude_reading else 77

def log_claude_reading(temperature):
    """Log Claude reading to file and database"""
    try:
        # Load existing readings for file
        readings = []
        if os.path.exists(claude_readings_file):
            with open(claude_readings_file, 'r') as f:
                readings = json.load(f)
        
        # Add new reading
        readings.append({
            "timestamp": datetime.now().isoformat(),
            "temperature": temperature
        })
        
        # Keep last 100 readings in file
        readings = readings[-100:]
        
        # Save back to file
        os.makedirs(os.path.dirname(claude_readings_file), exist_ok=True)
        with open(claude_readings_file, 'w') as f:
            json.dump(readings, f)
        
        # Also save to database
        from vision_database import log_vision_reading
        log_vision_reading(temperature, get_vision_confidence())
        
    except Exception as e:
        print(f"Error logging reading: {e}")

def get_vision_confidence():
    """Get confidence based on how recent the reading is"""
    # Use shared state instead of module variables
    from vision_state import get_current_vision_data
    vision_data = get_current_vision_data()
    return vision_data['confidence']