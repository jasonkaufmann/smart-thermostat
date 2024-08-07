import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import threading
from flask import Flask, render_template, request, redirect, jsonify
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Create the I2C bus interface.
logging.debug("Initializing I2C bus interface")
i2c = busio.I2C(board.SCL, board.SDA)

# Create a PCA9685 instance.
logging.debug("Creating PCA9685 instance")
pca = PCA9685(i2c)

# Set the PWM frequency to 50Hz, suitable for servos.
logging.debug("Setting PCA9685 frequency to 50Hz")
pca.frequency = 50

# Create servo objects for channels.
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
manual_override = False  # Manual override flag
last_action_time = time.time() - 100  # Start with time since last press > 45 seconds
screen_active = False  # Track whether the screen is active
lock = threading.Lock()
current_target_temp = None

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Smart Thermostat Control")
parser.add_argument('--simulate', action='store_true', help='Run in simulation mode (no servo actuation)')
args = parser.parse_args()

app = Flask(__name__)

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

def set_temperature(target_temp):
    """Set the temperature to the target_temp."""
    logging.info("Setting temperature to %d", target_temp)
    global current_heat_temp, current_cool_temp, ambient_temp, last_action_time, screen_active

    with lock:
        # Adjust mode based on ambient temperature and target
        if target_temp > ambient_temp and current_mode != MODE_HEAT:
            if time.time() - last_action_time > 45:
                activate_screen()
            logging.info("Switching to HEAT mode")
            cycle_mode_to_desired(MODE_HEAT)
        elif target_temp < ambient_temp and current_mode != MODE_COOL:
            if time.time() - last_action_time > 45:
                activate_screen()
            logging.info("Switching to COOL mode")
            cycle_mode_to_desired(MODE_COOL)

        if current_mode == MODE_HEAT:
            temp_difference = target_temp - current_heat_temp
            current_heat_temp = target_temp
            logging.info("Adjusting heat temperature to %d°F", current_heat_temp)
        elif current_mode == MODE_COOL:
            temp_difference = target_temp - current_cool_temp
            current_cool_temp = target_temp
            logging.info("Adjusting cool temperature to %d°F", current_cool_temp)
        else:
            logging.info("No adjustment needed in OFF mode")
            return  # No change needed in OFF mode

        # Adjust temperature
        if temp_difference > 0:  # Increase temperature
            logging.info("Increasing temperature by %d degrees", temp_difference)
            for _ in range(temp_difference):
                actuate_servo(servo_up, 180, 0)
            last_action_time = time.time()  # Update the last action time
        elif temp_difference < 0:  # Decrease temperature
            logging.info("Decreasing temperature by %d degrees", abs(temp_difference))
            for _ in range(abs(temp_difference)):
                actuate_servo(servo_down, 0, 180)
            last_action_time = time.time()  # Update the last action time

        if not args.simulate:
            # Save the settings to the file
            save_settings()

def activate_screen():
    """Activate the screen and set mode to HEAT or COOL."""
    logging.info("Activating screen...")
    global screen_active, last_action_time
    actuate_servo(servo_mode, 0, 180)
    last_action_time = time.time()  # Update the last action time

def read_ambient_temperature():
    """Read the ambient temperature from a file."""
    logging.info("Reading ambient temperature")
    global ambient_temp, current_target_temp
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
            if current_target_temp is not None:
                set_temperature(current_target_temp)  # Adjust temperature based on new ambient

def save_settings():
    """Save current settings to a file."""
    logging.info("Saving settings to file")
    global current_heat_temp, current_cool_temp, current_mode
    try:
        with open("settings.txt", "w") as file:
            file.write(f"{current_heat_temp}\n")
            file.write(f"{current_cool_temp}\n")
            file.write(f"{current_mode}\n")
        logging.info("Settings saved.")
    except Exception as e:
        logging.error("Error saving settings: %s", e)

def load_settings():
    """Load settings from a file."""
    logging.info("Loading settings from file")
    global current_heat_temp, current_cool_temp, current_mode
    try:
        with open("settings.txt", "r") as file:
            lines = file.readlines()
            current_heat_temp = int(lines[0].strip())
            current_cool_temp = int(lines[1].strip())
            current_mode = int(lines[2].strip())
        logging.info("Settings loaded.")
    except Exception as e:
        logging.error("Error loading settings, using default values: %s", e)
        current_heat_temp = 75
        current_cool_temp = 75
        current_mode = MODE_OFF

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
                file.write(f"Manual override: {'Active' if manual_override else 'Inactive'}\n")

        time.sleep(1)  # Log every second

@app.route("/", methods=["GET", "POST"])
def index():
    global current_mode, manual_override, last_action_time, current_target_temp

    logging.info("Received %s request to /", request.method)

    if request.method == "POST":
        logging.debug("Form data received: %s", request.form)

        # Handle manual override request
        if "manual_override" in request.form:
            manual_override = not manual_override
            logging.info("Manual override %s", "enabled" if manual_override else "disabled")
            return redirect("/")

        # Handle temperature set request
        if "set_temperature" in request.form:
            logging.info("Received temperature set request")
            target_temp = int(request.form.get("temperature", 75))
            set_temperature(target_temp)
            current_target_temp = target_temp
            logging.info("Set temperature to %d°F", target_temp)
            return redirect("/")

        # Handle mode set request only if manual override is active
        if "mode" in request.form and manual_override:
            selected_mode = request.form.get("mode")
            if selected_mode == "heat":
                cycle_mode_to_desired(MODE_HEAT)
                logging.info("Switched mode to HEAT")
            elif selected_mode == "cool":
                cycle_mode_to_desired(MODE_COOL)
                logging.info("Switched mode to COOL")
            else:
                cycle_mode_to_desired(MODE_OFF)
                logging.info("Switched mode to OFF")
            return redirect("/")

        # Handle light button click
        if "light" in request.form:
            if time.time() - last_action_time < 45:
                logging.warning("Attempted to actuate light button within 45 seconds of last action")
            else:
                actuate_servo(servo_mode, 0, 180)
                logging.info("Light button actuated")
                last_action_time = time.time()
            return redirect("/")

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
        manual_override=manual_override,
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
        app.debug = True
        app.run(host="0.0.0.0", port=5000)

    finally:
        logging.info("Exiting application")
        if not args.simulate:
            # Set all servos to a neutral position before exiting.
            servo_down.angle = 0
            servo_mode.angle = 0
            servo_up.angle = 180  # Return up servo to its default position
        pca.deinit()

# Run the main function
if __name__ == "__main__":
    main()
