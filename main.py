import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import threading

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
current_mode = MODE_OFF
last_action_time = time.time() - 46  # Assume start with time since last press > 45 seconds
lock = threading.Lock()

def actuate_servo(servo, start_angle, target_angle):
    """Move the servo from start_angle to target_angle and back."""
    servo.angle = target_angle
    time.sleep(0.3)  # Delay for 0.3 seconds
    servo.angle = start_angle
    time.sleep(0.5)  # Delay for 0.5 seconds

def change_mode(current_mode):
    """Cycle through the modes: OFF -> HEAT -> COOL -> OFF."""
    actuate_servo(servo_mode, 0, 180)

    if current_mode == MODE_OFF:
        return MODE_HEAT
    elif current_mode == MODE_HEAT:
        return MODE_COOL
    else:
        return MODE_OFF

def set_temperature(target_temp):
    """Set the temperature to the target_temp."""
    global current_heat_temp, current_cool_temp, current_mode, last_action_time

    with lock:
        if current_mode == MODE_HEAT:
            temp_difference = target_temp - current_heat_temp
            current_heat_temp = target_temp
        elif current_mode == MODE_COOL:
            temp_difference = target_temp - current_cool_temp
            current_cool_temp = target_temp
        else:
            return  # No change needed in OFF mode

        # Adjust temperature
        if temp_difference > 0:  # Increase temperature
            for _ in range(temp_difference):
                actuate_servo(servo_up, 180, 0)
        elif temp_difference < 0:  # Decrease temperature
            for _ in range(abs(temp_difference)):
                actuate_servo(servo_down, 0, 180)

        last_action_time = time.time()  # Update the last action time

def log_info():
    """Continuously log the current state to a file."""
    global current_heat_temp, current_cool_temp, current_mode, last_action_time

    while True:
        with lock:
            time_since_last_action = time.time() - last_action_time

            with open("info.txt", "w") as file:
                file.write(f"Time since last action: {time_since_last_action:.1f} seconds\n")
                file.write(f"Current heat temperature: {current_heat_temp}°F\n")
                file.write(f"Current cool temperature: {current_cool_temp}°F\n")
                file.write(f"Current mode: {['OFF', 'HEAT', 'COOL'][current_mode]}\n")

        time.sleep(1)  # Log every second

def handle_input():
    """Handle user input for setting the temperature."""
    global last_action_time

    while True:
        temp_input = input("Enter the desired temperature and press 'Enter': ").strip()

        try:
            target_temp = int(temp_input)

            # Actuate mode button if more than 45 seconds have passed
            if time.time() - last_action_time > 45:
                print("Activating screen...")
                actuate_servo(servo_mode, 0, 180)

            set_temperature(target_temp)
            last_action_time = time.time()  # Update the last action time

        except ValueError:
            print("Invalid input. Please enter a valid number.")

def main():
    try:
        # Start logging and input handling in separate threads
        logging_thread = threading.Thread(target=log_info, daemon=True)
        logging_thread.start()

        input_thread = threading.Thread(target=handle_input, daemon=True)
        input_thread.start()

        input_thread.join()  # Wait for the input thread to finish (which it won't until quit)

    finally:
        # Set all servos to a neutral position before exiting.
        servo_down.angle = 0
        servo_mode.angle = 0
        servo_up.angle = 180  # Return up servo to its default position
        pca.deinit()

# Run the main function
if __name__ == "__main__":
    main()
