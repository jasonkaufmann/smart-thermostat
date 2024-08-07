import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import threading
from flask import Flask, render_template, request, redirect, jsonify
import argparse
# Create the I2C bus interface.
i2c = busio.I2C(board.SCL, board.SDA)

# Create a PCA9685 instance.
pca = PCA9685(i2c)

# Set the PWM frequency to 50Hz, suitable for servos.
pca.frequency = 50

# Create servo objects for channels.
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
    if args.simulate:
        print(f"Simulating servo movement: {servo} from {start_angle} to {target_angle}")
    else:
        servo.angle = target_angle
        time.sleep(0.3)  # Delay for 0.3 seconds
        servo.angle = start_angle
        time.sleep(0.5)  # Delay for 0.5 seconds

def cycle_mode_to_desired(desired_mode):
    """Cycle through the modes until the desired mode is reached."""
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
        print(f"Mode changed to: {['OFF', 'HEAT', 'COOL', 'MANUAL'][current_mode]}")

def set_temperature(target_temp):
    """Set the temperature to the target_temp."""
    global current_heat_temp, current_cool_temp, ambient_temp, last_action_time, screen_active

    with lock:
        # Activate the screen if time since last action is > 45 seconds
        if time.time() - last_action_time > 45:
            activate_screen()

        # Adjust mode based on ambient temperature and target
        if target_temp > ambient_temp and current_mode != MODE_HEAT:
            print("Switching to HEAT mode")
            cycle_mode_to_desired(MODE_HEAT)
        elif target_temp < ambient_temp and current_mode != MODE_COOL:
            print("Switching to COOL mode")
            cycle_mode_to_desired(MODE_COOL)

        if current_mode == MODE_HEAT:
            temp_difference = target_temp - current_heat_temp
            current_heat_temp = target_temp
            print(f"Adjusting heat temperature to {current_heat_temp}°F")
        elif current_mode == MODE_COOL:
            temp_difference = target_temp - current_cool_temp
            current_cool_temp = target_temp
            print(f"Adjusting cool temperature to {current_cool_temp}°F")
        else:
            print("No adjustment needed in OFF mode")
            return  # No change needed in OFF mode

        # Adjust temperature
        if temp_difference > 0:  # Increase temperature
            for _ in range(temp_difference):
                actuate_servo(servo_up, 180, 0)
        elif temp_difference < 0:  # Decrease temperature
            for _ in range(abs(temp_difference)):
                actuate_servo(servo_down, 0, 180)

        last_action_time = time.time()  # Update the last action time

        if not args.simulate:
            # Save the settings to the file
            save_settings()

def activate_screen():
    """Activate the screen and set mode to HEAT or COOL."""
    global screen_active, last_action_time
    print("Activating screen...")
    actuate_servo(servo_mode, 0, 180)
    last_action_time = time.time()  # Update the last action time

def read_ambient_temperature():
    """Read the ambient temperature from a file."""
    global ambient_temp, current_target_temp
    ambient_temp_new = None
    try:
        with open("temp.txt", "r") as file:
            ambient_temp_new = float(file.read().strip())
            #print(f"Read ambient temperature: {ambient_temp}°F")
    except Exception as e:
        print(f"Error reading ambient temperature: {e}")

    if ambient_temp_new is not None:
        if ambient_temp_new != ambient_temp:
            ambient_temp = ambient_temp_new
            print(f"Ambient temperature updated to: {ambient_temp_new}°F")
            if current_target_temp is not None:
                set_temperature(current_target_temp)  # Adjust temperature based on new ambient
       
def save_settings():
    """Save current settings to a file."""
    global current_heat_temp, current_cool_temp, current_mode
    try:
        with open("settings.txt", "w") as file:
            file.write(f"{current_heat_temp}\n")
            file.write(f"{current_cool_temp}\n")
            file.write(f"{current_mode}\n")
        print("Settings saved.")
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_settings():
    """Load settings from a file."""
    global current_heat_temp, current_cool_temp, current_mode
    try:
        with open("settings.txt", "r") as file:
            lines = file.readlines()
            current_heat_temp = int(lines[0].strip())
            current_cool_temp = int(lines[1].strip())
            current_mode = int(lines[2].strip())
        print("Settings loaded.")
    except Exception as e:
        print(f"Error loading settings, using default values: {e}")
        current_heat_temp = 75
        current_cool_temp = 75
        current_mode = MODE_OFF

def log_info():
    """Continuously log the current state to a file."""
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

    if request.method == "POST":
        # Handle manual override request
        if "manual_override" in request.form:
            manual_override = not manual_override
            print(f"Manual override {'enabled' if manual_override else 'disabled'}")
            return redirect("/")

        # Handle temperature set request
        if "set_temperature" in request.form:
            target_temp = int(request.form.get("temperature", 75))
            set_temperature(target_temp)
            current_target_temp = target_temp
            return redirect("/")

        # Handle mode set request only if manual override is active
        if "mode" in request.form and manual_override:
            selected_mode = request.form.get("mode")
            if selected_mode == "heat":
                cycle_mode_to_desired(MODE_HEAT)
            elif selected_mode == "cool":
                cycle_mode_to_desired(MODE_COOL)
            else:
                cycle_mode_to_desired(MODE_OFF)
            return redirect("/")

        # Handle light button click
        if "light" in request.form:
            if time.time() - last_action_time < 45:
                print("Cannot actuate light button within 45 seconds of last action. Light should be on.")
            else:
                actuate_servo(servo_mode, 0, 180)
                print("Light button actuated")
                last_action_time = time.time()
            return redirect("/")

    # Calculate the time since the last action
    time_since_last_action = time.time() - last_action_time

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
    return jsonify({"time_since_last_action": round(time_since_last_action, 1)})

@app.route("/ambient_temperature", methods=["GET"])
def get_ambient_temperature():
    global ambient_temp
    # Ensure the latest ambient temperature is read
    read_ambient_temperature()
    return jsonify({"ambient_temperature": ambient_temp})

def main():
    try:
        # Load settings from the file at startup
        load_settings()

        # Start logging in a separate thread
        logging_thread = threading.Thread(target=log_info, daemon=True)
        logging_thread.start()

        # Start Flask web server
        app.debug = True
        app.run(host="0.0.0.0", port=5000)

    finally:
        if not args.simulate:
            # Set all servos to a neutral position before exiting.
            servo_down.angle = 0
            servo_mode.angle = 0
            servo_up.angle = 180  # Return up servo to its default position
        pca.deinit()

# Run the main function
if __name__ == "__main__":
    main()
