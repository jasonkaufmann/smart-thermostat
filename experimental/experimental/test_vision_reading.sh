#!/bin/bash
# Test script to read temperature with Claude vision

echo "Capturing thermostat display..."
python3 vision_temperature_reader.py

echo -e "\nTo analyze with Claude, run:"
echo "claude 'Look at experimental/vision_captures/latest.jpg - what temperature is shown on this thermostat display?'"
