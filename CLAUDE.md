# Smart Thermostat Project - Claude Instructions

## Project Overview
This is a smart thermostat control system that interfaces with a physical thermostat using servo motors and computer vision. The system includes:
- Web interface for remote control
- Temperature scheduling with timezone support
- Computer vision temperature detection
- Physical servo control via Raspberry Pi Zero

## Architecture

### Main Components
1. **Flask Web Server** (`main.py`) - Port 5000
   - Provides web UI and REST API
   - Manages thermostat state
   - Handles scheduling
   - Integrates vision system

2. **Scheduler** (`scheduler.py`)
   - SQLite-based schedule storage
   - Timezone-aware (US/Pacific)
   - Supports daily/weekday/weekend schedules
   - Automatic retry on failure

3. **Vision Service** (`vision_temperature_service.py`)
   - Reads temperature from thermostat display using AI
   - Updates SQLite database every 30 seconds
   - Provides confidence levels (HIGH/MEDIUM/LOW/STALE)

4. **Pi Zero Controller** (http://10.0.0.191:5000)
   - Controls physical servo motors
   - Actuates mode changes (OFF/HEAT/COOL)
   - Adjusts temperature settings

## Key Issues & Solutions

### 1. Timezone Issue (Fixed)
- **Problem**: Schedules executing 7 hours late
- **Cause**: Database storing UTC timestamps but scheduler using Pacific time
- **Solution**: Database timestamps are in UTC, application handles conversion properly

### 2. Vision State Sync (Fixed in v1.2.3)
- **Problem**: Vision display showing "STALE" despite active readings
- **Cause**: Vision service writes to SQLite, but web UI reads from JSON state file
- **Solution**: Added background thread `sync_vision_state_continuously()` that syncs DB to state file every 10 seconds

### 3. Scheduler Endpoint (Fixed in v1.2.1)
- **Problem**: "Unexpected token '<'" error when adding schedules
- **Cause**: Frontend sends new format with `days_of_week`, backend expected old format
- **Solution**: Updated `/set_schedule` endpoint to use new scheduler system

### 4. OFF Mode Temperature (Fixed in v1.2.4)
- **Problem**: OFF mode doesn't need temperature but UI required it
- **Solution**: Temperature field hidden when OFF selected, uses default 70°F internally

## Current Version
**v1.2.4** - Check `APP_VERSION` in `main.py` line 17

## Testing & Debugging

### Check Services
```bash
# Check if main app is running
ps aux | grep -E "python.*main.py" | grep -v grep

# Check vision service
ps aux | grep vision_temperature_service

# Check recent logs
tail -f smart_thermostat.log

# Check 6 AM schedule logs (enhanced logging added)
grep "6:00 AM\|6AM" smart_thermostat.log
```

### Database Queries
```bash
# Check schedules
python3 check_schedules.py

# Check vision readings
python3 check_vision_db.py

# Sync vision state manually
python3 sync_vision_state.py
```

## Important Files & Locations

### Configuration
- `thermostat_schedules.db` - Schedule database
- `vision_temperatures.db` - Vision readings database
- `experimental/vision_state.json` - Vision state for web UI
- `settings.json` - Thermostat settings

### Logs
- `smart_thermostat.log` - Main application log
- `reset.log` - Historical log data

### Static Files
- `static/script.js` - Frontend JavaScript
- `static/styles.css` - CSS styles
- `templates/index.html` - Main UI template

## API Endpoints

### Core Functions
- `GET /` - Main web interface
- `POST /set_mode` - Change mode (off/heat/cool)
- `POST /set_temperature` - Adjust temperature
- `POST /activate_light` - Activate thermostat screen

### Scheduling
- `POST /set_schedule` - Create new schedule
- `GET /get_scheduled_events` - List all schedules
- `DELETE /delete_schedule/<id>` - Remove schedule
- `PATCH /update_schedule/<id>` - Modify schedule

### Vision/Status
- `GET /vision_temperature_data` - Get vision readings
- `GET /ambient_temperature` - Current detected temperature
- `GET /version` - Check app version
- `GET /health` - Health check endpoint

## Known Issues

1. **6 AM Schedule Reliability** - Sometimes doesn't execute properly
   - Enhanced logging added in v1.2.2 to diagnose
   - Check logs for "===== 6:00 AM" markers

2. **Vision State File** - Can become empty unexpectedly
   - Sync thread should recreate it automatically
   - Manual fix: `python3 sync_vision_state.py`

## Deployment Notes

### Restart Application
The application needs to be restarted after code changes. Current process runs as user `jason`.

### Network Configuration
- Main app: `blade:5000`
- Pi Zero: `10.0.0.191:5000`
- CORS enabled for cross-origin requests

### Security Considerations
- No authentication currently implemented
- Runs on local network only
- No HTTPS configured

## Future Improvements

1. Add authentication for web interface
2. Implement HTTPS
3. Add more robust error recovery
4. Create systemd service files
5. Add temperature history graphs
6. Implement predictive heating/cooling

## Maintenance Commands

### Check System Status
```bash
# View all scheduled events
curl http://blade:5000/get_scheduled_events

# Check current mode
curl http://blade:5000/current_mode

# Health check
curl http://blade:5000/health
```

### Manual Controls
```bash
# Set to OFF mode
curl -X POST -H "Content-Type: application/json" \
  -d '{"mode":"off"}' http://blade:5000/set_mode

# Set temperature
curl -X POST -H "Content-Type: application/json" \
  -d '{"temperature":72}' http://blade:5000/set_temperature
```

## Troubleshooting

### Schedule Not Executing
1. Check timezone settings in `scheduler.py`
2. Look for retry attempts in logs
3. Verify scheduler thread is running
4. Check database for `last_error` field

### Vision Shows Stale
1. Check vision service is running
2. Verify sync thread is active
3. Check `experimental/vision_state.json` exists
4. Look for errors in vision database access

### Web UI Not Loading
1. Check Flask app is running
2. Verify port 5000 is not blocked
3. Check for JavaScript errors in browser console
4. Ensure all static files are accessible

## Development Guidelines

### Adding New Features
1. Update `APP_VERSION` when making changes
2. Add comprehensive logging for debugging
3. Handle timezone conversions carefully
4. Test with both simulated and real hardware
5. Update this documentation

### Code Style
- Use descriptive variable names
- Add logging for important operations
- Handle exceptions gracefully
- Return JSON for all API endpoints
- Keep functions focused and small

---
Last Updated: July 2025 (v1.2.4)