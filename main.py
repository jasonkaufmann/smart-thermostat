import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import curses

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

# Function to move the servo from its current angle to the specified target angle and back.
def actuate_servo(servo, start_angle, target_angle):
    servo.angle = target_angle
    time.sleep(0.3)  # Delay for 0.3 seconds
    servo.angle = start_angle
    time.sleep(0.5)  # Delay for 0.5 seconds

# Function to change the mode
def change_mode(current_mode):
    actuate_servo(servo_mode, 0, 180)

    # Cycle through the modes: OFF -> HEAT -> COOL -> OFF
    if current_mode == MODE_OFF:
        return MODE_HEAT
    elif current_mode == MODE_HEAT:
        return MODE_COOL
    else:
        return MODE_OFF

# Function to set the temperature
def set_temperature(current_temp, target_temp, current_mode):
    temp_difference = target_temp - current_temp

    # Decide mode based on target temperature
    if target_temp > current_temp:
        desired_mode = MODE_HEAT
    elif target_temp < current_temp:
        desired_mode = MODE_COOL
    else:
        return current_temp  # No change needed

    # Change mode if necessary
    if current_mode != desired_mode:
        while current_mode != desired_mode:
            current_mode = change_mode(current_mode)

    # Adjust temperature
    if temp_difference > 0:  # Increase temperature
        for _ in range(temp_difference):
            actuate_servo(servo_up, 180, 0)
    elif temp_difference < 0:  # Decrease temperature
        for _ in range(abs(temp_difference)):
            actuate_servo(servo_down, 0, 180)

    return target_temp

# Main function to handle input
def main(stdscr):
    # Set up the curses environment
    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(True)  # Make getch() non-blocking
    stdscr.clear()

    stdscr.addstr(0, 0, "Enter the desired temperature and press 'Enter'. Press 'q' to exit.\n")
    stdscr.refresh()

    # Set initial positions for servos
    servo_down.angle = 0
    servo_mode.angle = 0
    servo_up.angle = 180  # Start up servo at 180 degrees

    current_mode = MODE_OFF
    current_temp = 75
    last_action_time = time.time()

    try:
        while True:
            # Calculate the time since the last action
            time_since_last_action = time.time() - last_action_time
            stdscr.addstr(5, 0, f"Time since last action: {time_since_last_action:.1f} seconds")
            stdscr.addstr(6, 0, f"Current set temperature: {current_temp}°F")
            stdscr.clrtoeol()
            stdscr.refresh()

            # Process temperature input
            stdscr.addstr(2, 0, "Enter temperature: ")
            curses.echo()  # Enable echoing of input characters
            temp_input = stdscr.getstr(3, 0, 5).decode('utf-8')  # Read up to 5 characters for the temperature input
            curses.noecho()  # Disable echoing

            # Check if we need to actuate the mode button to activate the screen
            if time_since_last_action > 45:
                stdscr.addstr(1, 0, "Activating screen...")
                stdscr.clrtoeol()
                stdscr.refresh()
                actuate_servo(servo_mode, 0, 180)
                last_action_time = time.time()

            try:
                target_temp = int(temp_input)
                current_temp = set_temperature(current_temp, target_temp, current_mode)
                last_action_time = time.time()  # Update the last action time
            except ValueError:
                stdscr.addstr(4, 0, "Invalid input. Please enter a valid number.")
                stdscr.clrtoeol()
                stdscr.refresh()
                continue

            stdscr.addstr(2, 0, f"Current temperature: {current_temp}°F, Mode: {['OFF', 'HEAT', 'COOL'][current_mode]}")
            stdscr.clrtoeol()
            stdscr.refresh()

            key = stdscr.getch()
            if key == ord('q'):  # Quit on 'q' key
                break

            time.sleep(0.1)  # Add a small delay to reduce CPU usage

    finally:
        # Set all servos to a neutral position before exiting.
        servo_down.angle = 0
        servo_mode.angle = 0
        servo_up.angle = 180  # Return up servo to its default position
        pca.deinit()

# Run the main function inside the curses wrapper
curses.wrapper(main)
