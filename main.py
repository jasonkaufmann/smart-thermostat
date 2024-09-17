from flask import Flask, Response, render_template, request, jsonify
# from picamera2 import Picamera2
import cv2
import time
import threading
import argparse
import logging
from flask_cors import CORS
import datetime
import json
import requests
import os 

# Set up logging
# Set up logging to a file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='smart_thermostat.log',  # Log to this file
    filemode='a'  # Append to the file (use 'w' to overwrite)
)

# Global variables
latest_image_path = None
# Directory to save images
IMAGE_SAVE_PATH = 'static/images'
os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)


logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Create the I2C bus interface
# logging.debug("Initializing I2C bus interface")
# i2c = busio.I2C(board.SCL, board.SDA)

# Create a PCA9685 instance
# logging.debug("Creating PCA9685 instance")
# pca = PCA9685(i2c)

# Set the PWM frequency to 50Hz, suitable for servos
# logging.debug("Setting PCA9685 frequency to 50Hz")
# pca.frequency = 50

PI_ZERO_HOST = "http://10.0.0.54:5000"

# Create servo objects for channels
# logging.debug("Creating servo objects for channels")
servo_down = "down"  # Servo for down temperature
servo_mode = "mode"  # Servo for mode selection
servo_up = "up"    # Servo for up temperature

# Define the file path to store scheduled events
SCHEDULE_FILE_PATH = 'scheduled_events.json'
# Constants for modes
MODE_OFF = 0
MODE_HEAT = 1
MODE_COOL = 2

scheduled_events = []
# Global dictionary to keep track of active timers
active_timers = {}

# Global variables for managing state
current_heat_temp = 75
current_cool_temp = 75
ambient_temp = 75  # Default ambient temperature
current_mode = MODE_OFF
last_action_time = time.time() - 100  # Start with time since last press > 45 seconds
screen_active = False  # Track whether the screen is active
lock = threading.Lock()
current_desired_temp = None

# Global variable to store the latest frame
latest_frame = None

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Smart Thermostat Control")
parser.add_argument('--simulate', action='store_true', help='Run in simulation mode (no servo actuation)')
args = parser.parse_args()

app = Flask(__name__)
# Updated CORS configuration to allow specific origins
CORS(app, resources={r"/*": {"origins": "*"}})


def actuate_servo(servo_name, start_angle, target_angle):
    """Send a request to the Pi Zero to actuate a servo."""
    global last_action_time
    logging.info("Sending request to Pi Zero to actuate servo %s from %d to %d", servo_name, start_angle, target_angle)
    
    if args.simulate:
        logging.debug(f"Simulating servo movement: {servo_name} from {start_angle} to {target_angle}")
        return True
    else:
        try:
            response = requests.post(
                f"{PI_ZERO_HOST}/actuate_servo",
                json={"servo": servo_name, "start_angle": start_angle, "target_angle": target_angle},
                timeout=5  # Adjust timeout as necessary
            )
            response.raise_for_status()
            last_action_time = time.time()  # Update the last action time
            logging.info("Servo %s actuated successfully", servo_name)
            return True
        except requests.RequestException as e:
            logging.error("Error actuating servo: %s", e)
            return False

def cycle_mode_to_desired(desired_mode):
    """Cycle through the modes until the desired mode is reached."""
    logging.info("Cycling mode to desired mode: %s", ['OFF', 'HEAT', 'COOL'][desired_mode])
    global current_mode
    while current_mode != desired_mode:
        result = actuate_servo(servo_mode, 0, 180)
        if not result:
            logging.error("Failed to actuate servo_mode to cycle mode")
            return False
        if current_mode == MODE_OFF:
            current_mode = MODE_HEAT
        elif current_mode == MODE_HEAT:
            current_mode = MODE_COOL
        elif current_mode == MODE_COOL:
            current_mode = MODE_OFF  # Add manual mode in the cycle
        else:
            current_mode = MODE_OFF
        logging.debug("Mode changed to: %s", ['OFF', 'HEAT', 'COOL'][current_mode])
    return True

