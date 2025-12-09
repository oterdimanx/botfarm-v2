import sqlite3
import os

def migrate_cycle_tracking():
    db_path = 'data/bot_world.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cycle_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_number INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_currency REAL DEFAULT 0,
                total_transactions INTEGER DEFAULT 0,
                economic_events TEXT,
                notes TEXT
            )
        ''')
        
        print("✅ Created cycle_records table")
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate_cycle_tracking()