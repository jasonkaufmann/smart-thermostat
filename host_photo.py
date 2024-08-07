from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# Define the directory where the image is located
IMAGE_DIR = os.path.abspath('.')
IMAGE_NAME = 'latest_photo.jpg'

@app.route('/')
def serve_image():
    """Serve the image on the root URL."""
    return send_from_directory(IMAGE_DIR, IMAGE_NAME)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