def set_temperature_logic(target_temp):
    """Core logic for setting the temperature."""
    logging.info("Function set_temperature_logic called with target_temp: %d", target_temp)
    global current_heat_temp, current_cool_temp, ambient_temp, last_action_time, screen_active, current_mode

    # Attempt to acquire lock with a timeout
    acquired = lock.acquire(timeout=5)
    if not acquired:
        logging.error("Failed to acquire lock in set_temperature_logic")
        return {"status": "error", "message": "Could not acquire lock"}

    try:
        logging.debug("Entered lock block in set_temperature_logic")
        logging.debug("Current mode: %s", ['OFF', 'HEAT', 'COOL'][current_mode])
        logging.debug("Ambient temperature: %d°F", ambient_temp)

        if current_mode == MODE_HEAT:
            temp_difference = target_temp - current_heat_temp
            logging.debug("Calculated temperature difference for HEAT mode: %d", temp_difference)
        elif current_mode == MODE_COOL:
            temp_difference = target_temp - current_cool_temp
            logging.debug("Calculated temperature difference for COOL mode: %d", temp_difference)
        else:
            logging.info("No adjustment needed in OFF mode")
            return {"status": "success", "message": "No change needed"}

        success = True  # Initialize success flag

        # Adjust temperature
        if temp_difference > 0:  # Increase temperature
            if time.time() - last_action_time > 45:
                logging.info("More than 45 seconds since last action, activating screen")
                activate_screen()
            logging.info("Increasing temperature by %d degrees", temp_difference)
            for _ in range(temp_difference):
                logging.debug("Actuating servo to increase temperature")
                actuation_result = actuate_servo(servo_up, 180, 0)
                if not actuation_result:
                    logging.error("Failed to actuate servo_up to increase temperature")
                    success = False
                    break
            if success:
                logging.debug("Updated last_action_time after increasing temperature")
        elif temp_difference < 0:  # Decrease temperature
            if time.time() - last_action_time > 45:
                logging.info("More than 45 seconds since last action, activating screen")
                activate_screen()
            logging.info("Decreasing temperature by %d degrees", abs(temp_difference))
            for _ in range(abs(temp_difference)):
                logging.debug("Actuating servo to decrease temperature")
                actuation_result = actuate_servo(servo_down, 0, 180)
                if not actuation_result:
                    logging.error("Failed to actuate servo_down to decrease temperature")
                    success = False
                    break
            if success:
                logging.debug("Updated last_action_time after decreasing temperature")
        else:
            logging.info("No temperature change needed")
            return {"status": "success", "message": "Temperature already at desired value"}

        if success:
            # Only update the variables if all actuations succeeded
            if current_mode == MODE_HEAT:
                current_heat_temp = target_temp
                logging.info("Adjusted heat temperature to %d°F", current_heat_temp)
            elif current_mode == MODE_COOL:
                current_cool_temp = target_temp
                logging.info("Adjusted cool temperature to %d°F", current_cool_temp)
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Failed to actuate servo"}
    finally:
        lock.release()
        logging.debug("Lock released in set_temperature_logic")

def set_temperature(target_temp):
    global current_desired_temp
    """Wrapper to use within Flask context."""
    result = set_temperature_logic(target_temp)
    if result["status"] == "error":
        return jsonify(result), 503
    current_desired_temp = target_temp
    return jsonify(result)

import threading
import datetime
import logging

# Global dictionary to keep track of active timers
active_timers = {}

