from flask import Flask, jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def home():
    return jsonify(message='Hello from Flask!')

@app.route('/random-number')
def random_number():
    number = random.randint(1, 100)
    return jsonify(number=number)

if __name__ == '__main__':
    app.debug = True  # Enable auto-reload  
    app.run(host='0.0.0.0', port=5001)  # Run on port 5001
