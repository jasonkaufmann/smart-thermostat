"""
Shared state for vision detection
This ensures all parts of the system see the same state
"""
import os
import json
from datetime import datetime

# State file to persist between requests
STATE_FILE = "experimental/vision_state.json"

def save_state(temperature, timestamp):
    """Save the latest vision reading state"""
    state = {
        "temperature": temperature,
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
        "confidence": calculate_confidence(timestamp)
    }
    
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
    
    return state

def load_state():
    """Load the latest vision reading state"""
    if not os.path.exists(STATE_FILE):
        return None
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        # Recalculate confidence based on current time
        if state.get('timestamp'):
            timestamp = datetime.fromisoformat(state['timestamp'])
            state['confidence'] = calculate_confidence(timestamp)
        
        return state
    except:
        return None

def calculate_confidence(timestamp):
    """Calculate confidence based on timestamp age"""
    if not timestamp:
        return "NO_DATA"
    
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    
    age_seconds = (datetime.now() - timestamp).total_seconds()
    
    if age_seconds < 30:
        return "HIGH"
    elif age_seconds < 60:
        return "MEDIUM"
    elif age_seconds < 300:  # 5 minutes
        return "LOW"
    else:
        return "STALE"

def get_current_vision_data():
    """Get current vision data with proper confidence"""
    state = load_state()
    
    if not state:
        return {
            "temperature": None,
            "confidence": "NO_DATA",
            "timestamp": None
        }
    
    return state