def schedule_action(action_id, action_time, temperature, mode):
    global active_timers, scheduled_events
    """Schedule a thermostat change at a specific time every day."""

    def task(action_id):
        global current_desired_temp
        logging.info(f"Executing scheduled task for ID {action_id}")

        # Retrieve the latest scheduled event details for the given action_id
        event = next((event for event in scheduled_events if event['id'] == action_id), None)
        
        if event:
            # Use the most recent temperature and mode from the scheduled events
            temperature = event['temperature']
            mode = event['mode']
            
            logging.info(f"Using updated parameters for task ID {action_id}: Temperature={temperature}, Mode={mode}")

            mode_result = set_mode_logic(mode)
            if not mode_result:
                logging.error(f"Failed to set mode to {mode} for scheduled task ID {action_id}")
                return

            temp_result = set_temperature_logic(temperature)
            if temp_result.get("status") != "success":
                logging.error(f"Failed to set temperature to {temperature} for scheduled task ID {action_id}")
                return

            current_desired_temp = temperature
            save_settings()
            
            # Reschedule the task for the same time the next day
            reschedule_action(action_id, action_time, temperature, mode)
        else:
            logging.info(f"Scheduled event ID {action_id} has been deleted. No action will be taken.")
            # Clean up any remaining references to the deleted action
            if action_id in active_timers:
                del active_timers[action_id]  # Remove from active timers

    # Calculate the delay in seconds until the next occurrence of the action time
    now = datetime.datetime.now()
    next_action_time = datetime.datetime.combine(now.date(), action_time.time())
    
    if now >= next_action_time:
        # If the time is already passed today, schedule it for tomorrow
        next_action_time += datetime.timedelta(days=1)
    
    delay = (next_action_time - now).total_seconds()
    
    if delay > 0:
        # Schedule the task and pass action_id as an argument
        timer = threading.Timer(delay, task, args=(action_id,))
        timer.start()
        # Store the timer in the dictionary using action_id as the key
        active_timers[action_id] = timer
        logging.info(f"Scheduled task set for {next_action_time} (ID: {action_id}), in {delay} seconds")
    else:
        logging.warning("Scheduled time is in the past, not scheduling task.")

def reschedule_action(action_id, action_time, temperature, mode):
    """Reschedule the thermostat change for the next day."""
    # Schedule the action for the same time on the next day
    next_action_time = action_time + datetime.timedelta(days=1)
    schedule_action(action_id, next_action_time, temperature, mode)

def cancel_scheduled_action(action_id):
    """Cancel a scheduled thermostat change."""
    timer = active_timers.pop(action_id, None)
    if timer:
        timer.cancel()
        logging.info(f"Cancelled scheduled task with ID {action_id}")
    else:
        logging.warning(f"No active task found with ID {action_id} to cancel")

def activate_screen():
    """Activate the screen and set mode to HEAT or COOL."""
    logging.info("Activating screen...")
    global screen_active, last_action_time
    result = actuate_servo(servo_mode, 0, 180)
    if result:
        logging.info("Screen activated")
    else:
        logging.error("Failed to activate screen")

def read_ambient_temperature():
    """Read the ambient temperature from a file."""
    global ambient_temp, current_desired_temp
    ambient_temp_new = None
    try:
        with open("temp.txt", "r") as file:
            ambient_temp_new = float(file.read().strip())
    except Exception as e:
        logging.error("Error reading ambient temperature: %s", e)

    if ambient_temp_new is not None:
        if ambient_temp_new != ambient_temp:
            ambient_temp = ambient_temp_new
            logging.info("Ambient temperature updated to: %.1f°F", ambient_temp_new)

def save_settings():
    """Save current settings to a file."""
    logging.info("Saving settings to file")
    global current_heat_temp, current_cool_temp, current_mode, current_desired_temp
    try:
        with open("settings.txt", "w") as file:
            file.write(f"{current_heat_temp}\n")
            file.write(f"{current_cool_temp}\n")
            file.write(f"{current_desired_temp}\n")
            file.write(f"{current_mode}\n")
        logging.info("Settings saved.")
    except Exception as e:
        logging.error("Error saving settings: %s", e)

def load_settings():
    """Load settings from a file."""
    logging.info("Loading settings from file")
    global current_heat_temp, current_cool_temp, current_mode, current_desired_temp
    try:
        with open("settings.txt", "r") as file:
            lines = file.readlines()
            current_heat_temp = int(lines[0].strip())
            current_cool_temp = int(lines[1].strip())
            current_desired_temp = int(lines[2].strip())
            current_mode = int(lines[3].strip())
        logging.info("Settings loaded.")
    except Exception as e:
        logging.error("Error loading settings, using default values: %s", e)
        current_heat_temp = 75
        current_cool_temp = 75
        current_mode = MODE_OFF
        current_desired_temp = 70

