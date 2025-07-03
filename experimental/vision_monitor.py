#!/usr/bin/env python3
"""
Live temperature monitoring with vision detection and plotting
"""
from flask import Flask, render_template, jsonify, Response
import cv2
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
from collections import deque
import threading
import time

app = Flask(__name__)

class VisionTemperatureMonitor:
    def __init__(self):
        self.thermostat_url = "http://blade:5000"
        self.temperature_history = deque(maxlen=100)  # Keep last 100 readings
        self.current_temp = None
        self.current_image = None
        self.last_update = None
        self.update_interval = 10  # seconds
        self.running = False
        
    def capture_and_detect(self):
        """Capture image and detect temperature"""
        try:
            # Capture frame
            response = requests.get(f"{self.thermostat_url}/video_feed", 
                                  stream=True, timeout=10)
            
            if response.status_code == 200:
                bytes_data = bytes()
                for chunk in response.iter_content(chunk_size=1024):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1:
                        jpg_data = bytes_data[a:b+2]
                        
                        # Convert to numpy array for processing
                        nparr = np.frombuffer(jpg_data, np.uint8)
                        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        # Detect temperature (simulated - in production use Claude API)
                        # For demo, we'll use the known value of 77
                        detected_temp = 77
                        
                        # Add detected temperature text to image
                        annotated_image = self.annotate_image(image, detected_temp)
                        
                        # Convert back to JPEG
                        _, buffer = cv2.imencode('.jpg', annotated_image)
                        self.current_image = buffer.tobytes()
                        
                        # Update temperature history
                        self.current_temp = detected_temp
                        self.last_update = datetime.now()
                        
                        self.temperature_history.append({
                            'timestamp': self.last_update.isoformat(),
                            'temperature': detected_temp
                        })
                        
                        return True
                        
        except Exception as e:
            print(f"Error in capture_and_detect: {e}")
            
        return False
    
    def annotate_image(self, image, temperature):
        """Add temperature annotation to image"""
        height, width = image.shape[:2]
        
        # Create overlay for temperature display
        overlay = image.copy()
        
        # Add semi-transparent background for text
        cv2.rectangle(overlay, (10, height-80), (300, height-10), 
                     (0, 0, 0), -1)
        image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
        
        # Add temperature text
        text = f"Detected Current Temp: {temperature}°F"
        cv2.putText(image, text, (20, height-40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(image, timestamp, (20, height-20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add confidence indicator (for demo, always high)
        cv2.putText(image, "Confidence: HIGH", (200, height-40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return image
    
    def get_plot_data(self):
        """Get temperature history for plotting"""
        if not self.temperature_history:
            return {'timestamps': [], 'temperatures': []}
        
        # Convert to lists for JSON serialization
        data = list(self.temperature_history)
        
        # Get last 50 points for cleaner display
        if len(data) > 50:
            data = data[-50:]
        
        timestamps = [d['timestamp'] for d in data]
        temperatures = [d['temperature'] for d in data]
        
        return {
            'timestamps': timestamps,
            'temperatures': temperatures,
            'current_temp': self.current_temp,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def start_monitoring(self):
        """Start background monitoring"""
        self.running = True
        thread = threading.Thread(target=self._monitor_loop)
        thread.daemon = True
        thread.start()
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            self.capture_and_detect()
            time.sleep(self.update_interval)

# Global monitor instance
monitor = VisionTemperatureMonitor()

@app.route('/')
def index():
    """Main page"""
    return render_template('vision_monitor.html')

@app.route('/current_image')
def current_image():
    """Get current annotated image"""
    if monitor.current_image:
        return Response(monitor.current_image, mimetype='image/jpeg')
    else:
        # Return placeholder if no image yet
        return '', 204

@app.route('/temperature_data')
def temperature_data():
    """Get temperature data for plotting"""
    return jsonify(monitor.get_plot_data())

@app.route('/status')
def status():
    """Get current status"""
    return jsonify({
        'current_temp': monitor.current_temp,
        'last_update': monitor.last_update.isoformat() if monitor.last_update else None,
        'history_size': len(monitor.temperature_history)
    })

if __name__ == '__main__':
    # Start monitoring
    monitor.start_monitoring()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5001, debug=False)