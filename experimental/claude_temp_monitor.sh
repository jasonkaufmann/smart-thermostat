#!/bin/bash
# Continuous temperature monitoring with Claude Code

LOG_FILE="/home/jason/smart-thermostat/experimental/claude_temp_readings.log"
INTERVAL=30  # seconds

echo "Claude Code Temperature Monitor"
echo "=============================="
echo "Reading temperature every $INTERVAL seconds"
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Capture the display
    echo -n "[$TIMESTAMP] Capturing display... "
    python3 /home/jason/smart-thermostat/experimental/check_current_temp.py > /dev/null 2>&1
    
    # Get latest image
    LATEST_IMAGE=$(ls -t /home/jason/smart-thermostat/experimental/current_display_*.jpg 2>/dev/null | head -1)
    
    if [ -n "$LATEST_IMAGE" ]; then
        echo "done"
        
        # Ask Claude to read it
        echo -n "[$TIMESTAMP] Claude reading: "
        TEMP=$(claude "Look at $LATEST_IMAGE - what temperature number is shown on this thermostat display? Reply with just the number." 2>/dev/null)
        
        if [ -n "$TEMP" ]; then
            echo "${TEMP}°F"
            echo "[$TIMESTAMP] ${TEMP}°F" >> "$LOG_FILE"
        else
            echo "Failed to read"
            echo "[$TIMESTAMP] Failed to read" >> "$LOG_FILE"
        fi
    else
        echo "Failed to capture"
        echo "[$TIMESTAMP] Failed to capture" >> "$LOG_FILE"
    fi
    
    # Clean up old images (keep only last 10)
    ls -t /home/jason/smart-thermostat/experimental/current_display_*.jpg 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null
    
    # Wait for next reading
    sleep $INTERVAL
done