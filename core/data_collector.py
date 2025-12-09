"""
Simple external data collector
Step 1: Just get weather data for one location
"""

import requests
import json
import sqlite3
from datetime import datetime

class DataCollector:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_data_table()
    
    def _create_data_table(self):
        """Create table for external data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS external_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def collect_weather(self, location="Paris"):
        """Collect simple weather data - STEP 1: Basic collection only"""
        try:
            # Using a free, no-auth weather API
            url = f"http://wttr.in/{location}?format=j1"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                weather_data = response.json()
                
                # Store in database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO external_data (data_type, data_json)
                    VALUES (?, ?)
                ''', ('weather', json.dumps(weather_data)))
                
                conn.commit()
                conn.close()
                
                print(f"✅ Collected weather data for {location}")
                return True
            else:
                print(f"❌ Weather API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Weather collection error: {e}")
            return False
    
    def get_latest_weather(self):
        """Get latest weather data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data_json FROM external_data 
            WHERE data_type = 'weather' 
            ORDER BY collected_at DESC 
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None