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
import pytz
from scheduler import ThermostatScheduler, SchedulerError

# Application version - update this when making changes
APP_VERSION = "1.2.5"  # Display "OFF" instead of temperature when in OFF mode 

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

PI_ZERO_HOST = "http://10.0.0.191:5000"

# Create servo objects for channels
# logging.debug("Creating servo objects for channels")
servo_down = "down"  # Servo for down temperature
servo_mode = "mode"  # Servo for mode selection
servo_up = "up"    # Servo for up temperature

# Constants for modes
MODE_OFF = 0
MODE_HEAT = 1
MODE_COOL = 2

# Initialize the scheduler
scheduler = None

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
    global current_heat_temp, current_cool_temp, ambient_temp, last_action_time, screen_active, current_mode, current_desired_temp

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
            
            # Update desired temp so UI reflects the change (including scheduled changes)
            current_desired_temp = target_temp
            logging.info("Updated desired temperature to %d°F", current_desired_temp)
            
            # Save settings to persist scheduled changes
            if not args.simulate:
                save_settings()
            
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
        time_since_last_action=time_since_last_action,
        app_version=APP_VERSION
    )

@app.route("/set_temperature", methods=["POST"])
def set_temperature_route():
    global current_desired_temp
    data = request.get_json()

    if not data or 'temperature' not in data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    try:
        target_temp = int(data['temperature'])
    except ValueError:
        return jsonify({"status": "error", "message": "Temperature must be a number"}), 400
        
    # Validate temperature range
    if target_temp < 50 or target_temp > 90:
        return jsonify({"status": "error", "message": "Temperature must be between 50 and 90°F"}), 400
    
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
    
    # Check if this is being called for 6 AM schedule
    current_time = datetime.datetime.now(pytz.timezone('US/Pacific'))
    is_near_6am = 5 <= current_time.hour <= 7  # Consider calls between 5-7 AM as potentially 6 AM related
    
    if is_near_6am and mode == 'off':
        logging.info(f"===== 6AM MODE CHANGE REQUEST =====")
        logging.info(f"6AM Mode: Requested mode: {mode}")
        logging.info(f"6AM Mode: Current mode: {current_mode} ({'OFF' if current_mode == MODE_OFF else 'HEAT' if current_mode == MODE_HEAT else 'COOL'})")
        logging.info(f"6AM Mode: Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logging.info(f"6AM Mode: Time since last action: {time.time() - last_action_time:.1f} seconds")
    
    if time.time() - last_action_time > 45:
        logging.info("More than 45 seconds since last action, activating screen")
        if is_near_6am and mode == 'off':
            logging.info("6AM Mode: Activating screen due to inactivity timeout")
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
        if is_near_6am:
            logging.info("6AM Mode: Calling cycle_mode_to_desired(MODE_OFF)")
        success = cycle_mode_to_desired(MODE_OFF)
        if success:
            if is_near_6am:
                logging.info("6AM Mode: Successfully switched mode to OFF")
            else:
                logging.info("Switched mode to OFF")
            current_mode = MODE_OFF
        else:
            if is_near_6am:
                logging.error("6AM Mode: FAILED to switch mode to OFF")
            else:
                logging.error("Failed to switch mode to OFF")
            return False
    else:
        return False

    if not args.simulate:
        logging.info("Simulation mode is off, saving settings to file")
        # Save the settings to the file
        save_settings()
    
    if is_near_6am and mode == 'off':
        logging.info(f"===== 6AM MODE CHANGE COMPLETED =====")
        
    return True

@app.route("/set_mode", methods=["POST"])
def set_mode():
    global current_mode, last_action_time, current_desired_temp
    data = request.get_json()
    
    if not data or 'mode' not in data:
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    
    mode = data['mode'].lower()
    
    # Validate mode
    if mode not in ['off', 'heat', 'cool']:
        return jsonify({"status": "error", "message": "Mode must be 'off', 'heat', or 'cool'"}), 400

    result = set_mode_logic(mode)
    if not result:
        return jsonify({"status": "error", "message": "Failed to set mode"}), 500
    return jsonify({"status": "success", "mode": mode})


@app.route("/delete_schedule/<schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """Delete a scheduled event by its ID."""
    try:
        scheduler.delete_schedule(schedule_id)
        return jsonify({"status": "success", "message": f"Schedule {schedule_id} deleted"}), 200
    except SchedulerError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Error deleting schedule: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/update_schedule/<schedule_id>", methods=["PATCH"])
def update_schedule(schedule_id):
    """Update a scheduled event."""
    data = request.get_json()
    
    try:
        scheduler.update_schedule(schedule_id, **data)
        return jsonify({"status": "success", "message": f"Schedule {schedule_id} updated"}), 200
    except SchedulerError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Error updating schedule: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


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


# Vision-based temperature detection endpoints
vision_temperature_history = []
vision_last_detection = None

@app.route('/vision_annotated_image')
def vision_annotated_image():
    """Get the latest image with temperature annotation overlay"""
    global latest_image_path, vision_last_detection
    
    if not latest_image_path or not os.path.exists(latest_image_path):
        return '', 204
    
    try:
        # Read the image
        img = cv2.imread(latest_image_path)
        if img is None:
            return '', 204
        
        height, width = img.shape[:2]
        
        # Create overlay for temperature display
        overlay = img.copy()
        
        # Add gradient background at bottom
        gradient_height = 100
        for i in range(gradient_height):
            alpha = i / gradient_height * 0.7
            cv2.rectangle(overlay, (0, height-gradient_height+i), 
                         (width, height-gradient_height+i+1), (0, 0, 0), -1)
        
        img = cv2.addWeighted(overlay, 0.7, img, 0.3, 0)
        
        # Get detected temperature using Claude vision
        try:
            # Import vision integration module
            from vision_integration import get_claude_temperature, get_vision_confidence
            
            # Save current image for Claude to read
            temp_image_path = f"experimental/temp_vision_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            os.makedirs("experimental", exist_ok=True)
            cv2.imwrite(temp_image_path, img)
            
            # Get Claude's reading
            logging.info(f"[VISION] Calling Claude to read image: {temp_image_path}")
            detected_temp = get_claude_temperature(temp_image_path)
            confidence = get_vision_confidence()
            logging.info(f"[VISION] Claude returned: {detected_temp}°F with confidence: {confidence}")
            
            # Clean up temp image
            try:
                os.remove(temp_image_path)
            except:
                pass
                
        except Exception as e:
            # If Claude is not available, show error
            logging.error(f"Claude vision failed: {e}")
            detected_temp = None
            confidence = "ERROR"
        
        # Add temperature text
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if detected_temp is not None:
            temp_text = f"{detected_temp}°F"
            text_color = (0, 255, 0)  # Green for successful reading
        else:
            temp_text = "N/A"
            text_color = (0, 0, 255)  # Red for error
        
        # Center the temperature
        (text_width, text_height), _ = cv2.getTextSize(temp_text, font, 2, 3)
        text_x = (width - text_width) // 2
        
        cv2.putText(img, temp_text, (text_x, height-50), 
                   font, 2, text_color, 3)
        
        # Add label
        label = "Vision Detected Temp"
        (label_width, _), _ = cv2.getTextSize(label, font, 0.7, 2)
        label_x = (width - label_width) // 2
        cv2.putText(img, label, (label_x, height-85), 
                   font, 0.7, (255, 255, 255), 2)
        
        # Add confidence
        conf_text = f"Confidence: {confidence}"
        if confidence == "ERROR":
            conf_color = (0, 0, 255)  # Red for error
        elif confidence == "HIGH":
            conf_color = (0, 255, 0)  # Green for high
        elif confidence == "MEDIUM":
            conf_color = (0, 255, 255)  # Yellow for medium
        else:
            conf_color = (255, 255, 0)  # Cyan for low
            
        cv2.putText(img, conf_text, (20, height-15), 
                   font, 0.5, conf_color, 1)
        
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        cv2.putText(img, timestamp, (width-100, height-15), 
                   font, 0.5, (255, 255, 255), 1)
        
        # Encode image
        _, buffer = cv2.imencode('.jpg', img)
        
        # Update vision detection
        vision_last_detection = {
            'temperature': detected_temp,
            'confidence': confidence,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Only add to history if we have a valid temperature
        if detected_temp is not None:
            vision_temperature_history.append(vision_last_detection)
            if len(vision_temperature_history) > 100:  # Keep last 100 readings
                vision_temperature_history.pop(0)
        
        return Response(buffer.tobytes(), mimetype='image/jpeg')
        
    except Exception as e:
        logging.error(f"Error creating annotated image: {e}")
        return '', 500

@app.route('/vision_temperature_data')
@app.route('/vision_temperature_data/<timescale>')
def vision_temperature_data(timescale=None):
    """Get vision-based temperature history for plotting"""
    global vision_temperature_history, vision_last_detection
    
    # Try to load Claude readings from log file
    try:
        from vision_integration import claude_readings_file
        if os.path.exists(claude_readings_file):
            with open(claude_readings_file, 'r') as f:
                claude_history = json.load(f)
                
            # Use Claude readings if available
            if claude_history:
                # Convert to our format
                for reading in claude_history[-50:]:
                    if reading not in vision_temperature_history:
                        vision_temperature_history.append({
                            'timestamp': reading['timestamp'],
                            'temperature': reading['temperature'],
                            'confidence': 'HIGH'
                        })
    except:
        pass
    
    # Get last 50 points for cleaner display
    history = vision_temperature_history[-50:] if len(vision_temperature_history) > 50 else vision_temperature_history
    
    timestamps = [h['timestamp'] for h in history]
    temperatures = [h['temperature'] for h in history]
    
    # If timescale specified, use database
    if timescale and timescale in ['1minute', '1hour', '1day', '1week']:
        try:
            from vision_database import VisionDatabase
            db = VisionDatabase()
            db_data = db.get_readings_by_timescale(timescale)
            
            if db_data:
                timestamps = [d['timestamp'] for d in db_data]
                temperatures = [d['temperature'] for d in db_data]
                
                # Get most recent for current display
                latest = db_data[-1]
                current_temp = latest['temperature']
                last_update = latest['timestamp']
                
                # Check confidence based on how old the data is
                from vision_integration import get_vision_confidence
                confidence = get_vision_confidence()
                
                return jsonify({
                    'timestamps': timestamps,
                    'temperatures': temperatures,
                    'current_temp': current_temp,
                    'last_update': last_update,
                    'confidence': confidence,
                    'timescale': timescale
                })
        except Exception as e:
            logging.error(f"Error getting database readings: {e}")
    
    # Get the current vision state
    from vision_state import get_current_vision_data
    vision_data = get_current_vision_data()
    
    # Use vision state as primary source
    current_temp = vision_data['temperature']
    confidence = vision_data['confidence']
    last_update = vision_data['timestamp']
    
    # If no vision data, try history
    if current_temp is None and history:
        latest = history[-1]
        current_temp = latest.get('temperature')
        last_update = latest.get('timestamp')
        # Only recalculate confidence if we're using history data
        from vision_state import calculate_confidence
        confidence = calculate_confidence(last_update)
    
    return jsonify({
        'timestamps': timestamps,
        'temperatures': temperatures,
        'current_temp': current_temp,
        'last_update': last_update,
        'confidence': confidence,
        'timescale': 'realtime'
    })


@app.route("/set_schedule", methods=["POST"])
def set_schedule():
    """Create a new schedule using the new scheduler system"""
    logging.info(f"set_schedule endpoint hit - scheduler is {'initialized' if scheduler else 'None'}")
    logging.info(f"Request headers: {dict(request.headers)}")
    logging.info(f"Request method: {request.method}")
    logging.info(f"Request content type: {request.content_type}")
    
    try:
        data = request.get_json()
        logging.info(f"Received data: {data}")
    except Exception as e:
        logging.error(f"Failed to parse JSON: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

    if not data:
        logging.error("Invalid data received - data is None or empty")
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    # Extract data from the request
    time_str = data.get('time')
    temperature = data.get('temperature')
    mode = data.get('mode')
    days_of_week = data.get('days_of_week', 'daily')  # Default to daily if not provided
    enabled = data.get('enabled', True)

    # Validate required fields
    if not time_str:
        logging.error("Missing time in request")
        return jsonify({"status": "error", "message": "Missing time"}), 400
    
    if temperature is None:
        logging.error("Missing temperature in request")
        return jsonify({"status": "error", "message": "Missing temperature"}), 400
    
    if not mode:
        logging.error("Missing mode in request")
        return jsonify({"status": "error", "message": "Missing mode"}), 400

    # Check if scheduler is initialized
    if scheduler is None:
        logging.error("Scheduler is not initialized!")
        return jsonify({"status": "error", "message": "Scheduler not initialized. Please restart the application."}), 500
    
    try:
        # Use the new scheduler system
        schedule_id = scheduler.create_schedule(
            time_str=time_str,
            temperature=int(temperature),
            mode=mode.lower(),
            days_of_week=days_of_week,
            enabled=enabled
        )
        
        logging.info(f"Created schedule {schedule_id}: {time_str}, {temperature}°F, {mode}, {days_of_week}, enabled={enabled}")
        
        return jsonify({
            "status": "success", 
            "message": "Schedule created successfully",
            "schedule_id": schedule_id
        }), 200
        
    except SchedulerError as e:
        logging.error(f"Scheduler error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except AttributeError as e:
        logging.error(f"AttributeError in set_schedule: {e}")
        return jsonify({"status": "error", "message": "Invalid data format"}), 400
    except Exception as e:
        logging.error(f"Unexpected error creating schedule: {e}")
        return jsonify({"status": "error", "message": "Failed to create schedule"}), 500

@app.route("/get_scheduled_events", methods=["GET"])
def get_scheduled_events():
    try:
        schedules = scheduler.get_schedules()
        # Convert to the expected format for backward compatibility
        events = []
        for schedule in schedules:
            events.append({
                "id": schedule['id'],
                "time": schedule['time'],
                "temperature": schedule['temperature'],
                "mode": schedule['mode'],
                "enabled": schedule['enabled'],
                "days_of_week": schedule.get('days_of_week', 'daily'),
                "next_execution": schedule.get('next_execution', ''),
                "last_executed": schedule.get('last_executed', ''),
                "last_error": schedule.get('last_error', '')
            })
        return jsonify(events), 200
    except Exception as e:
        logging.error(f"Error getting schedules: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route("/schedule_history/<schedule_id>", methods=["GET"])
def get_schedule_history(schedule_id):
    """Get execution history for a specific schedule"""
    try:
        limit = request.args.get('limit', 10, type=int)
        history = scheduler.get_schedule_history(schedule_id, limit)
        return jsonify(history), 200
    except Exception as e:
        logging.error(f"Error getting schedule history: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

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

@app.route('/version', methods=['GET'])
def get_version():
    return jsonify({"version": APP_VERSION}), 200

@app.errorhandler(404)
def not_found(error):
    """Return JSON instead of HTML for 404 errors"""
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Return JSON instead of HTML for 500 errors"""
    logging.error(f"Internal server error: {error}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """Return JSON instead of HTML for all other errors"""
    logging.error(f"Unhandled exception: {error}")
    return jsonify({"status": "error", "message": str(error)}), 500

def sync_vision_state_continuously():
    """Continuously sync vision readings from database to state file"""
    import sqlite3
    from datetime import datetime
    
    STATE_FILE = "experimental/vision_state.json"
    DB_FILE = "vision_temperatures.db"
    
    while True:
        try:
            # Connect to database
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get latest reading
            cursor.execute('''
                SELECT * FROM vision_readings 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''')
            
            latest = cursor.fetchone()
            conn.close()
            
            if latest:
                # Parse timestamp
                timestamp_str = latest['timestamp']
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                # Save to state file
                state = {
                    "temperature": latest['temperature'],
                    "timestamp": timestamp.isoformat(),
                    "confidence": latest['confidence']
                }
                
                os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f)
                
                logging.debug(f"Vision state synced: {latest['temperature']}°F at {timestamp_str}")
            
        except Exception as e:
            logging.error(f"Error syncing vision state: {e}")
        
        # Sleep for 10 seconds before next sync
        time.sleep(10)

def main():
    global scheduler
    try:
        # Load settings from the file at startup
        logging.info("Starting main function")
        load_settings()
        
        # Initialize the scheduler with callbacks
        scheduler = ThermostatScheduler(
            temperature_callback=lambda temp: set_temperature_logic(temp).get("status") == "success",
            mode_callback=lambda mode: set_mode_logic(mode)
        )
        scheduler.start()

        # Start logging in a separate thread
        logging.info("Starting logging thread")
        logging_thread = threading.Thread(target=log_info, daemon=True)
        logging_thread.start()
        
        # Start vision state sync thread
        logging.info("Starting vision state sync thread")
        vision_sync_thread = threading.Thread(target=sync_vision_state_continuously, daemon=True)
        vision_sync_thread.start()

        # Start Flask web server
        logging.info("Starting Flask web server")
        app.debug = False  # Disable debug mode
        app.run(host="0.0.0.0", port=5000)

    finally:
        logging.info("Exiting application")
        if scheduler:
            scheduler.stop()
        if not args.simulate:
            # Set all servos to a neutral position before exiting
            servo_down.angle = 0
            servo_mode.angle = 0
            servo_up.angle = 180  # Return up servo to its default position

# Run the main function
if __name__ == "__main__":
    main()
