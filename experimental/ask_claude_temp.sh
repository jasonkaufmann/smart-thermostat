#!/bin/bash
# Script to ask Claude Code to read the thermostat temperature

# Capture the current display
echo "Capturing thermostat display..."
python3 /home/jason/smart-thermostat/experimental/check_current_temp.py

# Get the latest captured image
LATEST_IMAGE=$(ls -t /home/jason/smart-thermostat/experimental/current_display_*.jpg | head -1)

if [ -z "$LATEST_IMAGE" ]; then
    echo "Error: No image captured"
    exit 1
fi

echo "Image captured: $LATEST_IMAGE"

# Ask Claude to read the temperature
echo "Asking Claude Code to read the temperature..."
claude "Look at the thermostat display image at $LATEST_IMAGE and tell me only the temperature number shown. Just respond with the number, nothing else."