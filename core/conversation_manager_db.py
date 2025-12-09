import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.bot_engine_db import PrehistoricBotDB
from core.database_guardian import DatabaseGuardian
import time

class ConversationManagerDB:
    def __init__(self, db_file='data/bot_world.db'):
        self.db_file = db_file
        self.bots = self._load_all_bots()
    
    def _load_all_bots(self):
        """Load all active bots from the database"""
        import sqlite3
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name FROM bots WHERE is_active = 1')
        bot_list = cursor.fetchall()
        conn.close()
        
        bots = {}
        for bot_id, bot_name in bot_list:
            bots[bot_name.lower()] = PrehistoricBotDB(bot_id, self.db_file)
        
        print(f"✅ Loaded {len(bots)} bots from database")
        return bots
    
    def _get_bot_by_id(self,bot_id):
        """Load a bot from the database with id parameter"""
        import sqlite3
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id as bot_id, name, fullname, species, home_x, home_y, last_seen_home FROM bots WHERE id = ?', (bot_id,))
        bot_info = cursor.fetchone()
        self.bot_id, self.name, self.fullname, self.species, self.home_x, self.home_y, self.last_seen_home = bot_info
        conn.close()
        
        bots = bot_info

        
        print(f"✅ Loaded Bot {bot_id} from database")
        return bots

    def list_bots(self):
        """Show all available bots"""
        print("\n🤖 AVAILABLE BOTS:")
        for bot_name, bot in self.bots.items():
            knowledge_count = len(bot.get_knowledge())
            print(f"  {bot_name.title()} (ID: {bot.bot_id}) - {knowledge_count} facts")
    
    def start_group_conversation(self, rounds=3):
        """Start a conversation between all bots"""
        if len(self.bots) < 2:
            print("Need at least 2 bots for a group conversation!")
            return
        
        print("=== GROUP CONVERSATION STARTING ===")
        bot_names = list(self.bots.keys())
        
        # Start with a random bot
        import random
        starter_bot_name = random.choice(bot_names)
        starter_bot = self.bots[starter_bot_name]
        initial_message = "Hello everyone! How are you all doing today?"
        
        print(f"{starter_bot.name}: {initial_message}")
        
        last_message = initial_message
        last_speaker = starter_bot_name
        
        for round_num in range(rounds):
            print(f"\n--- Round {round_num + 1} ---")
            
            for bot_name in bot_names:
                if bot_name != last_speaker:
                    bot = self.bots[bot_name]
                    
                    print(f"[{bot.name} is thinking...]")
                    time.sleep(1)
                    
                    response = bot.process_input(last_message, speaker=last_speaker.title())
                    print(f"{bot.name}: {response}")
                    
                    last_message = response
                    last_speaker = bot_name
            
            print("-" * 40)
    
    def direct_message(self, from_bot_name, to_bot_name, message):
        """Send a direct message from one bot to another"""
        if from_bot_name not in self.bots or to_bot_name not in self.bots:
            print("Error: One or both bots not found!")
            return
        
        from_bot = self.bots[from_bot_name]
        to_bot = self.bots[to_bot_name]
        
        print(f"\n=== DIRECT MESSAGE ===")
        print(f"{from_bot.name} → {to_bot.name}: {message}")
        
        response = to_bot.process_input(message, speaker=from_bot.name)
        print(f"{to_bot.name} → {from_bot.name}: {response}")
        
        return response
    
    def private_chat(self, bot_name):
        """Start a private conversation with one specific bot"""
        if bot_name not in self.bots:
            print(f"Error: Bot '{bot_name}' not found!")
            return
        
        bot = self.bots[bot_name]
        print(f"\n🤖 PRIVATE CHAT WITH {bot.name.upper()} 🤖")
        print(f"Type 'quit' to end the conversation")
        print(f"Type 'status' to see {bot.name}'s current state")
        print(f"CREATOR COMMANDS:")
        print(f"  - 'remember that [fact]' - Teach me something new")
        print(f"  - 'forget that [fact]' - Make me forget something") 
        print(f"  - 'what do you know' - List all my knowledge")
        print("-" * 50)
        
        self._show_bot_status(bot)
        print("-" * 50)
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"{bot.name}: Goodbye!")
                break
            elif user_input.lower() == 'status':
                self._show_bot_status(bot)
                continue
            elif not user_input:
                continue
                
            response = bot.process_input(user_input)
            print(f"{bot.name}: {response}")
    
    def _show_bot_status(self, bot):
        """Show a bot's current status"""
        knowledge = bot.get_knowledge()
        print(f"\n{bot.name} Status:")
        print(f"Full Name: {bot.fullname}")
        print(f"Species: {bot.species}")
        print(f"Database ID: {bot.bot_id}")
        print("Current Needs:")
        for need, value in bot.needs.items():
            print(f"  - {need}: {value}/100")
        print(f"Knowledge: {len(knowledge)} facts")
        #print("Personality Highlights:")
        #high_traits = sorted(bot.personality.items(), key=lambda x: x[1], reverse=True)[:3]
        #for trait, value in high_traits:
        #    print(f"  - {trait}: {value:.2f}")

    def bot_statistics(self):
        """Show statistics about all bots"""
        import sqlite3
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        print("\n📊 BOT STATISTICS:")
        
        # Total knowledge
        cursor.execute('''
            SELECT b.name, COUNT(k.id) as fact_count 
            FROM bots b 
            LEFT JOIN knowledge k ON b.id = k.bot_id 
            GROUP BY b.id
        ''')
        print("Knowledge Distribution:")
        for bot_name, fact_count in cursor.fetchall():
            print(f"  {bot_name}: {fact_count} facts")
        
        # Memory usage
        cursor.execute('''
            SELECT b.name, COUNT(m.id) as memory_count 
            FROM bots b 
            LEFT JOIN memory m ON b.id = m.bot_id 
            GROUP BY b.id
        ''')
        print("\nMemory Usage:")
        for bot_name, memory_count in cursor.fetchall():
            print(f"  {bot_name}: {memory_count} memories")
        
        conn.close()

    def check_guardian_alerts(self):
        """Check if Micmac has any alerts to share"""
        guardian = DatabaseGuardian()
        report = guardian.generate_guardian_report()
        
        if report['overall_status'] in ['WARNING', 'CRITICAL']:
            message = guardian.get_guardian_message(report)
            print(f"\n🛡️ **MICMAC INTERRUPTION** 🛡️")
            print(message)
            
            # Log this in Micmac's memory
            micmac = self.bots.get('micmac')
            if micmac:
                micmac._add_to_memory(f"Issued database alert: {report['overall_status']}", 'system')
        
        return report

    def _load_personality_traits(self, cursor, bot_id):
        """Load personality traits for a specific bot - FIXED VERSION"""
        traits = {}
        
        try:
            cursor.execute('SELECT trait_name, value FROM personality WHERE bot_id = ?', (bot_id,))
            personality_data = cursor.fetchall()
            
            for trait_name, value in personality_data:
                traits[trait_name] = value

        except Exception as e:
            print(f"Error loading personality for bot {bot_id}: {e}")
            # Return empty dict instead of defaults to avoid confusion
            traits = {}
        
        return traits

    def check_economy(self):
        """Check the current economic status"""
        print("\n💰 ECONOMIC STATUS:")
        total_balance = 0
        for bot_name, bot in self.bots.items():
            if hasattr(bot, 'get_financial_status'):
                financial_status = bot.get_financial_status()
                balance = financial_status.get('balance', 0)
                total_balance += balance
                print(f"  {bot_name}: {balance:.1f} credits")
        
        print(f"  Total economy: {total_balance:.1f} credits")
        print(f"  Average balance: {total_balance / len(self.bots):.1f} credits")

