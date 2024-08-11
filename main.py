from flask import Flask, Response, render_template, request, jsonify
from picamera2 import Picamera2
import cv2
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import threading
import argparse
import logging
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Create the I2C bus interface
logging.debug("Initializing I2C bus interface")
i2c = busio.I2C(board.SCL, board.SDA)

# Create a PCA9685 instance
logging.debug("Creating PCA9685 instance")
pca = PCA9685(i2c)

# Set the PWM frequency to 50Hz, suitable for servos
logging.debug("Setting PCA9685 frequency to 50Hz")
pca.frequency = 50

# Create servo objects for channels
logging.debug("Creating servo objects for channels")
servo_down = servo.Servo(pca.channels[0])  # Servo for down temperature
servo_mode = servo.Servo(pca.channels[1])  # Servo for mode selection
servo_up = servo.Servo(pca.channels[2])    # Servo for up temperature

# Constants for modes
MODE_OFF = 0
MODE_HEAT = 1
MODE_COOL = 2

# Global variables for managing state
current_heat_temp = 75
current_cool_temp = 75
ambient_temp = 75  # Default ambient temperature
current_mode = MODE_OFF
last_action_time = time.time() - 100  # Start with time since last press > 45 seconds
screen_active = False  # Track whether the screen is active
lock = threading.Lock()
current_desired_temp = None

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Smart Thermostat Control")
parser.add_argument('--simulate', action='store_true', help='Run in simulation mode (no servo actuation)')
args = parser.parse_args()

# Initialize the camera
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (1920, 1080), "format": "RGB888"})
picam2.configure(config)
picam2.start()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        # Allow the GET, POST, and OPTIONS methods
        response = app.make_default_options_response()
        headers = response.headers

        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

        return response

def generate_frames():
    while True:
        # Capture frame-by-frame
        frame = picam2.capture_array()
        # Convert RGB to BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        # Convert the frame to bytes
        frame_bytes = buffer.tobytes()
        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        # Wait for 1 second before capturing the next frame
        time.sleep(1)

@app.route('/video_feed')
def video_feed():
    # Return a response with the JPEG frames
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def actuate_servo(servo, start_angle, target_angle):
    """Move the servo from start_angle to target_angle and back."""
    logging.info("Actuating servo from angle %d to %d", start_angle, target_angle)
    if args.simulate:
        logging.debug(f"Simulating servo movement: {servo} from {start_angle} to {target_angle}")
    else:
        servo.angle = target_angle
        time.sleep(0.3)  # Delay for 0.3 seconds
        servo.angle = start_angle
        time.sleep(0.5)  # Delay for 0.5 seconds

def cycle_mode_to_desired(desired_mode):
    """Cycle through the modes until the desired mode is reached."""
    logging.info("Cycling mode to desired mode: %s", ['OFF', 'HEAT', 'COOL'][desired_mode])
    global current_mode
    while current_mode != desired_mode:
        actuate_servo(servo_mode, 0, 180)
        if current_mode == MODE_OFF:
            current_mode = MODE_HEAT
        elif current_mode == MODE_HEAT:
            current_mode = MODE_COOL
        elif current_mode == MODE_COOL:
            current_mode = MODE_OFF  # Add manual mode in the cycle
        else:
            current_mode = MODE_OFF
        logging.debug("Mode changed to: %s", ['OFF', 'HEAT', 'COOL', 'MANUAL'][current_mode])

