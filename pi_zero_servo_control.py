# File: pi_zero_servo_control.py
from flask import Flask, Response, request, jsonify
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo
from picamera2 import Picamera2
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

# Initialize the camera
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (320, 240), "format": "RGB888"})
picam2.configure(config)
picam2.start()

def actuate_servo(servo, start_angle, target_angle):
    """Move the servo from start_angle to target_angle and back."""
    servo.angle = target_angle
    time.sleep(0.3)
    servo.angle = start_angle
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

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            frame = picam2.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, buffer = cv2.imencode('.jpg', frame_bgr)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
