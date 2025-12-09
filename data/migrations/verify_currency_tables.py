#!/usr/bin/env python3

import sqlite3
import os

def verify_tables():
    db_path = os.path.join(os.path.dirname(__file__), '../bot_world.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    tables = ['bot_currency', 'transactions', 'bot_assets', 'market_listings']
    
    for table in tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        result = cursor.fetchone()
        if result:
            print(f"✓ {table} table exists")
            
            # Count rows if applicable
            if table == 'bot_currency':
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {count} bots have currency accounts")
        else:
            print(f"✗ {table} table missing")
    
    conn.close()

if __name__ == "__main__":
    verify_tables()