def set_temperature_logic(target_temp):
    """Core logic for setting the temperature."""
    logging.info("Function set_temperature_logic called with target_temp: %d", target_temp)
    global current_heat_temp, current_cool_temp, ambient_temp, last_action_time, screen_active

    # Attempt to acquire lock with a timeout
    acquired = lock.acquire(timeout=5)
    if not acquired:
        logging.error("Failed to acquire lock in set_temperature_logic")
        return {"status": "error", "message": "Could not acquire lock"}

    try:
        logging.debug("Entered lock block in set_temperature_logic")
        logging.debug("Current mode: %s", ['OFF', 'HEAT', 'COOL'][current_mode])
        logging.debug("Ambient temperature: %d°F", ambient_temp)

        # Adjust mode based on ambient temperature and target
        if target_temp > ambient_temp and current_mode != MODE_HEAT:
            if time.time() - last_action_time > 45:
                logging.info("More than 45 seconds since last action, activating screen")
                activate_screen()
            logging.debug("Target temp (%d) > ambient temp (%d) and current mode is not HEAT", target_temp, ambient_temp)
            logging.info("Switching to HEAT mode")
            cycle_mode_to_desired(MODE_HEAT)
        elif target_temp < ambient_temp and current_mode != MODE_COOL:
            logging.debug("Target temp (%d) < ambient temp (%d) and current mode is not COOL", target_temp, ambient_temp)
            if time.time() - last_action_time > 45:
                logging.info("More than 45 seconds since last action, activating screen")
                activate_screen()
            logging.info("Switching to COOL mode")
            cycle_mode_to_desired(MODE_COOL)

        if current_mode == MODE_HEAT:
            temp_difference = target_temp - current_heat_temp
            logging.debug("Calculated temperature difference for HEAT mode: %d", temp_difference)
            current_heat_temp = target_temp
            logging.info("Adjusting heat temperature to %d°F", current_heat_temp)
        elif current_mode == MODE_COOL:
            temp_difference = target_temp - current_cool_temp
            logging.debug("Calculated temperature difference for COOL mode: %d", temp_difference)
            current_cool_temp = target_temp
            logging.info("Adjusting cool temperature to %d°F", current_cool_temp)
        else:
            logging.info("No adjustment needed in OFF mode")
            return {"status": "success", "message": "No change needed"}

        # Adjust temperature
        if temp_difference > 0:  # Increase temperature
            if time.time() - last_action_time > 45:
                logging.info("More than 45 seconds since last action, activating screen")
                activate_screen()
            logging.info("Increasing temperature by %d degrees", temp_difference)
            for _ in range(temp_difference):
                logging.debug("Actuating servo to increase temperature")
                actuate_servo(servo_up, 180, 0)
            last_action_time = time.time()  # Update the last action time
            logging.debug("Updated last_action_time after increasing temperature")
        elif temp_difference < 0:  # Decrease temperature
            if time.time() - last_action_time > 45:
                logging.info("More than 45 seconds since last action, activating screen")
                activate_screen()
            logging.info("Decreasing temperature by %d degrees", abs(temp_difference))
            for _ in range(abs(temp_difference)):
                logging.debug("Actuating servo to decrease temperature")
                actuate_servo(servo_down, 0, 180)
            last_action_time = time.time()  # Update the last action time
            logging.debug("Updated last_action_time after decreasing temperature")

        if not args.simulate:
            logging.info("Simulation mode is off, saving settings to file")
            # Save the settings to the file
            save_settings()
        else:
            logging.info("Simulation mode is on, not saving settings")
        return {"status": "success"}
    finally:
        lock.release()
        logging.debug("Lock released in set_temperature_logic")

def set_temperature(target_temp):
    """Wrapper to use within Flask context."""
    result = set_temperature_logic(target_temp)
    if result["status"] == "error":
        return jsonify(result), 503
    return jsonify(result)

def activate_screen():
    """Activate the screen and set mode to HEAT or COOL."""
    logging.info("Activating screen...")
    global screen_active, last_action_time
    actuate_servo(servo_mode, 0, 180)
    last_action_time = time.time()  # Update the last action time

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
            # Directly call the logic without Flask's jsonify
            set_temperature_logic(current_desired_temp)

def save_settings():
    """Save current settings to a file."""
    logging.info("Saving settings to file")
    global current_heat_temp, current_cool_temp, current_mode
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
            read_ambient_temperature()

            with open("info.txt", "w") as file:
                file.write(f"Time since last action: {time_since_last_action:.1f} seconds\n")
                file.write(f"Current heat temperature: {current_heat_temp}°F\n")
                file.write(f"Current cool temperature: {current_cool_temp}°F\n")
                file.write(f"Ambient temperature: {ambient_temp}°F\n")
                file.write(f"Current mode: {['OFF', 'HEAT', 'COOL', 'MANUAL'][current_mode]}\n")

        time.sleep(1)  # Log every second

