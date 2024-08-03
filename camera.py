from flask import Flask, render_template, Response
from picamera import PiCamera
from io import BytesIO
import time

app = Flask(__name__)
camera = PiCamera()

def gen_frames():
    # Stream camera frames.
    while True:
        frame = BytesIO()
        camera.capture(frame, format='jpeg', use_video_port=True)
        frame.seek(0)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame.read() + b'\r\n')

@app.route('/')
def index():
    # Main page for video streaming.
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    # Video streaming route.
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    camera.start_preview()
    time.sleep(2)  # Allow camera to warm up
    app.run(host='0.0.0.0', port=5000)