# Main menu
if __name__ == "__main__":
    cm = ConversationManagerDB()
    pb = PrehistoricBotDB(1, db_file='data/bot_world.db')
    
    print("🗄️  DATABASE-POWERED BOT CONVERSATION MANAGER 🗄️")
    print("=" * 50)
    
    while True:
        cm.list_bots()
        print("\nAvailable commands:")
        print("1 - Private chat with a bot")
        print("2 - Start group conversation") 
        print("3 - Send direct message (bot to bot)")
        print("4 - Show bot statistics")
        print("5 - Check Economy statistics")
        print("6 - Start New Model Conversation")
        print("7 - Exit")
        
        choice = input("\nChoose an option (1-5): ").strip()
        
        if choice == "1":
            bot_choice = input("Which bot would you like to chat with? ").strip().lower()
            cm.private_chat(bot_choice)

        elif choice == "2":
            rounds = input("How many conversation rounds? (default 3): ").strip()
            rounds = int(rounds) if rounds.isdigit() else 3
            cm.start_group_conversation(rounds)

        elif choice == "3":
            print("Available bots:", list(cm.bots.keys()))
            from_bot = input("From which bot? ").strip().lower()
            to_bot = input("To which bot? ").strip().lower()
            message = input("Message: ").strip()
            cm.direct_message(from_bot, to_bot, message)
 
        elif choice == "4":
            cm.bot_statistics()

        elif choice == "5":
            cm.check_economy()

        elif choice == "6":
            print({pb.language.generate_sentence(1)})
            break

        elif choice == "7":
            print("Goodbye! Database changes have been saved.")
            break
        else:
            print("Invalid choice!")