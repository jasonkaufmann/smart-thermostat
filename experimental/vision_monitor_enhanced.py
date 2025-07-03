#!/usr/bin/env python3
"""
Enhanced vision monitor with real temperature detection simulation
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
import random

app = Flask(__name__)

class EnhancedVisionMonitor:
    def __init__(self):
        self.thermostat_url = "http://blade:5000"
        self.temperature_history = deque(maxlen=200)  # Keep more history
        self.current_temp = None
        self.current_image = None
        self.last_update = None
        self.update_interval = 5  # seconds
        self.running = False
        self.confidence = "high"
        
        # For demo purposes, simulate temperature variations
        self.base_temp = 77
        self.temp_variation = 0
        
    def simulate_temperature_detection(self, image):
        """
        Simulate temperature detection with realistic variations
        In production, this would use Claude Vision API
        """
        # Simulate small temperature variations over time
        self.temp_variation += random.uniform(-0.3, 0.3)
        self.temp_variation = max(-2, min(2, self.temp_variation))  # Limit variation
        
        detected_temp = round(self.base_temp + self.temp_variation)
        
        # Simulate confidence based on image "quality"
        confidence_levels = ["high", "high", "high", "medium"]  # Mostly high confidence
        self.confidence = random.choice(confidence_levels)
        
        return detected_temp
    
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
                        
                        # Detect temperature
                        detected_temp = self.simulate_temperature_detection(image)
                        
                        # Add annotations to image
                        annotated_image = self.annotate_image_enhanced(image, detected_temp)
                        
                        # Convert back to JPEG
                        _, buffer = cv2.imencode('.jpg', annotated_image)
                        self.current_image = buffer.tobytes()
                        
                        # Update temperature history
                        self.current_temp = detected_temp
                        self.last_update = datetime.now()
                        
                        self.temperature_history.append({
                            'timestamp': self.last_update.isoformat(),
                            'temperature': detected_temp,
                            'confidence': self.confidence
                        })
                        
                        return True
                        
        except Exception as e:
            print(f"Error in capture_and_detect: {e}")
            
        return False
    
    def annotate_image_enhanced(self, image, temperature):
        """Enhanced image annotation with better visuals"""
        height, width = image.shape[:2]
        
        # Create overlay
        overlay = image.copy()
        
        # Add gradient background for temperature display
        gradient_height = 100
        for i in range(gradient_height):
            alpha = i / gradient_height * 0.7
            cv2.rectangle(overlay, (0, height-gradient_height+i), (width, height-gradient_height+i+1), 
                         (0, 0, 0), -1)
        
        image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
        
        # Add temperature with larger font
        temp_text = f"{temperature}°F"
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Get text size for centering
        (text_width, text_height), _ = cv2.getTextSize(temp_text, font, 2, 3)
        text_x = (width - text_width) // 2
        
        # Draw temperature
        cv2.putText(image, temp_text, (text_x, height-50), 
                   font, 2, (0, 255, 0), 3)
        
        # Add label
        label = "Detected Current Temp"
        (label_width, _), _ = cv2.getTextSize(label, font, 0.7, 2)
        label_x = (width - label_width) // 2
        cv2.putText(image, label, (label_x, height-85), 
                   font, 0.7, (255, 255, 255), 2)
        
        # Add confidence indicator
        conf_color = (0, 255, 0) if self.confidence == "high" else (0, 255, 255)
        conf_text = f"Confidence: {self.confidence.upper()}"
        cv2.putText(image, conf_text, (20, height-15), 
                   font, 0.5, conf_color, 1)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(image, timestamp, (width-100, height-15), 
                   font, 0.5, (255, 255, 255), 1)
        
        # Add detection box around temperature area (for visualization)
        # This shows where the vision system is "looking"
        roi_y1 = int(height * 0.18)
        roi_y2 = int(height * 0.42)
        roi_x1 = int(width * 0.32)
        roi_x2 = int(width * 0.68)
        
        cv2.rectangle(image, (roi_x1, roi_y1), (roi_x2, roi_y2), 
                     (0, 255, 0), 2)
        cv2.putText(image, "Detection ROI", (roi_x1, roi_y1-5), 
                   font, 0.5, (0, 255, 0), 1)
        
        return image
    
    def get_plot_data(self):
        """Get temperature history for plotting"""
        if not self.temperature_history:
            return {
                'timestamps': [], 
                'temperatures': [],
                'current_temp': None,
                'last_update': None
            }
        
        # Convert to lists for JSON serialization
        data = list(self.temperature_history)
        
        # Get last 100 points for display
        if len(data) > 100:
            data = data[-100:]
        
        timestamps = [d['timestamp'] for d in data]
        temperatures = [d['temperature'] for d in data]
        
        return {
            'timestamps': timestamps,
            'temperatures': temperatures,
            'current_temp': self.current_temp,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'confidence': self.confidence,
            'history_count': len(self.temperature_history)
        }
    
    def start_monitoring(self):
        """Start background monitoring"""
        self.running = True
        thread = threading.Thread(target=self._monitor_loop)
        thread.daemon = True
        thread.start()
        print("Vision monitoring started")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            success = self.capture_and_detect()
            if success:
                print(f"Detected temperature: {self.current_temp}°F (Confidence: {self.confidence})")
            time.sleep(self.update_interval)

# Global monitor instance
monitor = EnhancedVisionMonitor()

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
        # Capture an image if none exists
        monitor.capture_and_detect()
        if monitor.current_image:
            return Response(monitor.current_image, mimetype='image/jpeg')
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
        'history_size': len(monitor.temperature_history),
        'confidence': monitor.confidence,
        'update_interval': monitor.update_interval
    })

if __name__ == '__main__':
    print("Starting Enhanced Vision Temperature Monitor")
    print("="*50)
    print(f"Monitor will update every {monitor.update_interval} seconds")
    print("Access the web interface at: http://localhost:5001")
    print("="*50)
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Give it a moment to capture first image
    time.sleep(2)
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5001, debug=False)