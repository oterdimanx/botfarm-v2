import sqlite3
import random

def add_economic_traits():
    db_path = 'data/bot_world.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all bot IDs
        cursor.execute("SELECT id FROM bots WHERE is_active = 1")
        bot_ids = [row[0] for row in cursor.fetchall()]
        
        traits_added = 0
        for bot_id in bot_ids:
            # Check if generosity trait already exists
            cursor.execute("SELECT 1 FROM personality WHERE bot_id = ? AND trait_name = 'generosity'", (bot_id,))
            if not cursor.fetchone():
                # Add generosity trait (correlates with empathy/agreeableness)
                cursor.execute(
                    "INSERT INTO personality (bot_id, trait_name, value) VALUES (?, 'generosity', ?)",
                    (bot_id, random.uniform(0.2, 0.8))
                )
                traits_added += 1
            
            # Check if risk_taking trait already exists  
            cursor.execute("SELECT 1 FROM personality WHERE bot_id = ? AND trait_name = 'risk_taking'", (bot_id,))
            if not cursor.fetchone():
                # Add risk_taking trait (correlates with neuroticism)
                cursor.execute(
                    "INSERT INTO personality (bot_id, trait_name, value) VALUES (?, 'risk_taking', ?)",
                    (bot_id, random.uniform(0.1, 0.7))
                )
                traits_added += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Added {traits_added} economic traits across {len(bot_ids)} bots")
        
    except Exception as e:
        print(f"Error adding economic traits: {e}")

if __name__ == "__main__":
    add_economic_traits()