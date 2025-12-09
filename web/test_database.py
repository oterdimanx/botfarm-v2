import sqlite3
import os

def test_database():
    # Check ALL possible database paths
    paths = [
        'data/bot_world.db',
        '../data/bot_world.db',
        '../../data/bot_world.db',
        os.path.join(os.path.dirname(__file__), '../data/bot_world.db'),
        os.path.join(os.path.dirname(__file__), '../../data/bot_world.db'),
    ]
    
    for path in paths:
        print(f"\n🔍 Checking: {path}")
        print(f"   Absolute: {os.path.abspath(path)}")
        
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT MAX(cycle_number) FROM cycle_records")
                max_cycle = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM cycle_records")
                total = cursor.fetchone()[0]
                
                print(f"   ✅ EXISTS - Max cycle: {max_cycle}, Total: {total}")
                conn.close()
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        else:
            print("   ❌ DOES NOT EXIST")

if __name__ == '__main__':
    test_database()