def load_scheduled_events():
    """Load scheduled events from a file on startup and schedule them."""
    global scheduled_events
    try:
        with open(SCHEDULE_FILE_PATH, 'r') as file:
            scheduled_events = json.load(file)
        print(f"Loaded {len(scheduled_events)} scheduled events from file.")
        
        # Schedule each event that was loaded
        for event in scheduled_events:
            if event['enabled']:
                action_time = datetime.datetime.strptime(event['time'], '%H:%M')  # Assuming time is in 'HH:MM' format
                # Combine today's date with the scheduled time
                action_datetime = datetime.datetime.combine(datetime.datetime.now().date(), action_time.time())
                schedule_action(event['id'], action_datetime, event['temperature'], event['mode'])
                print(f"Scheduled action for event ID {event['id']} at {action_datetime}")
                
    except (FileNotFoundError, json.JSONDecodeError):
        print("No scheduled events file found or file is corrupted. Starting fresh.")
        scheduled_events = []

def save_scheduled_events():
    """Save scheduled events to a file whenever they change."""
    global scheduled_events
    try:
        with open(SCHEDULE_FILE_PATH, 'w') as file:
            json.dump(scheduled_events, file, indent=4)
        print("Scheduled events saved to file.")
    except Exception as e:
        print(f"Error saving scheduled events to file: {e}")


def log_info():
    """Continuously log the current state to a file."""
    logging.info("Starting log info thread")
    global current_heat_temp, current_cool_temp, ambient_temp, current_mode, last_action_time

    while True:
        with lock:
            time_since_last_action = time.time() - last_action_time
            # Read the latest ambient temperature from the file
            #read_ambient_temperature()

            with open("info.txt", "w") as file:
                file.write(f"Time since last action: {time_since_last_action:.1f} seconds\n")
                file.write(f"Current heat temperature: {current_heat_temp}°F\n")
                file.write(f"Current cool temperature: {current_cool_temp}°F\n")
                file.write(f"Ambient temperature: {ambient_temp}°F\n")
                file.write(f"Current mode: {['OFF', 'HEAT', 'COOL'][current_mode]}\n")

        time.sleep(1)  # Log every second

@app.route("/", methods=["GET"])
def index():
    global current_mode, last_action_time

    logging.info("Rendering index page")

    # Calculate the time since the last action
    time_since_last_action = time.time() - last_action_time
    logging.debug("Time since last action: %.1f seconds", time_since_last_action)

    # Read the latest ambient temperature from the file
    #read_ambient_temperature()

    return render_template(
        "index.html",
        current_heat_temp=current_heat_temp,
        current_cool_temp=current_cool_temp,
        ambient_temp=ambient_temp,
        current_mode=current_mode,
        mode_options=["OFF", "HEAT", "COOL"],
        time_since_last_action=time_since_last_action
    )

@app.route("/set_temperature", methods=["POST"])
def set_temperature_route():
    global current_desired_temp
    data = request.get_json()

    if not data or 'temperature' not in data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    target_temp = int(data['temperature'])
    logging.info("Received temperature set request")
    result = set_temperature_logic(target_temp)
    if result["status"] == "success":
        current_desired_temp = target_temp
        logging.info("Set temperature to %d°F", target_temp)
        if not args.simulate:
            logging.info("Simulation mode is off, saving settings to file")
            # Save the settings to the file
            save_settings()
        return jsonify(result)
    else:
        logging.error("Failed to set temperature")
        return jsonify(result), 500

@app.route("/activate_light", methods=["POST"])
def activate_light_route():
    global last_action_time
    if time.time() - last_action_time < 45:
        logging.warning("Attempted to actuate light button within 45 seconds of last action")
        return jsonify({"status": "error", "message": "Action too soon"}), 429
    else:
        result = actuate_servo(servo_mode, 0, 180)
        if result:
            logging.info("Light button actuated")
            return jsonify({"status": "success", "light": "activated"})
        else:
            logging.error("Failed to actuate light button")
            return jsonify({"status": "error", "message": "Failed to activate light"}), 500

