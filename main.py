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

# Function to move the servo from its current angle to the specified target angle and back.
def actuate_servo(servo, start_angle, target_angle):
    servo.angle = target_angle
    time.sleep(0.3)  # Delay for 0.5 seconds
    servo.angle = start_angle
    time.sleep(0.5)  # Delay for 0.5 seconds

# Main function to handle keyboard input using curses
def main(stdscr):
    # Set up the curses environment
    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(True)  # Make getch() non-blocking
    stdscr.clear()

    stdscr.addstr(0, 0, "Use the arrow keys to control the servos. Press 'q' to exit.")
    stdscr.refresh()

    # Set initial positions for servos
    servo_down.angle = 0
    servo_mode.angle = 0
    servo_up.angle = 180  # Start up servo at 180 degrees

    try:
        while True:
            key = stdscr.getch()

            if key == curses.KEY_UP:
                actuate_servo(servo_up, 180, 0)
            elif key == curses.KEY_DOWN:
                actuate_servo(servo_down, 0, 180)
            elif key == curses.KEY_RIGHT:
                actuate_servo(servo_mode, 0, 180)
            elif key == ord('q'):  # Quit on 'q' key
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
