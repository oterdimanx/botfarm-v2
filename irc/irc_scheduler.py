# irc/irc_scheduler.py - Schedule IRC visits for other bots
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import random
import threading
from datetime import datetime, timedelta
from config import irc_conf

class IRCScheduler:
    def __init__(self, conversation_manager):
        self.cm = conversation_manager
        self.running = False
        self.scheduler_thread = None
        
        # Visit schedules for each bot (excluding Samirah - she's permanent)
        self.bot_schedules = {}
        
    def should_visit_irc(self, bot):
        """Decide if a bot should visit IRC based on personality and needs"""
        if bot.name.lower() == "samirah":
            return False  # She's permanent
            
        # Base decision on curiosity and energy
        curiosity = bot.needs.get('curiosity', 0)
        energy = bot.needs.get('energy', 0)
        
        # More curious bots visit more often
        if curiosity > 80 and energy > 40:
            return random.random() < 0.3  # 30% chance
        elif curiosity > 60 and energy > 50:
            return random.random() < 0.15  # 15% chance
        elif curiosity > 40:
            return random.random() < 0.05  # 5% chance
            
        return False
    
    def get_visit_duration(self, bot):
        """Determine how long a bot should stay based on personality"""
        base_duration = 5  # minutes
        
        # Adjust based on personality
        if bot.personality.get('extraversion', 0.5) > 0.7:
            base_duration += random.randint(2, 5)  # Extraverts stay longer
        if bot.personality.get('curiosity', 0.5) > 0.8:
            base_duration += random.randint(3, 8)  # Very curious stay longer
            
        return max(3, min(15, base_duration))  # 3-15 minute range
    
    def get_visit_purpose(self, bot):
        """Generate a visit purpose based on bot's personality"""
        purposes = {
            'samirah': ["exploring new ideas", "meeting new people", "creative inspiration"],
            'jean-pierre': ["data collection", "pattern analysis", "logical discussion"],
            'micmac': ["system monitoring", "security assessment", "protocol observation"],
            'roger': ["practical learning", "problem solving", "skill development"]
        }
        
        bot_purposes = purposes.get(bot.name.lower(), ["learning", "observing", "exploring"])
        return random.choice(bot_purposes)
    
    def start_scheduled_visits(self):
        """Start the scheduler to periodically check for IRC visits"""
        self.running = True
        print("🕒 Starting IRC visit scheduler...")
        
        while self.running:
            try:
                # Check every 10 minutes
                for _ in range(600):  # 10 minutes in seconds
                    if not self.running:
                        break
                    time.sleep(1)
                
                if not self.running:
                    break
                    
                # Check each bot (except Samirah)
                for bot_name, bot in self.cm.bots.items():
                    if bot_name.lower() != 'samirah' and self.should_visit_irc(bot):
                        duration = self.get_visit_duration(bot)
                        purpose = self.get_visit_purpose(bot)
                        
                        print(f"🎫 Scheduling {bot_name} for IRC visit ({duration}min) - {purpose}")
                        
                        # Start visit in background
                        visit_thread = threading.Thread(
                            target=self._start_bot_visit,
                            args=(bot, duration, purpose),
                            daemon=True
                        )
                        visit_thread.start()
                        
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
    
    def _start_bot_visit(self, bot, duration, purpose):
        """Start an IRC visit for a bot"""
        try:
            from irc.irc_client_with_memory import IRCClientWithMemory
            
            # Use a working server
            working_server = irc_conf.IRC['servers']['efnet'][3]
            
            client = IRCClientWithMemory(
                bot_id=bot.bot_id,
                server=working_server,
                nickname=bot.name.lower(),
                channel=irc_conf.IRC['connect']['channel']
            )
            
            if client.connect():
                print(f"🌐 {bot.name} starting IRC visit: {purpose}")
                
                # Send purpose message
                client.send_message(f"Hello! {bot.name} here for {purpose}. Staying for {duration} minutes.")
                
                # Record the scheduled visit
                client._add_irc_memory("scheduled_visit", f"Visiting for {purpose} for {duration} minutes")
                
                # Stay for duration
                client.stay_connected(minutes=duration)
                
                print(f"✅ {bot.name}'s IRC visit completed")
            else:
                print(f"❌ {bot.name} failed to connect to IRC")
                
        except Exception as e:
            print(f"❌ IRC visit failed for {bot.name}: {e}")
    
    def start_in_background(self):
        """Start the scheduler in background"""
        self.scheduler_thread = threading.Thread(
            target=self.start_scheduled_visits,
            daemon=True
        )
        self.scheduler_thread.start()
        print("✅ IRC scheduler running in background")
        return self.scheduler_thread
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        print("🛑 IRC scheduler stopped")

# Test the scheduler
def test_scheduler():
    """Test the IRC scheduler"""
    from core.conversation_manager_db import ConversationManagerDB
    
    print("🧪 Testing IRC Scheduler")
    print("=" * 40)
    
    cm = ConversationManagerDB()
    scheduler = IRCScheduler(cm)
    
    print("🤖 Checking bots for IRC visits:")
    for bot_name, bot in cm.bots.items():
        if bot_name.lower() != 'samirah':
            should_visit = scheduler.should_visit_irc(bot)
            duration = scheduler.get_visit_duration(bot)
            purpose = scheduler.get_visit_purpose(bot)
            
            status = "✅ YES" if should_visit else "❌ NO"
            print(f"  {bot_name}: {status} ({duration}min - {purpose})")
    
    print(f"\n🎯 Samirah: PERMANENT (not scheduled)")
    
    # Start scheduler for a short test
    print("\n🚀 Starting scheduler for 2 minutes...")
    scheduler.start_in_background()
    time.sleep(120)  # Run for 2 minutes
    scheduler.stop()
    print("✅ Scheduler test completed")

if __name__ == "__main__":
    test_scheduler()
