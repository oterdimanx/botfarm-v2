# core/db_inspector.py
import sqlite3
import sys

def inspect_database(db_path):
    """Inspect the database structure to understand available tables and columns"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== DATABASE STRUCTURE ===")
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        # Get table structure
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  Column: {col[1]} (Type: {col[2]})")
        
        # Show sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"  Sample row: {sample}")
    
    conn.close()

if __name__ == "__main__":
    inspect_database("data/bot_world.db")