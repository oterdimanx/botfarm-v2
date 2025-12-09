import sqlite3
import json

def analyze_database():
    db_path = 'data/bot_world.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 DATABASE STRUCTURE ANALYSIS")
    print("=" * 60)
    
    # 1. List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📊 TABLE: {table_name}")
        
        # 2. Show table structure
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        # 3. Show row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   Rows: {count}")
        
        # 4. For cycle tables, show min/max
        if 'cycle' in table_name.lower():
            cursor.execute(f"SELECT MIN(cycle_number), MAX(cycle_number) FROM {table_name}")
            min_max = cursor.fetchone()
            print(f"   Cycle range: {min_max[0]} to {min_max[1]}")
            
            # Show duplicates
            cursor.execute(f'''
                SELECT cycle_number, COUNT(*) as duplicates 
                FROM {table_name} 
                GROUP BY cycle_number 
                HAVING COUNT(*) > 1
                ORDER BY duplicates DESC
                LIMIT 5
            ''')
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"   DUPLICATES FOUND:")
                for cycle, dup_count in duplicates:
                    print(f"      Cycle {cycle}: {dup_count} copies")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Analysis complete")

if __name__ == '__main__':
    analyze_database()