import sqlite3
import random
from datetime import datetime
from core.currency import CurrencySystem
from core.language_system import LanguageSystem

class PrehistoricBotDB:
    def __init__(self, bot_id, db_file='data/bot_world.db'):
        self.bot_id = bot_id
        self.db_file = db_file
        self.load_bot_data()
        self.currency = CurrencySystem(db_file)
        self.language = LanguageSystem(db_file)
    
    def load_bot_data(self):
        """Load bot data from database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Load basic info
        cursor.execute('SELECT name, fullname, species, home_x, home_y, last_seen_home FROM bots WHERE id = ?', (self.bot_id,))
        bot_info = cursor.fetchone()
        self.name, self.fullname, self.species, self.home_x, self.home_y, self.last_seen_home = bot_info
        
        # Load personality
        cursor.execute('SELECT trait_name, value FROM personality WHERE bot_id = ?', (self.bot_id,))
        self.personality = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Load needs
        cursor.execute('SELECT need_name, value FROM needs WHERE bot_id = ?', (self.bot_id,))
        self.needs = {row[0]: row[1] for row in cursor.fetchall()}

        # Load energy
        cursor.execute('SELECT value FROM needs WHERE need_name = "energy" AND bot_id = ?', (self.bot_id,))
        self.energy = {row[0] for row in cursor.fetchall()}
        
        conn.close()
    
    def get_knowledge(self):
        """Get all knowledge facts for this bot"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT fact FROM knowledge WHERE bot_id = ?', (self.bot_id,))
        facts = [row[0] for row in cursor.fetchall()]
        conn.close()
        return facts
    
    def get_personality_modifier(self, trait):
        """Get a random modifier based on personality trait"""
        if trait in self.personality:
            return random.uniform(-self.personality[trait], self.personality[trait])
        return 0
    
    def _add_to_memory(self, event, event_type='conversation'):
        """Add an event to the bot's memory"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO memory (bot_id, event, event_type)
            VALUES (?, ?, ?)
        ''', (self.bot_id, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {event}", event_type))
        conn.commit()
        conn.close()
    
    def _update_needs(self):
        """Update needs in the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        for need, value in self.needs.items():
            cursor.execute('''
                UPDATE needs SET value = ?, last_updated = CURRENT_TIMESTAMP
                WHERE bot_id = ? AND need_name = ?
            ''', (value, self.bot_id, need))
        conn.commit()
        conn.close()
    
    def _update_need(self, need_name, new_value):
        """Update a single need"""
        self.needs[need_name] = max(0, min(100, new_value))  # Clamp between 0-100
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE needs SET value = ?, last_updated = CURRENT_TIMESTAMP
            WHERE bot_id = ? AND need_name = ?
        ''', (self.needs[need_name], self.bot_id, need_name))
        conn.commit()
        conn.close()
    
    def _update_needs_after_interaction(self):
        """Update needs after an interaction - CONSUME energy, GAIN social"""
        # Social interaction increases social need
        self._update_need('social', min(100, self.needs.get('social', 50) + 5))
        
        # Any activity consumes energy
        self._update_need('energy', max(0, self.needs.get('energy', 50) - 3))
        
        # Learning/curiosity might increase curiosity need
        self._update_need('curiosity', min(100, self.needs.get('curiosity', 50) + 2))

    def add_knowledge(self, fact, source='creator'):
        """Add new knowledge to the bot"""
        # Check if fact already exists
        existing_knowledge = self.get_knowledge()
        if fact in existing_knowledge:
            return False  # Already known
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO knowledge (bot_id, fact, source)
            VALUES (?, ?, ?)
        ''', (self.bot_id, fact, source))
        conn.commit()
        conn.close()
        
        self._add_to_memory(f"Learned new fact from {source}: {fact}", 'learning')
        return True
    
    def remove_knowledge(self, fact):
        """Remove knowledge from the bot"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM knowledge 
            WHERE bot_id = ? AND fact = ?
        ''', (self.bot_id, fact))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            self._add_to_memory(f"Forgot fact: {fact}", 'learning')
        
        return deleted
    
    def process_input(self, input_text, speaker="Human"):
        response = ""
        input_text_lower = input_text.lower()
        original_input = input_text
        
        # Store who's speaking
        self._add_to_memory(f"{speaker} said: '{original_input}'")
        
        # Update needs after any interaction
        self._update_need('social', self.needs['social'] + 5)
        self._update_need('energy', self.needs['energy'] - 2)
        
        # SPECIAL CREATOR COMMANDS
        if speaker == "Human":
            if input_text_lower.startswith(("remember that ", "learn that ")):
                if input_text_lower.startswith("remember that "):
                    new_fact = original_input[14:].strip()
                else:
                    new_fact = original_input[11:].strip()
                
                if new_fact:
                    if self.add_knowledge(new_fact):
                        response = f"Thank you! I've learned: \"{new_fact}\""
                    else:
                        response = "I already know that!"
                else:
                    response = "Please tell me what to remember."
                # 🆕 UPDATE NEEDS AFTER RESPONSE
                self._update_needs_after_interaction()
                return response
            
            elif input_text_lower.startswith("forget that "):
                fact_to_forget = original_input[12:].strip()
                if self.remove_knowledge(fact_to_forget):
                    response = f"I've forgotten: \"{fact_to_forget}\""
                else:
                    response = "I couldn't find that fact in my knowledge."
                # 🆕 UPDATE NEEDS AFTER RESPONSE
                self._update_needs_after_interaction()
                return response
            
            elif input_text_lower in ["what do you know", "show your knowledge", "list knowledge"]:
                knowledge = self.get_knowledge()
                if knowledge:
                    knowledge_list = "\n".join([f"- {fact}" for fact in knowledge])
                    response = f"I know {len(knowledge)} things:\n{knowledge_list}"
                else:
                    response = "My knowledge base is empty. Please teach me something!"
                # 🆕 UPDATE NEEDS AFTER RESPONSE
                self._update_needs_after_interaction()
                return response
        
        # 🛡️ **MICMAC GUARDIAN FEATURES** - Only for Micmac
        if self.name.lower() == "micmac":
            database_keywords = [
                'database status', 'database report', 'how is the database',
                'system status', 'health report', 'guardian report',
                'any issues', 'problems', 'alerts', 'monitoring',
                'status report', 'how are systems'
            ]
            
            # Check if this is a database-related question for Micmac
            is_database_query = any(keyword in input_text_lower for keyword in database_keywords)
            
            if is_database_query:
                # Import and use the DatabaseGuardian
                from database_guardian import DatabaseGuardian
                guardian = DatabaseGuardian()
                report = guardian.generate_guardian_report()
                
                # Convert technical report to roleplayed response
                if report['overall_status'] == 'CRITICAL':
                    urgency = "🚨 **CRITICAL ALERT** 🚨"
                    tone = "I must report critical issues that require immediate attention!"
                elif report['overall_status'] == 'WARNING':
                    urgency = "⚠️ **WARNING** ⚠️"
                    tone = "I'm detecting some concerning patterns that need monitoring."
                else:
                    urgency = "✅ **SYSTEM NOMINAL** ✅"
                    tone = "All systems are operating within normal parameters."
                
                db_size = report['details']['database_size']
                memory_usage = report['details']['memory_usage']
                
                response = f"{urgency}\n"
                response += f"{tone}\n\n"
                response += f"**Database Status Report**\n"
                response += f"• 📊 Database Size: {db_size['size_mb']}MB\n"
                response += f"• 🧠 Total Memories: {memory_usage['total_memories']}\n"
                response += f"• 🤖 Active Bots: {len(report['details']['bot_stats'])}\n"
                response += f"• ⏰ Last Check: {report['timestamp']}\n"
                
                if report['alerts']:
                    response += f"\n**Alerts:**\n"
                    for alert in report['alerts']:
                        response += f"• {alert}\n"
                
                self._add_to_memory(f"Generated database status report")
                # 🆕 UPDATE NEEDS AFTER RESPONSE
                self._update_needs_after_interaction()
                return response
        
        # REGULAR CONVERSATION LOGIC (only reached if no guardian response)
        knowledge = self.get_knowledge()
        
        if "hello" in input_text_lower or "hi" in input_text_lower:
            if self.name.lower() == "micmac":
                response = f"Greetings {speaker}. I am {self.name}, Database Guardian. How may I assist?"
            else:
                mood_modifier = self.get_personality_modifier('neuroticism')
                if mood_modifier > 0.3:
                    response = "Oh... hello. What do you want?"
                else:
                    response = f"Hello {speaker}! It's good to hear from you."
        
        elif "purpose" in input_text_lower or "role" in input_text_lower:
            if self.name.lower() == "micmac":
                response = "I am the Database Guardian. My duty is to monitor system integrity, protect all digital entities, and alert when issues arise."
            else:
                response = f"My name is {self.fullname or self.name}. I am a {self.species}."
        
        # REGULAR CONVERSATION LOGIC
        knowledge = self.get_knowledge()  # Get fresh knowledge from DB
        
        if "hello" in input_text_lower or "hi" in input_text_lower:
            mood_modifier = self.get_personality_modifier('neuroticism')
            if mood_modifier > 0.3:
                response = "Oh... hello. What do you want?"
            else:
                response = f"Hello {speaker}! It's good to hear from you."
        
        elif "how are you" in input_text_lower:
            avg_need = sum(self.needs.values()) / len(self.needs)
            if avg_need > 70:
                response = "I'm functioning within optimal parameters."
            else:
                response = "My systems are feeling a bit depleted..."
        
        elif "what is" in input_text_lower:
            topic = input_text_lower.replace("what is", "").strip()
            response = f"I don't know anything about {topic}."
            for fact in knowledge:
                if topic in fact.lower():
                    response = fact
                    break
        
        elif "introduce yourself" in input_text_lower:
            response = f"My name is {self.fullname or self.name}. I am a {self.species}."
        
        else:
            default_responses = ["I see.", "Can you elaborate?", "My databases are unclear on that."]
            response = random.choice(default_responses)
        
        self._add_to_memory(f"I replied: '{response}'")
        # 🆕 UPDATE NEEDS AFTER RESPONSE
        self._update_needs_after_interaction()
        return response

    def bots_interact(self, bot1_id, bot2_id, location):
        """Two bots have an interaction/conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversation record
        cursor.execute('''
            INSERT INTO conversations (bot1_id, bot2_id, location_x, location_y)
            VALUES (?, ?, ?, ?)
        ''', (bot1_id, bot2_id, location[0], location[1]))
        conversation_id = cursor.lastrowid
        
        # Generate conversation
        messages = []
        
        # Bot1 speaks first
        context = {'interaction_type': 'greeting', 'other_bot_id': bot2_id}
        message1 = self.language.generate_sentence(bot1_id, context)
        
        cursor.execute('''
            INSERT INTO conversation_messages (conversation_id, bot_id, message)
            VALUES (?, ?, ?)
        ''', (conversation_id, bot1_id, message1))
        messages.append(message1)
        
        # Bot2 responds
        context['responding_to'] = message1
        message2 = self.language.generate_sentence(bot2_id, context)
        
        cursor.execute('''
            INSERT INTO conversation_messages (conversation_id, bot_id, message)
            VALUES (?, ?, ?)
        ''', (conversation_id, bot2_id, message2))
        messages.append(message2)
        
        # Possible third exchange (50% chance)
        if random.random() > 0.5:
            context['final_exchange'] = True
            message3 = self.language.generate_sentence(bot1_id, context)
            
            cursor.execute('''
                INSERT INTO conversation_messages (conversation_id, bot_id, message)
                VALUES (?, ?, ?)
            ''', (conversation_id, bot1_id, message3))
            messages.append(message3)
        
        conn.commit()
        conn.close()
        
        return messages

# Simple test
if __name__ == "__main__":
    print("Testing Database-Powered Bot...")
    bot = PrehistoricBotDB(1)  # Test with Samirah
    print(f"Loaded: {bot.name} ({bot.fullname})")
    print(f"Personality: {bot.personality}")
    print(f"Needs: {bot.needs}")
    print(f"Knowledge: {len(bot.get_knowledge())} facts")
    print(f"Initial energy: {bot.needs.get('energy', 'N/A')}")
    
    # Test conversation
    response = bot.process_input("Hello")
    print(f"\nSamirah: {response}")
    print(f"Energy after interaction: {bot.needs.get('energy', 'N/A')}")