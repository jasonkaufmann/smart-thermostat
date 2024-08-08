from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
import cv2
import time

app = Flask(__name__)

# Initialize the camera
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # Capture frame-by-frame
        frame = picam2.capture_array()
        # Convert RGB to BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame_bgr)
        # Convert the frame to bytes
        frame_bytes = buffer.tobytes()
        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        # Wait for 3 seconds before capturing the next frame
        time.sleep(3)

@app.route('/video_feed')
def video_feed():
    # Return a response with the JPEG frames
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    # HTML template to display the video stream
    return render_template_string('''
    <!doctype html>
    <html>
    <head>
        <title>Video Stream</title>
    </head>
    <body>
        <h1>Video Stream</h1>
        <img id="video" src="{{ url_for('video_feed') }}" style="width:640px; height:480px;">
        <script>
            // JavaScript to reload the image every 3 seconds
            setInterval(() => {
                const video = document.getElementById('video');
                video.src = "{{ url_for('video_feed') }}" + '?t=' + new Date().getTime();
            }, 3000);
        </script>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    # Start the Flask app on all IP addresses, port 5000
    app.run(host='0.0.0.0', port=5000)
