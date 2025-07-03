#!/usr/bin/env python3
import sqlite3
import os

print("=== Checking Vision Database ===\n")

# Find vision-related databases
db_files = [f for f in os.listdir('.') if f.endswith('.db') and 'vision' in f.lower()]
print(f"Found database files: {db_files}")

for db_file in db_files:
    print(f"\n--- Database: {db_file} ---")
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Tables: {[t[0] for t in tables]}")
        
        # For each table, show schema and recent data
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"Columns: {[c[1] for c in columns]}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Row count: {count}")
            
            # Get recent entries if any
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 3")
                rows = cursor.fetchall()
                print("Recent entries:")
                for row in rows:
                    print(f"  {row}")
                    
        conn.close()
    except Exception as e:
        print(f"Error reading {db_file}: {e}")