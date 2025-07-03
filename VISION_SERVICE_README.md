# Vision Temperature Service

This is a centralized service that continuously reads the thermostat temperature using Claude AI vision capabilities and writes it to a file that multiple frontends can read.

## Architecture

1. **vision_temperature_service.py** - Main service that runs continuously
   - Captures images from the thermostat camera every 30 seconds
   - Uses Claude to read the temperature from the image
   - Writes the result to `/var/tmp/thermostat_temperature.json`

2. **read_vision_temperature.py** - Simple Python module for reading the temperature
   - Provides easy functions to read the temperature from the shared file
   - No need for each frontend to call Claude directly

3. **vision-temperature.service** - Systemd service file for automatic startup

## Installation

```bash
# Install and start the service
sudo ./install_vision_service.sh

# Check if it's running
sudo systemctl status vision-temperature.service

# View logs
sudo journalctl -u vision-temperature.service -f
```

## Usage

### From Python

```python
from read_vision_temperature import get_temperature_only

# Get the temperature
temp = get_temperature_only()
if temp is not None:
    print(f"Current temperature: {temp}°F")
```

### From Command Line

```bash
# Read the JSON file directly
cat /var/tmp/thermostat_temperature.json

# Use Python one-liner
python3 -c "from read_vision_temperature import get_temperature_only; print(get_temperature_only())"
```

### From Other Languages

Simply read and parse the JSON file at `/var/tmp/thermostat_temperature.json`:

```json
{
  "temperature": 72,
  "timestamp": "2024-01-15T10:30:45.123456",
  "confidence": "HIGH",
  "age_seconds": 15.5
}
```

## Benefits

1. **Single Claude Process**: Only one process calls Claude, reducing API usage
2. **Always Available**: Temperature is always available from the file, even if Claude is slow
3. **Multiple Readers**: Any number of frontends can read the temperature simultaneously
4. **Simple Interface**: Just read a JSON file - works with any programming language
5. **Confidence Tracking**: Know how fresh the temperature reading is

## Configuration

Edit `vision_temperature_service.py` to change:
- `UPDATE_INTERVAL`: How often to update (default: 30 seconds)
- `OUTPUT_FILE`: Where to write the temperature (default: `/var/tmp/thermostat_temperature.json`)

## Troubleshooting

1. **No temperature data**: Check if the service is running
2. **Old data**: Check the `age_seconds` field and service logs
3. **Permission errors**: Make sure the service can write to `/var/tmp/`

## Example

See `example_temperature_reader.py` for a complete example of using the service.