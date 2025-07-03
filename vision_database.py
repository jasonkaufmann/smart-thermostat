#!/usr/bin/env python3
"""
Database storage for vision temperature readings with timescale views
"""
import sqlite3
import json
from datetime import datetime, timedelta
import os

class VisionDatabase:
    def __init__(self, db_path="vision_temperatures.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create main readings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vision_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature INTEGER,
                confidence TEXT,
                raw_response TEXT
            )
        ''')
        
        # Create index for faster time-based queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON vision_readings(timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_reading(self, temperature, confidence="HIGH", raw_response=None):
        """Add a new temperature reading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO vision_readings (temperature, confidence, raw_response)
            VALUES (?, ?, ?)
        ''', (temperature, confidence, raw_response))
        
        conn.commit()
        conn.close()
    
    def get_readings_by_timescale(self, timescale="1hour"):
        """Get readings for different timescales with appropriate aggregation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        if timescale == "1minute":
            # Last minute - all data points
            start_time = now - timedelta(minutes=1)
            cursor.execute('''
                SELECT timestamp, temperature, confidence
                FROM vision_readings
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', (start_time,))
            
        elif timescale == "1hour":
            # Last hour - 1 minute averages
            start_time = now - timedelta(hours=1)
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m-%d %H:%M:00', timestamp) as minute,
                    AVG(temperature) as temperature,
                    COUNT(*) as count
                FROM vision_readings
                WHERE timestamp > ?
                GROUP BY minute
                ORDER BY minute ASC
            ''', (start_time,))
            
        elif timescale == "1day":
            # Last day - 15 minute averages
            start_time = now - timedelta(days=1)
            cursor.execute('''
                SELECT 
                    datetime((strftime('%s', timestamp) / 900) * 900, 'unixepoch') as quarter_hour,
                    AVG(temperature) as temperature,
                    COUNT(*) as count
                FROM vision_readings
                WHERE timestamp > ?
                GROUP BY quarter_hour
                ORDER BY quarter_hour ASC
            ''', (start_time,))
            
        elif timescale == "1week":
            # Last week - hourly averages
            start_time = now - timedelta(weeks=1)
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    AVG(temperature) as temperature,
                    COUNT(*) as count
                FROM vision_readings
                WHERE timestamp > ?
                GROUP BY hour
                ORDER BY hour ASC
            ''', (start_time,))
        
        else:
            # Default to last hour
            return self.get_readings_by_timescale("1hour")
        
        rows = cursor.fetchall()
        conn.close()
        
        # Format for chart display
        data = []
        for row in rows:
            if timescale == "1minute":
                data.append({
                    'timestamp': row[0],
                    'temperature': row[1],
                    'confidence': row[2]
                })
            else:
                data.append({
                    'timestamp': row[0],
                    'temperature': round(row[1], 1),
                    'count': row[2]
                })
        
        return data
    
    def cleanup_old_data(self):
        """Remove data older than 1 week"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(weeks=1)
        cursor.execute('''
            DELETE FROM vision_readings
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total readings
        cursor.execute('SELECT COUNT(*) FROM vision_readings')
        total = cursor.fetchone()[0]
        
        # Readings in last hour
        hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute('SELECT COUNT(*) FROM vision_readings WHERE timestamp > ?', (hour_ago,))
        last_hour = cursor.fetchone()[0]
        
        # Average temperature last 24 hours
        day_ago = datetime.now() - timedelta(days=1)
        cursor.execute('SELECT AVG(temperature) FROM vision_readings WHERE timestamp > ?', (day_ago,))
        avg_temp = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_readings': total,
            'readings_last_hour': last_hour,
            'avg_temp_24h': round(avg_temp, 1) if avg_temp else None
        }

# Integration with vision system
def log_vision_reading(temperature, confidence="HIGH"):
    """Log a vision reading to the database"""
    db = VisionDatabase()
    db.add_reading(temperature, confidence)
    
    # Cleanup old data occasionally
    import random
    if random.random() < 0.01:  # 1% chance
        deleted = db.cleanup_old_data()
        if deleted > 0:
            print(f"Cleaned up {deleted} old vision readings")

if __name__ == "__main__":
    # Test the database
    db = VisionDatabase()
    
    # Add some test data
    print("Adding test data...")
    import random
    for i in range(20):
        temp = 77 + random.randint(-2, 2)
        db.add_reading(temp, "HIGH")
    
    # Get different timescales
    for scale in ["1minute", "1hour", "1day", "1week"]:
        data = db.get_readings_by_timescale(scale)
        print(f"\n{scale}: {len(data)} data points")
        if data:
            print(f"  Latest: {data[-1]}")
    
    # Show stats
    stats = db.get_stats()
    print(f"\nStats: {stats}")