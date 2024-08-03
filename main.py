import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

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

try:
    servos = [servo0, servo1, servo2, servo3]

    while True:
        for servo in servos:
            # Move servo to 0 degrees.
            servo.angle = 0
            time.sleep(1)

            # Move servo to 90 degrees.
            servo.angle = 90
            time.sleep(1)

            # Move servo to 180 degrees.
            servo.angle = 180
            time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    # Set all servos to a neutral position before exiting.
    for servo in servos:
        servo.angle = 90
    pca.deinit()