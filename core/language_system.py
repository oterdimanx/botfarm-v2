import random
import sqlite3
from datetime import datetime

class LanguageSystem:
    def __init__(self, db_path):
        self.db_path = db_path
        self.cache = {}
    
    def generate_sentence(self, bot_id, context=None):
        """
        Generate a sentence for a bot based on its knowledge and context
        context = {'interaction_type': 'greeting', 'other_bot_id': 2, 'location': (x,y)}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get bot's personality/mood
        mood = self._get_bot_mood(bot_id, cursor)
        
        # Choose sentence pattern based on context
        pattern = self._choose_pattern(context, mood, cursor)
        
        # Fill pattern with words from bot's knowledge
        sentence = self._fill_pattern(pattern, bot_id, context, mood, cursor)
        
        conn.close()
        return sentence
    
    def _get_bot_mood(self, bot_id, cursor):
        """Determine bot's current emotional state"""
        # Check bot's needs
        cursor.execute('SELECT value FROM needs WHERE need_name = "energy" AND bot_id = ?', (bot_id,))
        energy_needs = cursor.fetchone()

        cursor.execute('SELECT value FROM needs WHERE need_name = "social" AND bot_id = ?', (bot_id,))
        social_needs = cursor.fetchone()
        
        mood = 'neutral'
        if energy_needs:
            energy = energy_needs[0]
            if energy < 20:
                mood = 'negative'
            elif social_needs[0] > 80:
                mood = 'positive'
            
            # Check recent events
            #cursor.execute('''
            #    SELECT COUNT(*) FROM bot_events 
            #    WHERE bot_id = ? AND created_at > datetime('now', '-1 hour')
            #''', (bot_id,))
            #recent_events = cursor.fetchone()[0]
            
            #if recent_events > 5:
            #    mood = 'excited' if random.random() > 0.5 else 'overwhelmed'
        
        return mood
    
    def _choose_pattern(self, context, mood, cursor):
        """Select appropriate grammar pattern"""
        if context and context.get('interaction_type'):
            interaction = context['interaction_type']
            
            if interaction == 'greeting':
                patterns = ['Hello {other}!', 'Hi there!', 'Good to see you!']
                return random.choice(patterns)
            elif interaction == 'trade':
                patterns = ['I have {object} to trade.', 'Do you need {object}?', 'Let us trade {object}.']
                return random.choice(patterns)
        
        # Random pattern based on mood
        if mood == 'positive':
            cursor.execute(
                "SELECT pattern FROM grammar_patterns WHERE pattern_type = 'statement' ORDER BY RANDOM() LIMIT 1"
            )
        elif mood == 'negative':
            cursor.execute(
                "SELECT pattern FROM grammar_patterns WHERE pattern_type = 'exclamation' ORDER BY RANDOM() LIMIT 1"
            )
        else:
            cursor.execute("SELECT pattern FROM grammar_patterns ORDER BY RANDOM() LIMIT 1")
        
        result = cursor.fetchone()
        return result[0] if result else "{subject} {verb} {object}"
    
    def _fill_pattern(self, pattern, bot_id, context, mood, cursor):
        """Replace placeholders with actual words"""
        # Get bot's knowledge
        cursor.execute('''
            SELECT knowledge_type, subject, fact 
            FROM knowledge 
            WHERE bot_id = ? 
            ORDER BY confidence DESC, learned_at DESC 
            LIMIT 10
        ''', (bot_id,))
        knowledge = cursor.fetchall()
        
        # Available replacements
        replacements = {}
        
        # Subject (usually "I" or bot's name)
        cursor.execute('SELECT name FROM bots WHERE id = ?', (bot_id,))
        bot_name = cursor.fetchone()[0]
        replacements['subject'] = 'I'
        replacements['{bot_name}'] = bot_name
        
        # Other bot if in conversation
        if context and 'other_bot_id' in context:
            cursor.execute('SELECT name FROM bots WHERE id = ?', (context['other_bot_id'],))
            other_name = cursor.fetchone()[0]
            replacements['other'] = other_name
        
        # Get words from vocabulary based on knowledge
        for _, subject, fact in knowledge:
            if subject in ['food', 'item', 'location']:
                # Find related words
                cursor.execute(
                    "SELECT word FROM vocabulary WHERE subcategory = ? ORDER BY RANDOM() LIMIT 1",
                    (subject,)
                )
                result = cursor.fetchone()
                if result:
                    replacements[subject] = result[0]
        
        # Fill in missing slots with random appropriate words
        if '{verb}' in pattern and 'verb' not in replacements:
            cursor.execute(
                "SELECT word FROM vocabulary WHERE category = 'verb' AND emotional_tone = ? ORDER BY RANDOM() LIMIT 1",
                (mood,)
            )
            result = cursor.fetchone()
            replacements['verb'] = result[0] if result else 'go'
        
        if '{object}' in pattern and 'object' not in replacements:
            cursor.execute(
                "SELECT word FROM vocabulary WHERE category = 'noun' ORDER BY RANDOM() LIMIT 1"
            )
            result = cursor.fetchone()
            replacements['object'] = result[0] if result else 'food'
        
        if '{adjective}' in pattern and 'adjective' not in replacements:
            cursor.execute(
                "SELECT word FROM vocabulary WHERE category = 'adjective' AND emotional_tone = ? ORDER BY RANDOM() LIMIT 1",
                (mood,)
            )
            result = cursor.fetchone()
            replacements['adjective'] = result[0] if result else 'good'
        
        # Apply replacements
        sentence = pattern
        for placeholder, fact in replacements.items():
            sentence = sentence.replace(f'{{{placeholder}}}', fact)
        
        # Capitalize first letter
        return sentence[0].upper() + sentence[1:] if sentence else "Hello."
    
    def learn_from_interaction(self, bot_id, interaction_type, details):
        """Bot learns new words/knowledge from interactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if interaction_type == 'found_item':
            item = details.get('item')
            cursor.execute(
                "INSERT INTO bot_knowledge (bot_id, knowledge_type, subject, fact) VALUES (?, ?, ?, ?)",
                (bot_id, 'has', 'item', item)
            )
            
            # Also learn the word if not in vocabulary
            cursor.execute("SELECT id FROM vocabulary WHERE word = ?", (item,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO vocabulary (word, category, subcategory) VALUES (?, ?, ?)",
                    (item, 'noun', 'item')
                )
        
        elif interaction_type == 'visited_location':
            location_type = details.get('location_type')
            cursor.execute(
                "INSERT INTO bot_knowledge (bot_id, knowledge_type, subject, fact) VALUES (?, ?, ?, ?)",
                (bot_id, 'seen', 'location', location_type)
            )
        
        conn.commit()
        conn.close()
