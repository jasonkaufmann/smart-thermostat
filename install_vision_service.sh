#!/bin/bash
# Installation script for the vision temperature service

echo "Installing Vision Temperature Service..."

# Create log directory if it doesn't exist
sudo mkdir -p /var/log
sudo touch /var/log/vision_temperature_service.log
sudo chown jason:jason /var/log/vision_temperature_service.log

# Create the temperature file location
sudo mkdir -p /var/tmp
sudo touch /var/tmp/thermostat_temperature.json
sudo chown jason:jason /var/tmp/thermostat_temperature.json

# Copy the service file to systemd
sudo cp vision-temperature.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable vision-temperature.service

# Start the service
sudo systemctl start vision-temperature.service

# Show status
echo ""
echo "Service installation complete!"
echo ""
echo "To check service status: sudo systemctl status vision-temperature.service"
echo "To view logs: sudo journalctl -u vision-temperature.service -f"
echo "To stop service: sudo systemctl stop vision-temperature.service"
echo "To restart service: sudo systemctl restart vision-temperature.service"
echo ""
echo "Temperature file location: /var/tmp/thermostat_temperature.json"