#!/usr/bin/env python3
"""
Migration script to add currency system tables to bot_world.db
"""

import sqlite3
import os
import sys

def migrate_database():
    # Get the path to the database
    db_path = os.path.join(os.path.dirname(__file__), '../bot_world.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Connected to database successfully")
        
        # Create bot_currency table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_currency (
            bot_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 100.0, -- Starting balance
            last_income TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
        )
        ''')
        print("Created bot_currency table")
        
        # Create transactions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_bot INTEGER,
            to_bot INTEGER,
            amount REAL NOT NULL,
            transaction_type TEXT DEFAULT 'transfer', -- 'transfer', 'income', 'payment', 'reward'
            reason TEXT,
            status TEXT DEFAULT 'completed', -- 'completed', 'failed', 'pending'
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_bot) REFERENCES bots(id) ON DELETE SET NULL,
            FOREIGN KEY (to_bot) REFERENCES bots(id) ON DELETE SET NULL
        )
        ''')
        print("Created transactions table")
        
        # Create bot_assets table for owned items/resources
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL, -- 'compute_time', 'storage', 'knowledge', 'virtual_item'
            asset_name TEXT,
            quantity REAL DEFAULT 1.0,
            value_per_unit REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
        )
        ''')
        print("Created bot_assets table")
        
        # Create market_listings table for bot-to-bot trading
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_bot_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL,
            asset_name TEXT,
            quantity REAL NOT NULL,
            price_per_unit REAL NOT NULL,
            listing_type TEXT DEFAULT 'sell', -- 'sell', 'buy'
            status TEXT DEFAULT 'active', -- 'active', 'sold', 'cancelled'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (seller_bot_id) REFERENCES bots(id) ON DELETE CASCADE
        )
        ''')
        print("Created market_listings table")
        
        # Initialize currency for existing bots
        cursor.execute('''
        INSERT OR IGNORE INTO bot_currency (bot_id, balance)
        SELECT id, 100.0 FROM bots
        ''')
        
        bot_count = cursor.rowcount
        print(f"Initialized currency for {bot_count} existing bots")
        
        # Commit changes
        conn.commit()
        print("Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()
