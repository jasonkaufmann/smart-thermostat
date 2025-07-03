#!/bin/bash
# Quick one-liner to get current temperature

# Capture and ask Claude in one go
python3 /home/jason/smart-thermostat/experimental/check_current_temp.py > /dev/null 2>&1 && \
claude "Look at $(ls -t /home/jason/smart-thermostat/experimental/current_display_*.jpg | head -1) - what temperature is shown? Just the number."