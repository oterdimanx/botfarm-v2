import sqlite3

def enhance_cycle_tracking():
    db_path = 'data/bot_world.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add columns for bot needs tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cycle_bot_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_number INTEGER NOT NULL,
                bot_id INTEGER NOT NULL,
                bot_name TEXT NOT NULL,
                energy REAL DEFAULT 0,
                social REAL DEFAULT 0,
                curiosity REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            )
        ''')
        
        print("✅ Created enhanced cycle_bot_stats table")
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enhance_cycle_tracking()