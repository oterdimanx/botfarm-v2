import sqlite3

def debug_cycle_data():
    conn = sqlite3.connect('data/bot_world.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔍 DEBUGGING CYCLE DATA STORAGE")
    print("=" * 50)
    
    # Check cycle_records table
    cursor.execute("SELECT COUNT(*) as count FROM cycle_records")
    cycle_count = cursor.fetchone()['count']
    print(f"📊 cycle_records: {cycle_count} total cycles")
    
    if cycle_count > 0:
        cursor.execute('SELECT * FROM cycle_records ORDER BY cycle_number DESC LIMIT 3')
        recent_cycles = cursor.fetchall()
        print(f"\n🔄 Most recent {len(recent_cycles)} cycles:")
        for cycle in recent_cycles:
            print(f"  Cycle {cycle['cycle_number']}:")
            print(f"    Currency: {cycle['total_currency']}")
            print(f"    Transactions: {cycle['total_transactions']}")
            print(f"    Timestamp: {cycle['timestamp']}")
    
    # Check cycle_bot_stats table  
    cursor.execute("SELECT COUNT(*) as count FROM cycle_bot_stats")
    bot_stat_count = cursor.fetchone()['count']
    print(f"\n🤖 cycle_bot_stats: {bot_stat_count} total bot records")
    
    if bot_stat_count > 0:
        cursor.execute('''
            SELECT cycle_number, COUNT(*) as bot_count 
            FROM cycle_bot_stats 
            GROUP BY cycle_number 
            ORDER BY cycle_number DESC 
            LIMIT 3
        ''')
        recent_bot_stats = cursor.fetchall()
        print(f"\n📈 Recent cycles with bot data:")
        for stat in recent_bot_stats:
            print(f"  Cycle {stat['cycle_number']}: {stat['bot_count']} bots recorded")
        
        # Show sample bot data from latest cycle
        cursor.execute('''
            SELECT MAX(cycle_number) as latest_cycle FROM cycle_bot_stats
        ''')
        latest_cycle = cursor.fetchone()['latest_cycle']
        
        if latest_cycle:
            cursor.execute('''
                SELECT bot_name, energy, social, curiosity, balance 
                FROM cycle_bot_stats 
                WHERE cycle_number = ?
            ''', (latest_cycle,))
            bot_data = cursor.fetchall()
            print(f"\n🎯 Bot data from latest cycle ({latest_cycle}):")
            for bot in bot_data:
                print(f"  {bot['bot_name']}:")
                print(f"    Energy: {bot['energy']}")
                print(f"    Social: {bot['social']}") 
                print(f"    Curiosity: {bot['curiosity']}")
                print(f"    Balance: {bot['balance']}")
    
    # If no data in cycle_bot_stats, check if table exists
    if bot_stat_count == 0:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cycle_bot_stats'")
        table_exists = cursor.fetchone()
        print(f"\n❓ cycle_bot_stats table exists: {bool(table_exists)}")
        
        if table_exists:
            cursor.execute("PRAGMA table_info(cycle_bot_stats)")
            columns = cursor.fetchall()
            print("   Table columns:")
            for col in columns:
                print(f"     {col[1]} ({col[2]})")
    
    conn.close()
    print("\n" + "=" * 50)

if __name__ == '__main__':
    debug_cycle_data()