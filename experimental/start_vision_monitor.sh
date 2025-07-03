#!/bin/bash
# Start the vision temperature monitor

echo "Starting Vision Temperature Monitor..."
echo "=================================="
echo ""
echo "This will:"
echo "1. Capture thermostat display every 5 seconds"
echo "2. Detect temperature using vision (simulated)"
echo "3. Display annotated image with detected temp"
echo "4. Plot temperature history over time"
echo ""
echo "Access the web interface at:"
echo "http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================="
echo ""

# Make sure we're in the right directory
cd /home/jason/smart-thermostat/experimental

# Start the monitor
python3 vision_monitor_enhanced.py