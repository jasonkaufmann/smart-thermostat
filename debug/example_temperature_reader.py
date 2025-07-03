#!/usr/bin/env python3
"""
Example of how to use the centralized vision temperature service
from any Python application
"""

from read_vision_temperature import (
    get_vision_temperature, 
    get_temperature_only,
    is_temperature_fresh,
    format_temperature_display
)

def main():
    print("Vision Temperature Reader Example")
    print("=" * 40)
    
    # Method 1: Get just the temperature value
    temp = get_temperature_only()
    if temp is not None:
        print(f"Current temperature: {temp}°F")
    else:
        print("No temperature data available")
    
    # Method 2: Get full data with metadata
    data = get_vision_temperature()
    print("\nFull temperature data:")
    print(f"  Temperature: {data.get('temperature')}°F")
    print(f"  Confidence: {data.get('confidence')}")
    print(f"  Last Update: {data.get('timestamp')}")
    print(f"  Age: {data.get('age_seconds', 0):.1f} seconds")
    
    # Method 3: Check if data is fresh
    if is_temperature_fresh(max_age_seconds=60):
        print("\nTemperature data is fresh (less than 60 seconds old)")
    else:
        print("\nWarning: Temperature data may be stale")
    
    # Method 4: Get formatted display string
    print(f"\nFormatted display: {format_temperature_display()}")
    
    # Example of using in a loop (e.g., for a GUI)
    print("\nExample usage in application:")
    print("while True:")
    print("    temp = get_temperature_only()")
    print("    if temp is not None:")
    print("        update_display(temp)")
    print("    time.sleep(1)  # Update every second")

if __name__ == "__main__":
    main()