@app.route("/", methods=["GET", "POST"])
def index():
    global current_mode, last_action_time, current_desired_temp

    logging.info("Received %s request to /", request.method)

    if request.method == "POST":
        data = request.get_json()
        logging.debug("JSON data received: %s", data)

        # Handle temperature set request
        if "set_temperature" in data:
            logging.info("Received temperature set request")
            target_temp = int(data.get("temperature", 75))
            set_temperature(target_temp)
            current_desired_temp = target_temp
            logging.info("Set temperature to %d°F", target_temp)
            return jsonify({"status": "success", "temperature": target_temp})

        # Handle mode set request only if manual override is active
        if "mode" in data:
            selected_mode = data.get("mode")
            if selected_mode == "heat":
                cycle_mode_to_desired(MODE_HEAT)
                logging.info("Switched mode to HEAT")
            elif selected_mode == "cool":
                cycle_mode_to_desired(MODE_COOL)
                logging.info("Switched mode to COOL")
            else:
                cycle_mode_to_desired(MODE_OFF)
                logging.info("Switched mode to OFF")
            return jsonify({"status": "success", "mode": selected_mode})

        # Handle light button click
        if "light" in data:
            if time.time() - last_action_time < 45:
                logging.warning("Attempted to actuate light button within 45 seconds of last action")
            else:
                actuate_servo(servo_mode, 0, 180)
                logging.info("Light button actuated")
                last_action_time = time.time()
            return jsonify({"status": "success", "light": "activated"})

    # Calculate the time since the last action
    time_since_last_action = time.time() - last_action_time
    logging.debug("Time since last action: %.1f seconds", time_since_last_action)

    # Read the latest ambient temperature from the file
    read_ambient_temperature()

    return render_template(
        "index.html",
        current_heat_temp=current_heat_temp,
        current_cool_temp=current_cool_temp,
        ambient_temp=ambient_temp,
        current_mode=current_mode,
        mode_options=["OFF", "HEAT", "COOL"],
        time_since_last_action=time_since_last_action
    )

@app.route("/time_since_last_action", methods=["GET"])
def get_time_since_last_action():
    global last_action_time
    # Calculate the time since the last action
    time_since_last_action = time.time() - last_action_time
    logging.debug("Time since last action requested: %.1f seconds", time_since_last_action)
    return jsonify({"time_since_last_action": round(time_since_last_action, 1)})

@app.route("/ambient_temperature", methods=["GET"])
def get_ambient_temperature():
    global ambient_temp
    # Ensure the latest ambient temperature is read
    logging.debug("Ambient temperature requested")
    read_ambient_temperature()
    return jsonify({"ambient_temperature": ambient_temp})

@app.route("/current_mode", methods=["GET"])
def get_current_mode():
    global current_mode
    mode_name = ['OFF', 'HEAT', 'COOL', 'MANUAL'][current_mode]
    logging.debug("Current mode requested: %s", mode_name)
    return jsonify({"current_mode": mode_name})

@app.route("/set_temperature", methods=["GET"])
def get_desired_temperature():
    global current_desired_temp
    logging.debug("Desired temperature requested: %d°F", current_desired_temp)
    return jsonify({"desired_temperature": current_desired_temp})

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
        actuate_servo(servo_mode, 0, 180)
        logging.info("Light button actuated")
        last_action_time = time.time()
    return jsonify({"status": "success"})

def main():
    try:
        # Load settings from the file at startup
        logging.info("Starting main function")
        load_settings()

        # Start logging in a separate thread
        logging.info("Starting logging thread")
        logging_thread = threading.Thread(target=log_info, daemon=True)
        logging_thread.start()

        # Start Flask web server
        logging.info("Starting Flask web server")
        app.debug = False
        app.run(host="0.0.0.0", port=5000)

    finally:
        logging.info("Exiting application")
        if not args.simulate:
            # Set all servos to a neutral position before exiting
            servo_down.angle = 0
            servo_mode.angle = 0
            servo_up.angle = 180  # Return up servo to its default position
        pca.deinit()

# Run the main function
if __name__ == "__main__":
    main()
