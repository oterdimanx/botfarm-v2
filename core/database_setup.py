import sqlite3
import json
import os

class BotDatabase:
    def __init__(self, db_file='data/bot_world.db'):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize the database with all required tables"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Table 1: Bots - core identity and personality
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                fullname TEXT,
                species TEXT DEFAULT 'Digital Entity',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Table 2: Personality traits
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personality (
                bot_id INTEGER,
                trait_name TEXT NOT NULL,
                value REAL NOT NULL CHECK (value >= 0 AND value <= 1),
                FOREIGN KEY (bot_id) REFERENCES bots (id),
                PRIMARY KEY (bot_id, trait_name)
            )
        ''')
        
        # Table 3: Knowledge base
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                fact TEXT NOT NULL,
                source TEXT DEFAULT 'creator',  -- 'creator', 'bot', 'system'
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 1.0,
                FOREIGN KEY (bot_id) REFERENCES bots (id)
            )
        ''')
        
        # Table 4: Memory/Conversation history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                event TEXT NOT NULL,
                event_type TEXT DEFAULT 'conversation',  -- 'conversation', 'learning', 'system'
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id)
            )
        ''')
        
        # Table 5: Needs/State
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS needs (
                bot_id INTEGER,
                need_name TEXT NOT NULL,
                value REAL NOT NULL CHECK (value >= 0 AND value <= 100),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id),
                PRIMARY KEY (bot_id, need_name)
            )
        ''')
        
        # Table 6: Skills/Abilities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                bot_id INTEGER,
                skill_name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                FOREIGN KEY (bot_id) REFERENCES bots (id),
                PRIMARY KEY (bot_id, skill_name)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully!")
    
    def migrate_existing_bots(self):
        """Migrate existing JSON bot data to the database"""
        bot_files = ['bot_samirah.json', 'bot_jean-pierre.json', 'bot_roger.json']
        
        for bot_file in bot_files:
            if os.path.exists(bot_file):
                print(f"📦 Migrating {bot_file} to database...")
                with open(bot_file, 'r') as f:
                    bot_data = json.load(f)
                
                self.add_bot_from_json(bot_data, bot_file)
    
    def add_bot_from_json(self, bot_data, original_filename):
        """Add a bot from JSON data to the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Insert basic bot info
        cursor.execute('''
            INSERT INTO bots (name, fullname, species)
            VALUES (?, ?, ?)
        ''', (bot_data['name'], bot_data.get('fullname', ''), bot_data['species']))
        
        bot_id = cursor.lastrowid
        
        # Insert personality traits
        for trait, value in bot_data['personality'].items():
            cursor.execute('''
                INSERT INTO personality (bot_id, trait_name, value)
                VALUES (?, ?, ?)
            ''', (bot_id, trait, value))
        
        # Insert knowledge
        for fact in bot_data['knowledge']:
            cursor.execute('''
                INSERT INTO knowledge (bot_id, fact, source)
                VALUES (?, ?, ?)
            ''', (bot_id, fact, 'creator'))
        
        # Insert needs
        for need, value in bot_data['needs'].items():
            cursor.execute('''
                INSERT INTO needs (bot_id, need_name, value)
                VALUES (?, ?, ?)
            ''', (bot_id, need, value))
        
        # Insert skills
        for skill, level in bot_data['skills'].items():
            cursor.execute('''
                INSERT INTO skills (bot_id, skill_name, level)
                VALUES (?, ?, ?)
            ''', (bot_id, skill, level))
        
        # Insert memories
        for memory in bot_data['memory']:
            cursor.execute('''
                INSERT INTO memory (bot_id, event, event_type)
                VALUES (?, ?, ?)
            ''', (bot_id, memory, 'conversation'))
        
        conn.commit()
        conn.close()
        
        print(f"✅ {bot_data['name']} migrated to database with ID {bot_id}")
    
    def list_bots(self):
        """List all bots in the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.name, b.fullname, COUNT(k.fact) as knowledge_count
            FROM bots b
            LEFT JOIN knowledge k ON b.id = k.bot_id
            WHERE b.is_active = 1
            GROUP BY b.id
        ''')
        
        bots = cursor.fetchall()
        conn.close()
        
        print("\n🤖 BOTS IN DATABASE:")
        for bot in bots:
            print(f"  {bot[0]}: {bot[1]} ({bot[2]}) - {bot[3]} facts")
        
        return bots

# Run the setup
if __name__ == "__main__":
    db = BotDatabase()
    db.migrate_existing_bots()
    db.list_bots()