def set_mode_logic(mode):
    global current_mode, last_action_time, current_desired_temp
    if time.time() - last_action_time > 45:
        logging.info("More than 45 seconds since last action, activating screen")
        activate_screen()

    if mode == 'heat':
        success = cycle_mode_to_desired(MODE_HEAT)
        if success:
            logging.info("Switched mode to HEAT")
            current_mode = MODE_HEAT
            current_desired_temp = current_heat_temp
        else:
            logging.error("Failed to switch mode to HEAT")
            return False
    elif mode == 'cool':
        success = cycle_mode_to_desired(MODE_COOL)
        if success:
            logging.info("Switched mode to COOL")
            current_mode = MODE_COOL
            current_desired_temp = current_cool_temp
        else:
            logging.error("Failed to switch mode to COOL")
            return False
    elif mode == 'off':
        success = cycle_mode_to_desired(MODE_OFF)
        if success:
            logging.info("Switched mode to OFF")
            current_mode = MODE_OFF
        else:
            logging.error("Failed to switch mode to OFF")
            return False
    else:
        return False

    if not args.simulate:
        logging.info("Simulation mode is off, saving settings to file")
        # Save the settings to the file
        save_settings()
    return True

@app.route("/set_mode", methods=["POST"])
def set_mode():
    global current_mode, last_action_time, current_desired_temp
    data = request.get_json()
    
    if not data or 'mode' not in data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    
    mode = data['mode'].lower()

    result = set_mode_logic(mode)
    if not result:
        return jsonify({"status": "error", "message": "Invalid mode or failed to set mode"}), 400
    return jsonify({"status": "success", "mode": mode})


