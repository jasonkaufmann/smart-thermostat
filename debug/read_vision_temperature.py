#!/usr/bin/env python3
"""
Simple module to read the AI vision temperature from the centralized service file.
This can be used by any frontend to get the current temperature reading.
"""

import json
import os
from datetime import datetime

# Location of the temperature file written by the service
TEMPERATURE_FILE = "/var/tmp/thermostat_temperature.json"

def get_vision_temperature():
    """
    Read the current vision-detected temperature from the service file.
    
    Returns a dictionary with:
    - temperature: The temperature value (int) or None if not available
    - timestamp: ISO format timestamp of the reading
    - confidence: HIGH, MEDIUM, LOW, or SERVICE_STOPPED
    - age_seconds: How old the reading is in seconds
    - error: Error message if something went wrong
    """
    try:
        # Check if the file exists
        if not os.path.exists(TEMPERATURE_FILE):
            return {
                "temperature": None,
                "timestamp": None,
                "confidence": "NO_DATA",
                "age_seconds": None,
                "error": "Temperature file not found. Is the service running?"
            }
        
        # Read the file
        with open(TEMPERATURE_FILE, 'r') as f:
            data = json.load(f)
            
        # Calculate current age if we have a timestamp
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'])
            age_seconds = (datetime.now() - timestamp).total_seconds()
            data['age_seconds'] = age_seconds
            
            # Recalculate confidence based on current age
            if data.get('confidence') != 'SERVICE_STOPPED':
                if age_seconds < 60:
                    data['confidence'] = 'HIGH'
                elif age_seconds < 300:
                    data['confidence'] = 'MEDIUM'
                else:
                    data['confidence'] = 'LOW'
        
        return data
        
    except json.JSONDecodeError:
        return {
            "temperature": None,
            "timestamp": None,
            "confidence": "ERROR",
            "age_seconds": None,
            "error": "Invalid JSON in temperature file"
        }
    except Exception as e:
        return {
            "temperature": None,
            "timestamp": None,
            "confidence": "ERROR", 
            "age_seconds": None,
            "error": f"Error reading temperature: {str(e)}"
        }

def get_temperature_only():
    """
    Simple function that returns just the temperature value.
    Returns None if no valid temperature is available.
    """
    data = get_vision_temperature()
    return data.get('temperature')

def is_temperature_fresh(max_age_seconds=300):
    """
    Check if the temperature reading is fresh enough.
    
    Args:
        max_age_seconds: Maximum age in seconds to consider fresh (default 5 minutes)
        
    Returns:
        True if the reading is fresh, False otherwise
    """
    data = get_vision_temperature()
    age = data.get('age_seconds')
    return age is not None and age <= max_age_seconds

def format_temperature_display():
    """
    Get a formatted string for displaying the temperature.
    Includes confidence indicator.
    """
    data = get_vision_temperature()
    temp = data.get('temperature')
    confidence = data.get('confidence', 'UNKNOWN')
    
    if temp is None:
        return "No temperature data"
    
    # Add confidence indicator
    if confidence == 'HIGH':
        indicator = '●'  # Solid circle for high confidence
    elif confidence == 'MEDIUM':
        indicator = '◐'  # Half circle for medium
    elif confidence == 'LOW':
        indicator = '○'  # Empty circle for low
    else:
        indicator = '?'  # Question mark for errors/unknown
        
    return f"{temp}°F {indicator}"


# Example usage
if __name__ == "__main__":
    # Get full data
    print("Full temperature data:")
    data = get_vision_temperature()
    for key, value in data.items():
        print(f"  {key}: {value}")
    
    print(f"\nSimple temperature: {get_temperature_only()}°F")
    print(f"Is fresh: {is_temperature_fresh()}")
    print(f"Display format: {format_temperature_display()}")