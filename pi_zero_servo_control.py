from flask import Flask, jsonify, request
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from picamera2 import Picamera2
import threading
import requests
import logging
import cv2 

app = Flask(__name__)

# Create the I2C bus interface
i2c = busio.I2C(board.SCL, board.SDA)

# Create a PCA9685 instance
pca = PCA9685(i2c)
pca.frequency = 50  # Set the PWM frequency to 50Hz

# Create servo objects for channels
servo_down = servo.Servo(pca.channels[0])
servo_mode = servo.Servo(pca.channels[1])
servo_up = servo.Servo(pca.channels[2])

# Initialize the camera with lower resolution and frame rate
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (800, 600), "format": "YUV420"},
    controls={"FrameRate": 5}  # Limit to 5 frames per second
)
picam2.configure(config)
picam2.start()

# Blade server URL
BLADE_SERVER_URL = 'http://10.0.0.213:5000'  # Update with the actual IP or hostname

# Create a session for persistent connections
session = requests.Session()

def actuate_servo(servo_motor, start_angle, target_angle):
    """Move the servo from start_angle to target_angle and back."""
    servo_motor.angle = target_angle
    time.sleep(0.3)
    servo_motor.angle = start_angle
    time.sleep(0.5)

@app.route('/actuate_servo', methods=['POST'])
def handle_actuate_servo():
    data = request.get_json()
    servo_name = data.get('servo')
    start_angle = data.get('start_angle', 0)
    target_angle = data.get('target_angle', 180)

    if servo_name == 'down':
        actuate_servo(servo_down, start_angle, target_angle)
    elif servo_name == 'mode':
        actuate_servo(servo_mode, start_angle, target_angle)
    elif servo_name == 'up':
        actuate_servo(servo_up, start_angle, target_angle)
    else:
        return jsonify({"status": "error", "message": "Invalid servo name"}), 400

    return jsonify({"status": "success"})

def capture_and_send_image():
    while True:
        logging.info("Capturing and sending image")
        # Capture an image
        frame = picam2.capture_array()
        # Extract the grayscale component
        grayscale_frame = frame[:frame.shape[0]//2, :]
        # Encode the frame in JPEG format with lower quality
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]  # Quality from 0 to 100
        ret, buffer = cv2.imencode('.jpg', grayscale_frame, encode_param)
        if not ret:
            logging.error("Failed to encode image")
            continue
        # Prepare the image data for sending
        image_data = buffer.tobytes()
        # Send the image to the blade server
        try:
            response = session.post(
                f"{BLADE_SERVER_URL}/receive_image",
                files={'image': ('image.jpg', image_data, 'image/jpeg')},
                timeout=10  # Set a timeout for the request
            )
            response.raise_for_status()
            logging.info("Image sent successfully")
        except requests.RequestException as e:
            logging.error(f"Error sending image: {e}")
        # Release resources
        del frame
        del grayscale_frame
        del buffer
        del image_data
        # Wait for 10 seconds before capturing the next frame
        time.sleep(4)

# Start the image capture and send thread
threading.Thread(target=capture_and_send_image, daemon=True).start()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='pi_zero.log',
        filemode='a'
    )
    app.run(host='0.0.0.0', port=5000)