@app.route("/delete_schedule/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """Delete a scheduled event by its ID."""
    global scheduled_events

    # Find the schedule in the list and remove it
    scheduled_events = [event for event in scheduled_events if event['id'] != schedule_id]

    cancel_scheduled_action(schedule_id)  # Cancel the scheduled action if it exists

    save_scheduled_events()  # Save changes to file

    return jsonify({"status": "success", "message": f"Schedule with ID {schedule_id} deleted"}), 200

@app.route("/update_schedule/<int:schedule_id>", methods=["PATCH"])
def update_schedule(schedule_id):
    """Update the 'enabled' state of a scheduled event."""
    global scheduled_events
    data = request.get_json()

    if 'enabled' not in data:
        return jsonify({"status": "error", "message": "Invalid data, 'enabled' field is required"}), 400

    # Find the schedule by ID and update its 'enabled' state
    for event in scheduled_events:
        if event['id'] == schedule_id:
            event['enabled'] = data['enabled']
            if not data['enabled']:
                cancel_scheduled_action(schedule_id)  # Cancel the scheduled action if it is disabled
            else:
                # Correct the datetime parsing format to match 'HH:MM'
                action_time = datetime.datetime.strptime(event['time'], '%H:%M')
                schedule_action(schedule_id, action_time, event['temperature'], event['mode'])
            save_scheduled_events()  # Save changes to file
            return jsonify({"status": "success", "message": f"Schedule with ID {schedule_id} updated"}), 200

    return jsonify({"status": "error", "message": f"Schedule with ID {schedule_id} not found"}), 404


@app.route('/receive_image', methods=['POST'])
def receive_image():
    logging.info("Received request for /receive_image endpoint")
    global latest_image_path
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image part"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        # Save the image
        filename = 'latest_image.jpg'
        filepath = os.path.join(IMAGE_SAVE_PATH, filename)
        file.save(filepath)
        with lock:
            latest_image_path = filepath  # Update the global variable
        logging.info("Received and saved new image: %s", filepath)
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": "File not allowed"}), 400



@app.route('/video_feed')
def video_feed():
    logging.info("Received request for /video_feed endpoint")
    
    def generate():
        with lock:
            if latest_image_path and os.path.exists(latest_image_path):
                with open(latest_image_path, 'rb') as img_file:
                    frame = img_file.read()
                    logging.debug("Read latest image from disk")
            else:
                logging.warning("No image available to stream")
                frame = None

        if frame:
            # Prepare the frame to be sent in a multipart response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            logging.debug("Yielded a frame to client")
        else:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + b'\r\n')
            logging.error("No image available to yield")

    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )



@app.route("/set_schedule", methods=["POST"])
def set_schedule():
    global scheduled_events

    data = request.get_json()

    if not data:
        logging.error("Invalid data received")
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    # Extract data from the request
    time_str = data.get('time')
    temperature = data.get('temperature')
    mode = data.get('mode').lower()
    enabled = data.get('enabled')

    # Validate data
    if time_str is None or temperature is None or mode is None or enabled is None:
        logging.error("Missing fields in the request")
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    # Parse the time string into a datetime object
    try:
        action_time = datetime.datetime.strptime(time_str, '%H:%M')
        now = datetime.datetime.now()
        action_time = action_time.replace(year=now.year, month=now.month, day=now.day)
        if action_time < now:
            action_time += datetime.timedelta(days=1)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid time format"}), 400

    mode_constant = {
        'off': MODE_OFF,
        'heat': MODE_HEAT,
        'cool': MODE_COOL
    }.get(mode)

    if mode_constant is None:
        logging.error("Invalid mode received")
        return jsonify({"status": "error", "message": "Invalid mode"}), 400

    event_id = len(scheduled_events) + 1  # Simple ID assignment (incremental)
    # Only schedule if enabled is true
    if enabled:
        schedule_action(event_id, action_time, temperature, mode_constant)
    
    # Add the scheduled event to the list
    scheduled_events.append({
        "id": event_id,
        "time": time_str,
        "temperature": temperature,
        "mode": mode,
        "enabled": enabled
    })
    
    logging.info(f"Scheduled time: {time_str}, Temperature: {temperature}, Mode: {mode}, Enabled: {enabled}")
    save_scheduled_events()  # Save changes to file
    logging.info("Scheduled event saved to file")

    return jsonify({"status": "success", "message": "Schedule set successfully"}), 200

@app.route("/get_scheduled_events", methods=["GET"])
def get_scheduled_events():
    return jsonify(scheduled_events), 200

@app.route("/time_since_last_action", methods=["GET"])
def get_time_since_last_action():
    global last_action_time
    # Calculate the time since the last action
    time_since_last_action = time.time() - last_action_time
    logging.debug("Time since last action requested: %.1f seconds", time_since_last_action)
    response = jsonify({"time_since_last_action": round(time_since_last_action, 1)})
    return response

@app.route("/ambient_temperature", methods=["GET"])
def get_ambient_temperature():
    global ambient_temp
    # Ensure the latest ambient temperature is read
    logging.debug("Ambient temperature requested")
    read_ambient_temperature()
    response = jsonify({"ambient_temperature": ambient_temp})
    return response

@app.route("/current_mode", methods=["GET"])
def get_current_mode():
    global current_mode
    mode_name = ['OFF', 'HEAT', 'COOL'][current_mode]
    logging.debug("Current mode requested: %s", mode_name)
    response = jsonify({"current_mode": mode_name})
    return response

@app.route("/set_temperature", methods=["GET"])
def get_desired_temperature():
    global current_desired_temp
    logging.debug("Desired temperature requested: %d°F", current_desired_temp)
    response = jsonify({"desired_temperature": current_desired_temp})
    return response

@app.route("/temperature_settings")
def get_temperature_settings():
    return jsonify({
        "current_heat_temp": current_heat_temp,
        "current_cool_temp": current_cool_temp
    })

@app.route("/activate_light", methods=["POST"])
def activate_light():
    global last_action_time
    if time.time() - last_action_time < 45:
        logging.warning("Attempted to actuate light button within 45 seconds of last action")
    else:
        result = actuate_servo(servo_mode, 0, 180)
        if result:
            logging.info("Light button actuated")
        else:
            logging.error("Failed to actuate light button")
    return jsonify({"status": "success" if result else "error"})

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

def main():
    try:
        # Load settings from the file at startup
        logging.info("Starting main function")
        load_settings()
        load_scheduled_events()

        # Start logging in a separate thread
        logging.info("Starting logging thread")
        logging_thread = threading.Thread(target=log_info, daemon=True)
        logging_thread.start()

        # Start Flask web server
        logging.info("Starting Flask web server")
        app.debug = False  # Disable debug mode
        app.run(host="0.0.0.0", port=5000)

    finally:
        logging.info("Exiting application")
        if not args.simulate:
            # Set all servos to a neutral position before exiting
            servo_down.angle = 0
            servo_mode.angle = 0
            servo_up.angle = 180  # Return up servo to its default position

# Run the main function
if __name__ == "__main__":
    main()
