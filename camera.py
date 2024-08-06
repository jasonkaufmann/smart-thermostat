from flask import Flask, render_template, Response
from picamera2 import Picamera2, Preview
import cv2
import io

app = Flask(__name__)

# Initialize the camera
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (1920, 1080), "format": "RGB888"})
picam2.configure(config)
picam2.start()

def gen_frames():
    while True:
        frame = picam2.capture_array()
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    # Main page for video streaming.
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    # Video streaming route.
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
