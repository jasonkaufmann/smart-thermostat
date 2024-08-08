import cv2
from picamera2 import Picamera2
import time

# Initialize the camera
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (1280, 720), "format": "RGB888"})
picam2.configure(config)
picam2.start()

# Capture and stream video
def stream_video():
    gst_str = (
        "appsrc ! videoconvert ! x264enc speed-preset=ultrafast tune=zerolatency "
        "! rtph264pay config-interval=1 pt=96 ! udpsink host=10.0.0.213 port=5000"
    )

    # OpenCV VideoWriter object using GStreamer pipeline
    out = cv2.VideoWriter(gst_str, cv2.CAP_GSTREAMER, 0, 30, (1280, 720), True)

    if not out.isOpened():
        print("Failed to open video writer")
        return

    print("Starting video stream...")
    try:
        while True:
            frame = picam2.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
            time.sleep(0.033)  # Sleep to match 30fps
    except KeyboardInterrupt:
        print("Stopping stream...")
    finally:
        out.release()
        picam2.stop()

if __name__ == "__main__":
    stream_video()
