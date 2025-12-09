import sqlite3

def clean_duplicate_cycles():
    db_path = 'data/bot_world.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🧹 Cleaning duplicate cycles...")
    
    # 1. Keep only the FIRST record of each cycle
    cursor.execute('''
        DELETE FROM cycle_records 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM cycle_records 
            GROUP BY cycle_number
        )
    ''')
    
    deleted_cycles = cursor.rowcount
    print(f"✅ Deleted {deleted_cycles} duplicate cycle records")
    
    # 2. Keep only the FIRST bot stats of each (cycle, bot) pair
    cursor.execute('''
        DELETE FROM cycle_bot_stats 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM cycle_bot_stats 
            GROUP BY cycle_number, bot_id
        )
    ''')
    
    deleted_stats = cursor.rowcount
    print(f"✅ Deleted {deleted_stats} duplicate bot stats")
    
    conn.commit()
    
    # 3. Verify cleanup
    cursor.execute("SELECT COUNT(*) FROM cycle_records")
    remaining = cursor.fetchone()[0]
    print(f"📊 Remaining unique cycles: {remaining}")
    
    cursor.execute("SELECT MAX(cycle_number) FROM cycle_records")
    max_cycle = cursor.fetchone()[0]
    print(f"📊 Max cycle number: {max_cycle}")
    
    conn.close()

if __name__ == '__main__':
    clean_duplicate_cycles()