import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from pynput import keyboard

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

# Function to move the servo to 180 degrees and back to 0 degrees.
def actuate_servo(servo):
    servo.angle = 180
    time.sleep(0.5)  # Delay for 0.5 seconds
    servo.angle = 0
    time.sleep(0.5)  # Delay for 0.5 seconds

# Function to handle key press events
def on_press(key):
    try:
        if key == keyboard.Key.up:
            actuate_servo(servo_up)
        elif key == keyboard.Key.down:
            actuate_servo(servo_down)
        elif key == keyboard.Key.right:
            actuate_servo(servo_mode)
    except AttributeError:
        # Handle special keys if needed
        pass

# Set all servos to a neutral position at the start
servo_down.angle = 0
servo_mode.angle = 0
servo_up.angle = 0

print("Use the arrow keys to control the servos. Press 'Ctrl+C' to exit.")

# Start listening to keyboard events
listener = keyboard.Listener(on_press=on_press)
listener.start()

try:
    while True:
        time.sleep(0.1)  # Keep the program running
except KeyboardInterrupt:
    pass
finally:
    # Set all servos to a neutral position before exiting.
    servo_down.angle = 0
    servo_mode.angle = 0
    servo_up.angle = 0
    pca.deinit()
    listener.stop()
