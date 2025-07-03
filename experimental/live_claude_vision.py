#!/usr/bin/env python3
"""
Live monitoring that saves images for Claude Code to analyze
This demonstrates how Claude Code can directly read temperatures
"""
import os
import time
import json
from datetime import datetime
from claude_code_vision import ClaudeCodeVisionReader

class LiveClaudeMonitor:
    def __init__(self):
        self.reader = ClaudeCodeVisionReader()
        self.results_file = "experimental/claude_analysis/temperature_readings.json"
        self.readings = []
        
        # Load existing readings if any
        if os.path.exists(self.results_file):
            with open(self.results_file, 'r') as f:
                self.readings = json.load(f)
    
    def capture_and_wait_for_analysis(self):
        """Capture image and wait for Claude Code to analyze it"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Capturing thermostat...")
        
        image_path, latest_path = self.reader.capture_for_analysis()
        
        if image_path:
            print(f"✓ Saved to: {latest_path}")
            print("📸 Claude Code can now analyze this image")
            
            # Create a placeholder for the reading
            reading = {
                "timestamp": datetime.now().isoformat(),
                "image_path": image_path,
                "temperature": None,  # Claude Code will fill this in
                "status": "awaiting_analysis"
            }
            
            self.readings.append(reading)
            self.save_readings()
            
            return latest_path
        
        return None
    
    def record_temperature(self, temperature):
        """Record the temperature that Claude Code read"""
        if self.readings and self.readings[-1]["status"] == "awaiting_analysis":
            self.readings[-1]["temperature"] = temperature
            self.readings[-1]["status"] = "analyzed"
            self.save_readings()
            
            print(f"✅ Recorded temperature: {temperature}°F")
            self.display_stats()
    
    def save_readings(self):
        """Save readings to file"""
        with open(self.results_file, 'w') as f:
            json.dump(self.readings, f, indent=2)
    
    def display_stats(self):
        """Display statistics from readings"""
        analyzed = [r for r in self.readings if r["temperature"] is not None]
        
        if analyzed:
            temps = [r["temperature"] for r in analyzed]
            avg_temp = sum(temps) / len(temps)
            
            print(f"\n📊 Statistics ({len(analyzed)} readings):")
            print(f"   Average: {avg_temp:.1f}°F")
            print(f"   Min: {min(temps)}°F")
            print(f"   Max: {max(temps)}°F")
            print(f"   Latest: {temps[-1]}°F")
    
    def run_interactive(self):
        """Run in interactive mode"""
        print("🌡️  Claude Code Live Thermostat Monitor")
        print("="*50)
        print("This will capture images for Claude Code to analyze")
        print("After each capture, Claude Code can read the temperature")
        print("="*50)
        
        while True:
            # Capture image
            latest_path = self.capture_and_wait_for_analysis()
            
            if latest_path:
                # Show the path for Claude Code
                print(f"\n💡 To analyze: Look at {latest_path}")
                print("   Claude Code should read the temperature from the display")
                
                # In a real integration, Claude Code would automatically
                # analyze and call record_temperature()
                
                # For demo, prompt for the reading
                temp_input = input("\nWhat temperature does Claude Code see? (or 'q' to quit): ")
                
                if temp_input.lower() == 'q':
                    break
                
                try:
                    temp = int(temp_input)
                    self.record_temperature(temp)
                except ValueError:
                    print("Invalid temperature")
            
            # Wait before next capture
            print("\nWaiting 10 seconds before next capture...")
            time.sleep(10)

def demo_direct_analysis():
    """Demonstrate direct Claude Code analysis"""
    monitor = LiveClaudeMonitor()
    
    print("📷 Capturing current thermostat display...")
    latest_path = monitor.capture_and_wait_for_analysis()
    
    if latest_path:
        print(f"\n✅ Image ready at: {latest_path}")
        print("\n🔍 Claude Code Analysis:")
        print("   Looking at the thermostat display image...")
        
        # Claude Code can directly look at the image and read it
        # For this demo, I'll analyze it now
        
        return latest_path

if __name__ == "__main__":
    # Run the demo
    image_path = demo_direct_analysis()
    
    if image_path:
        print("\n💬 Claude Code can now read this thermostat display")
        print("   and provide the temperature reading directly!")