import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
import keyboard  # Import the keyboard module for detecting key presses

# Create the I2C bus interface.
i2c = busio.I2C(board.SCL, board.SDA)

# Create a PCA9685 instance.
pca = PCA9685(i2c)

# Set the PWM frequency to 50Hz, suitable for servos.
pca.frequency = 50

# Create a servo object on channel 0.
servo0 = servo.Servo(pca.channels[0])
servo1 = servo.Servo(pca.channels[1])
servo2 = servo.Servo(pca.channels[14])
servo3 = servo.Servo(pca.channels[15])

# Initial angle for servo0
servo0_angle = 90  # Start at a neutral position

# Function to update servo0's position and print the current angle
def update_servo_position(servo, angle):
    servo.angle = angle
    print(f"Servo0 position: {angle} degrees")

try:
    servos = [servo0, servo1, servo2, servo3]
    
    # Set all servos to a neutral position at the start
    for servo in servos:
        servo.angle = 90

    update_servo_position(servo0, servo0_angle)  # Set initial position for servo0

    print("Use the up and down arrow keys to adjust servo0 position. Press 'Ctrl+C' to exit.")
    
    while True:
        if keyboard.is_pressed('up'):
            if servo0_angle < 180:
                servo0_angle += 1
                update_servo_position(servo0, servo0_angle)
                time.sleep(0.1)  # Add a small delay to avoid too fast changes
                
        elif keyboard.is_pressed('down'):
            if servo0_angle > 0:
                servo0_angle -= 1
                update_servo_position(servo0, servo0_angle)
                time.sleep(0.1)  # Add a small delay to avoid too fast changes

except KeyboardInterrupt:
    pass

finally:
    # Set all servos to a neutral position before exiting.
    for servo in servos:
        servo.angle = 90
    pca.deinit()
