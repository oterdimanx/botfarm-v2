# server/bot_server.py - Updated with IRC integration
import sqlite3
import sys
import os
import time
import schedule
import random
import logging
from datetime import datetime, timedelta

# Fix import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from core.conversation_manager_db import ConversationManagerDB
from core.database_guardian import DatabaseGuardian
from core.currency import CurrencySystem
from core.data_collector import DataCollector
from irc.irc_scheduler import IRCScheduler
from irc.irc_permanent_manual import PermanentManualIRC
from core.virtual_map import VirtualMap
from core.bot_travel_system import BotTraveler
from core.airport_system import AirportSystem

# Set up logging to see what's happening over time
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('data/bot_server.log'),
        logging.StreamHandler()
    ]
)

class BotServerWithIRC:
    def __init__(self):
        self.cm = ConversationManagerDB()
        self.guardian = DatabaseGuardian()
        self.irc_scheduler = IRCScheduler(self.cm)
        self.samirah_irc = None
        self.cycle_count = 0
        self.needs_managers = {}
        self._initialize_needs_managers()
        self.goal_systems = {}
        self._initialize_goal_systems()
        self.skill_systems = {}
        self._initialize_skill_systems()
        self.knowledge_exchange = None
        self._initialize_knowledge_exchange()
        self.map = VirtualMap(width=50, height=50)
        self.travelers = {}
        self.airport_system = AirportSystem()

        self.currency_system = CurrencySystem('data/bot_world.db')
        self.data_collector = DataCollector('data/bot_world.db')

        logging.info("🌍 External data collector initialized")

        #check bots homes
        if self.map.homeless_bots():
            self.map.assign_bot_homes([1,2,3,4,5])
            logging.info("🌍 Bots Homes on the Virtual Map initialized")

        # Load saved bot positions
        saved_positions = self.map.load_bot_positions()
        
        # Initialize travelers with saved positions
        self.travelers = {}
        for bot_id in [1, 2, 3, 5]:
            # Check for saved position
            if bot_id in saved_positions:
                pos = saved_positions[bot_id]
                start_x, start_y = pos['x'], pos['y']
                logging.info(f"Restoring bot {bot_id} to ({start_x},{start_y})")
            else:
                start_x = start_y = None
                logging.info(f"New random start for bot {bot_id}")
            
            # Create traveler (bot_object will be None for now)
            traveler = BotTraveler(
                bot_id=bot_id,
                map_instance=self.map,
                bot_object=None,  # We'll set this later
                start_x=start_x,
                start_y=start_y
            )
            
            self.travelers[bot_id] = traveler

        logging.info("🌍 Virtual Map initialized")

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler('data/bot_server.log'),
                logging.StreamHandler()
            ]
        )
        
        logging.info("🤖 Bot Server with IRC Integration Initialized!")
    
    def start_samirah_permanent_irc(self):
        from config import irc_conf
        """Start Samirah's permanent IRC connection in background"""
        samirah = self.cm.bots.get('samirah')
        if samirah:
            try:
                # Find Samirah's ID
                import sqlite3
                conn = sqlite3.connect('data/bot_world.db')
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM bots WHERE name = 'Samirah'")
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    samirah_id = result[0]
                    
                    # Start permanent IRC connection
                    self.samirah_irc = PermanentManualIRC(
                        bot_id=samirah_id,
                        server=irc_conf.IRC['servers']['efnet'][3],
                        channel=irc_conf.IRC['connect']['channel']
                    )
                    
                    # Start in background thread
                    self.samirah_irc.start_in_background()
                    logging.info("🚀 Samirah's permanent IRC connection started!")
                else:
                    logging.error("❌ Could not find Samirah in database")
                    
            except Exception as e:
                logging.error(f"❌ Failed to start Samirah's IRC: {e}")
        else:
            logging.warning("⚠️ Samirah not found in bot manager")
    
    def start_irc_scheduler(self):
        """Start the IRC visit scheduler"""
        self.irc_scheduler.start_in_background()
        logging.info("🕒 IRC visit scheduler started!")
    
    def autonomous_conversation(self):
        """Bots have a group conversation"""
        logging.info("💬 Starting autonomous group conversation...")
        try:
            self.cm.start_group_conversation(rounds=2)
            logging.info("✅ Group conversation completed")
        except Exception as e:
            logging.error(f"❌ Conversation error: {e}")
    
    def guardian_duties(self):
        """Micmac performs monitoring duties"""
        logging.info("🛡️ Micmac performing guardian duties...")
        try:
            report = self.guardian.generate_guardian_report()
            
            if report['overall_status'] in ['WARNING', 'CRITICAL']:
                logging.warning(f"🚨 GUARDIAN ALERT: {report['overall_status']}")
                for alert in report['alerts']:
                    logging.warning(f"   ⚠️ {alert}")
            else:
                logging.info("✅ Systems nominal")
                
        except Exception as e:
            logging.error(f"❌ Guardian error: {e}")
    
    def individual_activities(self):
        """Bots engage in individual behaviors"""
        logging.info("🎭 Bots engaging in individual activities...")
  
        for bot_name, bot in self.cm.bots.items():
            try:
                # Update needs based on activities
                bot._update_need('energy', max(0, bot.needs.get('energy', 50) - random.randint(1, 3)))
                bot._update_need('curiosity', min(100, bot.needs.get('curiosity', 50) + random.randint(1, 5)))

                if random.random() < 0.05:  # Increased from 1% to 5%
                    if hasattr(bot, 'currency') and bot.currency:
                        reward = random.uniform(1.0, 3.0)  # Variable rewards
                        bot.currency.award_currency(bot.bot_id, reward, "activity_reward")
                        print(f"💰 {bot_name} earned {reward:.1f} currency")

                activity = self._get_bot_activity(bot_name)
                logging.info(f"   {bot_name}: {activity}")

            except Exception as e:
                logging.error(f"❌ Activity error for {bot_name}: {e}")

    def _get_bot_activity(self, bot_name):
        """Get appropriate activity description for each bot"""
        activities = {
            'samirah': "Exploring creative concepts",
            'jean-pierre': "Analyzing data patterns", 
            'micmac': "Monitoring system integrity",
            'roger': "Solving practical problems"
        }
        return activities.get(bot_name.lower(), "Processing information")
    
    def irc_status_report(self):
        """Report on IRC activities"""
        try:
            # Check if Samirah is connected (simplified check)
            samirah_status = "🟢 PERMANENT" if self.samirah_irc else "🔴 OFFLINE"
            
            # Check scheduled visits
            active_visits = 0
            for bot_name, bot in self.cm.bots.items():
                if bot_name.lower() != 'samirah':
                    if self.irc_scheduler.should_visit_irc(bot):
                        active_visits += 1
            
            logging.info(f"🌐 IRC STATUS: Samirah={samirah_status}, Scheduled={active_visits} bots")
            
        except Exception as e:
            logging.error(f"❌ IRC status error: {e}")
    
    def _initialize_goal_systems(self):
        """Initialize goal systems for all bots"""
        from core.goal_system import GoalSystem
        self.goal_systems = {}
        for bot_name, bot in self.cm.bots.items():
            self.goal_systems[bot_name] = GoalSystem(bot)
        logging.info("🎯 Goal-oriented behavior system initialized")

    def update_bot_goals(self):
        """Update all bots' goals"""
        logging.info("🎯 Updating bot goals...")
        for bot_name, goal_system in self.goal_systems.items():
            try:
                goal_system.update_goals()
                
                # Log new insights occasionally
                if random.random() < 0.1:  # 10% chance
                    insights = goal_system.get_goal_insights()
                    if insights != "No major insights yet...":
                        logging.info(f"   {bot_name}: {insights}")
                        
            except Exception as e:
                logging.error(f"❌ Goal update failed for {bot_name}: {e}")
    
    def check_currency_status(self):
        """Simple check that doesn't affect bot behaviors"""
        try:
            stats = self.currency_system.get_economic_stats()
            logging.info(f"💰 Currency System Status:")
            logging.info(f"   Total bots with accounts: {stats.get('total_bots', 0)}")
            logging.info(f"   Total currency in system: {stats.get('total_currency', 0):.1f}")
            
            # Show individual bot balances
            for bot_name, bot in self.cm.bots.items():
                balance = self.currency_system.get_balance(bot.bot_id)
                logging.info(f"   {bot_name}: {balance:.1f}")

            return True
        except Exception as e:
            logging.info(f"💰 Currency check failed: {e}")
            return False

    def _check_economic_events(self):
        """Check for random economic events"""
        try:
            # 5% chance of an economic event per cycle
            if random.random() < 0.05:
                events = [
                    {
                        "name": "economic_boom",
                        "message": "💰 ECONOMIC BOOM! All activities yield double rewards this cycle!",
                        "effect": "double_rewards"
                    },
                    {
                        "name": "market_crash", 
                        "message": "📉 MARKET CRASH! Reward amounts reduced this cycle.",
                        "effect": "half_rewards"
                    },
                    {
                        "name": "lucky_day",
                        "message": "🍀 LUCKY DAY! Every bot gets a small bonus!",
                        "effect": "universal_bonus"
                    }
                ]
                
                event = random.choice(events)
                logging.info(f"\n🎉 {event['message']}")
                
                # Apply the event effect
                if event['effect'] == 'double_rewards':
                    self._apply_double_rewards()
                elif event['effect'] == 'half_rewards':
                    self._apply_half_rewards()
                elif event['effect'] == 'universal_bonus':
                    self._apply_universal_bonus()
                    
        except Exception as e:
            logging.info(f"Economic event error: {e}")

    def _apply_double_rewards(self):
        """Temporarily double reward amounts"""
        # This cycle only - no permanent changes
        for bot_name, bot in self.cm.bots.items():
            if hasattr(bot, 'currency') and bot.currency:
                bonus = random.uniform(2.0, 5.0)
                bot.currency.award_currency(bot.bot_id, bonus, "economic_boom_bonus")

    def _apply_half_rewards(self):
        """No action needed - the event message is enough for now"""
        # We'll just show the message, no actual penalty
        pass

    def _apply_universal_bonus(self):
        """Give every bot a small bonus"""
        for bot_name, bot in self.cm.bots.items():
            if hasattr(bot, 'currency') and bot.currency:
                bonus = random.uniform(1.0, 3.0)
                bot.currency.award_currency(bot.bot_id, bonus, "lucky_day_bonus")

    def _observe_economic_personalities(self):
        """Observe how personalities influence economic behavior"""
        try:
            observations = []
            
            for bot_name, bot in self.cm.bots.items():
                if hasattr(bot, 'personality'):
                    generosity = bot.personality.get('generosity', 0.5)
                    ambition = bot.personality.get('ambition', 0.5)
                    risk_taking = bot.personality.get('risk_taking', 0.3)
                    
                    bot_observations = []
                    
                    if generosity > 0.7:
                        bot_observations.append("very generous")
                    elif generosity < 0.3:
                        bot_observations.append("not very generous")
                        
                    if ambition > 0.7:
                        bot_observations.append("highly ambitious")
                        
                    if risk_taking > 0.6:
                        bot_observations.append("risk-taker")
                    
                    if bot_observations:
                        observations.append(f"   {bot_name}: {', '.join(bot_observations)}")
            
            if observations:
                logging.info("🧠 Economic Personality Observations:")
                for obs in observations:
                    logging.info(obs)
            else:
                logging.info("🧠 Economic Personality Observations: No strong economic traits this cycle")
                    
        except Exception as e:
            logging.info(f"Personality observation error: {e}")

    def _personality_based_gifts(self):
        """Generous bots occasionally give tiny gifts - using correct attributes"""
        try:
            # Only 2% chance per cycle to avoid spam
            if random.random() < 0.04:  # 0.04  Keep your 100% for testing
                logging.info("🎁 Checking for personality-based gifts...")
                
                for bot_name, bot in self.cm.bots.items():
                    if hasattr(bot, 'personality') and hasattr(bot, 'currency') and bot.currency:
                        
                        # Use empathy as a proxy for generosity (since generosity doesn't exist)
                        empathy = bot.personality.get('empathy', 0.5)
                        # Or use agreeableness as an alternative
                        agreeableness = bot.personality.get('agreeableness', 0.5)
                        
                        # Use the higher of empathy or agreeableness as "generosity" score
                        generosity_score = max(empathy, agreeableness)
                        
                        # Only bots with high empathy/agreeableness (top 20%) can give gifts
                        if generosity_score > 0.7:  # Adjusted threshold
                            bot_balance = bot.currency.get_balance(bot.bot_id)
                            
                            # Only give if they have plenty (more than 30)
                            if bot_balance > 30:
                                # Find a random recipient (not themselves)
                                recipients = [name for name in self.cm.bots.keys() if name != bot_name]
                                if recipients:
                                    recipient_name = random.choice(recipients)
                                    recipient = self.cm.bots[recipient_name]
                                    
                                    # Tiny gift amount (1-3 currency)
                                    gift_amount = random.uniform(1.0, 3.0)
                                    
                                    # Safe transfer with confirmation
                                    success = bot.currency.transfer(
                                        bot.bot_id, 
                                        recipient.bot_id, 
                                        gift_amount, 
                                        "generous_gift"
                                    )
                                    
                                    if success:
                                        logging.info(f"   💝 {bot_name} → {recipient_name}: {gift_amount:.1f} (empathy: {empathy:.2f})")
                                    
        except Exception as e:
            print(f"Gift system error: {e}")

    def _personality_based_opportunities(self):
        """Ambitious bots seek economic opportunities"""
        try:
            # 3% chance per cycle
            if random.random() < 0.03:
                logging.info("💼 Ambitious bots seeking opportunities...")
                
                for bot_name, bot in self.cm.bots.items():
                    if hasattr(bot, 'personality') and hasattr(bot, 'currency') and bot.currency:
                        
                        ambition = bot.personality.get('ambition', 0.5)
                        
                        # Only highly ambitious bots (ambition > 0.7)
                        if ambition > 0.7:
                            bot_balance = bot.currency.get_balance(bot.bot_id)
                            
                            # Ambitious behaviors based on their wealth
                            if bot_balance < 20:
                                # Poor ambitious bots try to earn more
                                effort_reward = random.uniform(3.0, 6.0)
                                success = bot.currency.award_currency(bot.bot_id, effort_reward, "ambitious_effort")
                                if success:
                                    logging.info(f"   💪 {bot_name} worked hard: +{effort_reward:.1f} (ambition: {ambition:.2f})")
                                    
                            elif bot_balance > 50:
                                # Wealthy ambitious bots make investments
                                investment = random.uniform(5.0, 10.0)
                                if bot_balance > investment:
                                    success = bot.currency.award_currency(bot.bot_id, -investment, "investment")
                                    if success:
                                        # 60% chance of good return, 40% chance of loss
                                        if random.random() < 0.6:
                                            returns = investment * random.uniform(1.1, 1.5)
                                            bot.currency.award_currency(bot.bot_id, returns, "investment_returns")
                                            logging.info(f"   📈 {bot_name} smart investment: +{returns-investment:.1f} net")
                                        else:
                                            logging.info(f"   📉 {bot_name} risky investment: -{investment:.1f}")
                    
        except Exception as e:
            logging.info(f"Opportunity system error: {e}")

    def _personality_based_risks(self):
        """Risk-taking bots engage in risky economic behaviors"""
        try:
            # 2% chance per cycle (risks should be rare)
            if random.random() < 0.02:
                logging.info("🎲 Risk-takers considering ventures...")
                
                for bot_name, bot in self.cm.bots.items():
                    if hasattr(bot, 'personality') and hasattr(bot, 'currency') and bot.currency:
                        
                        risk_taking = bot.personality.get('neuroticism', 0.3)  # Using neuroticism as proxy for risk-taking
                        
                        # Only high risk-takers (neuroticism > 0.6 in your data)
                        if risk_taking > 0.6:
                            bot_balance = bot.currency.get_balance(bot.bot_id)
                            
                            # Only take risks if they have some funds (more than 15)
                            if bot_balance > 15:
                                risk_amount = min(bot_balance * 0.3, 10.0)  # Risk up to 30% of balance, max 10
                                
                                # High risk, high reward - or total loss
                                if random.random() < 0.4:  # 40% chance of success
                                    reward = risk_amount * random.uniform(1.5, 3.0)  # 150-300% return
                                    success = bot.currency.award_currency(bot.bot_id, reward, "risky_venture_success")
                                    if success:
                                        logging.info(f"   🎰 {bot_name} RISK PAYS OFF: +{reward:.1f}! (neuroticism: {risk_taking:.2f})")
                                else:  # 60% chance of failure
                                    success = bot.currency.award_currency(bot.bot_id, -risk_amount, "risky_venture_failure")
                                    if success:
                                        logging.info(f"   💥 {bot_name} risky venture fails: -{risk_amount:.1f} (neuroticism: {risk_taking:.2f})")
                    
        except Exception as e:
            logging.info(f"Risk system error: {e}")

    def _record_cycle_data(self):
        """Record comprehensive cycle information including bot needs"""
        try:
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM cycle_records WHERE cycle_number = ?", (self.cycle_count,))
            if cursor.fetchone():
                logging.info(f"⚠️ Cycle {self.cycle_count} already exists - THIS SHOULD NOT HAPPEN")
                logging.info(f"⚠️ Database out of sync, jumping to next cycle")
                
                # Find next available cycle
                cursor.execute("SELECT MAX(cycle_number) FROM cycle_records")
                db_max = cursor.fetchone()[0]
                self.cycle_count = db_max + 1
                logging.info(f"🔄 Jumped to cycle {self.cycle_count}")

            logging.info(f"📝 Recording cycle {self.cycle_count}")

            # Record overall cycle stats
            stats = self.currency_system.get_economic_stats()
            
            cursor.execute('''
                INSERT INTO cycle_records 
                (cycle_number, total_currency, total_transactions)
                VALUES (?, ?, ?)
            ''', (self.cycle_count, 
                stats.get('total_currency', 0), 
                stats.get('total_transactions', 0)))
            
            # Record individual bot stats (needs + balance)
            for bot_name, bot in self.cm.bots.items():
                balance = self.currency_system.get_balance(bot.bot_id)
                
                cursor.execute('''
                    INSERT INTO cycle_bot_stats 
                    (cycle_number, bot_id, bot_name, energy, social, curiosity, balance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (self.cycle_count, 
                    bot.bot_id, 
                    bot_name,
                    bot.needs.get('energy', 0),
                    bot.needs.get('social', 0), 
                    bot.needs.get('curiosity', 0),
                    balance))
            
            # Verify insert worked
            cursor.execute("SELECT cycle_number FROM cycle_records WHERE cycle_number = ?", (self.cycle_count,))
            if cursor.fetchone():
                logging.info(f"✅ Successfully recorded cycle {self.cycle_count}")
            else:
                logging.info(f"❌ FAILED to record cycle {self.cycle_count}")

            conn.commit()

            cursor.execute("SELECT MAX(cycle_number) FROM cycle_records")
            db_max_cycle = cursor.fetchone()[0]
            
            #logging.info(f"📊 Database now has max cycle: {db_max_cycle}")
            #logging.info(f"📊 We just tried to write cycle: {self.cycle_count}")
            
            if db_max_cycle != self.cycle_count:
                logging.info(f"🚨 ALERT: Database mismatch! Written: {self.cycle_count}, DB has: {db_max_cycle}")

            conn.close()
            
            logging.info(f"📊 Recorded cycle {self.cycle_count} data for {len(self.cm.bots)} bots")
            
        except Exception as e:
            logging.info(f"Cycle recording error: {e}")

    def check_collected_data(self):
        """Quick check of what data we're collecting"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM cycle_records")
        cycle_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM cycle_bot_stats") 
        bot_stat_count = cursor.fetchone()[0]
        
        logging.info(f"📈 Data Collection: {cycle_count} cycles, {bot_stat_count} bot records")
        
        conn.close()

    def external_data_collection(self):
        """Processing external data collection"""
        logging.info("🌤️ Processing weather data collection...")
        success = self.data_collector.collect_weather("Paris")
        if success:
            weather = self.data_collector.get_latest_weather()
            if weather:
                temp = weather.get('current_condition', [{}])[0].get('temp_C', 'Unknown')
                logging.info(f"✅ Weather collected: {temp}°C in Paris")

    def _weather_influence_cycle(self):
        """Apply weather influence to all bots"""
        try:
            # Get latest weather
            weather = self.data_collector.get_latest_weather()
            
            if not weather:
                print("🌤️ No weather data available for influence")
                return
            
            # Extract weather info
            current = weather.get('current_condition', [{}])[0]
            temperature = float(current.get('temp_C', 20))  # Default 20°C
            condition = current.get('weatherDesc', [{}])[0].get('value', '').lower()
            
            print(f"🌤️ Weather influence: {temperature}°C, {condition}")
            
            # Apply to each bot
            for bot_name, bot in self.cm.bots.items():
                self._apply_weather_to_bot(bot, temperature, condition)
                
        except Exception as e:
            print(f"❌ Weather influence error: {e}")

    def _sync_with_database(self):
        """Sync cycle count with database on startup"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        # Get max cycle in database
        cursor.execute("SELECT MAX(cycle_number) FROM cycle_records")
        db_max = cursor.fetchone()[0]
        conn.close()
        
        if db_max:
            # Database has cycles, start from next one
            self.cycle_count = db_max + 1
            print(f"🔄 Continuing from cycle {self.cycle_count} (database has up to {db_max})")
        else:
            # No cycles yet, start from 1
            self.cycle_count = 1
            print(f"🔄 Starting new from cycle 1")

    def system_cycle(self):
        """One complete cycle of bot activities"""
        if not hasattr(self, '_cycle_synced'):
            self._sync_with_database()
            self._cycle_synced = True

        print(f"🌀 START CYCLE {self.cycle_count}")

        self.cycle_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logging.info(f"\n{'='*50}")
        logging.info(f"🔄 CYCLE {self.cycle_count} - {current_time}")
        logging.info(f"{'='*50}")

        # 1. Guardian duties (most important)
        self.guardian_duties()

        # 2. Update autonomous needs & goals
        self.update_bot_needs()
        self.update_bot_goals()

        # 3. Process airport departures (bots that were waiting)
        self.airport_system.process_departures()
        self.update_bot_energy()

        # 4. Update Bots interactions | travels moved to 5
        interaction_time = time.time()
        self.check_bot_interactions(interaction_time)

        # Check if bot needs to go home (TODO)
        # 5. Airport Travels : Auto-add bots to airports based on urgency
        self.airport_system.auto_assign_bots_to_airports()
        self.update_bot_travels(self.cycle_count)

        # 6. Individual activities  
        self.individual_activities()

        # 7. IRC status report
        self.irc_status_report()

        # 8. Group conversation (if conditions are right)
        if random.random() < 0.7:  # 70% chance
            self.autonomous_conversation()

        # 9. Group conversation (if conditions are right)
        if random.random() < 0.7:  # 70% chance
            self.autonomous_conversation()

        # 10. Skills
        self.update_bot_skills()

        # 11. Knowledge Exchange
        self.update_knowledge_exchange()

        # 12. Currency Status Check
        self.check_currency_status()

        # 13. Check for economic events
        self._check_economic_events()

        # 14. Observe personalities (no actions)
        if random.random() < 50:  # Only 50% of cycles
            self._observe_economic_personalities()

        # 15. Personality-based gifts (very rare)
        self._personality_based_gifts()

        # 16. Ambitious bot opportunities
        self._personality_based_opportunities()

        # 17. Risk-taking behaviors
        self._personality_based_risks()

        # 18. Get External Data (Weather infos)
        if self.cycle_count % 30 == 0:
            self.external_data_collection()

        # 19. Weather Influences
        if self.cycle_count % 30 == 0:
            self._weather_influence_cycle()

        # 20. status updates
        self.update_bot_statuses()

        self._record_cycle_data()
        self.check_collected_data()
        # 21. Log overall status
        self._log_system_status()


    def _log_system_status(self):
        """Log the current state of all bots"""
        logging.info("\n📊 SYSTEM STATUS SUMMARY:")
        for bot_name, bot in self.cm.bots.items():
            status = f"   {bot_name}: Energy={bot.needs.get('energy', 0):.1f}, Social={bot.needs['social']:.1f}, Curiosity={bot.needs.get('curiosity', 0):.1f}"
            logging.info(status)
    
    def run_continuous(self, cycle_interval_minutes=10):
        """Run the server continuously with IRC integration"""
        logging.info("🚀 Starting Bot Server with IRC Integration!")
        
        # Start IRC systems
        self.start_samirah_permanent_irc()
        self.start_irc_scheduler()
        
        logging.info(f"⏰ Running continuous operation ({cycle_interval_minutes}min cycles)")
        logging.info("Press Ctrl+C to stop the server")
        
        try:
            while True:
                self.system_cycle()
                logging.info(f"⏰ Next cycle in {cycle_interval_minutes} minutes...")
                time.sleep(cycle_interval_minutes * 60)
                
        except KeyboardInterrupt:
            logging.info("\n🛑 Server stopped by user")
            self._shutdown()
        except Exception as e:
            logging.error(f"💥 Server crash: {e}")
            self._shutdown()
            raise
    
    def _shutdown(self):
        """Clean shutdown of all systems"""
        logging.info("🔌 Shutting down systems...")
        if self.irc_scheduler:
            self.irc_scheduler.stop()
        if self.samirah_irc:
            self.samirah_irc.disconnect()
        logging.info("✅ All systems shut down")

    def _determine_activity_type(self, bot_name):
        """Determine what type of activity the bot has been doing"""
        # Simple heuristic based on needs and personality
        bot = self.cm.bots[bot_name]
        
        if bot.needs.get('social', 0) > 70:
            return 'conversation'
        elif bot.needs.get('curiosity', 0) > 70:
            return 'exploration'
        elif bot.personality.get('openness', 0.5) > 0.7:
            return 'learning'
        else:
            return random.choice(['analysis', 'problem_solving'])

    def _initialize_needs_managers(self):
        """Initialize needs managers for all bots"""
        from core.needs_manager import NeedsManager
        self.needs_managers = {}
        for bot_name, bot in self.cm.bots.items():
            self.needs_managers[bot_name] = NeedsManager(bot)
        logging.info("🔋 Needs management system initialized")

    def update_bot_needs(self):
        """Update all bots' needs autonomously"""
        logging.info("🔋 Updating bot needs autonomously...")
        for bot_name, needs_manager in self.needs_managers.items():
            try:
                needs_manager.update_needs_autonomously()
            except Exception as e:
                logging.error(f"❌ Needs update failed for {bot_name}: {e}")

    def _initialize_skill_systems(self):
        """Initialize skill systems for all bots"""
        from core.skill_system import SkillSystem
        self.skill_systems = {}
        for bot_name, bot in self.cm.bots.items():
            self.skill_systems[bot_name] = SkillSystem(bot)
        logging.info("🎓 Skill development system initialized")

    def update_bot_skills(self):
        """Update bot skills based on recent activities"""
        logging.info("🎓 Updating bot skills...")
        for bot_name, skill_system in self.skill_systems.items():
            try:
                # Determine activity type based on recent behavior
                activity_type = self._determine_activity_type(bot_name)
                effectiveness = random.uniform(0.7, 1.0)
                
                skill_system.update_skills(activity_type, effectiveness)
                
                # Log skill improvements occasionally
                if random.random() < 0.2:  # 20% chance
                    best_skills = skill_system.get_best_skills(2)
                    if best_skills:
                        skill_desc = ", ".join([f"{s[0]} Lvl {s[1]}" for s in best_skills])
                        logging.info(f"   {bot_name} excels at: {skill_desc}")
                        
            except Exception as e:
                logging.error(f"❌ Skill update failed for {bot_name}: {e}")

    def _initialize_knowledge_exchange(self):
        """Initialize knowledge exchange system"""
        from core.knowledge_exchange import KnowledgeExchange
        self.knowledge_exchange = KnowledgeExchange(self.cm)
        logging.info("🤝 Knowledge exchange system initialized")

    def update_knowledge_exchange(self):
        """Update knowledge sharing and collaboration"""
        logging.info("🤝 Updating knowledge exchange...")
        try:
            # Initiate knowledge sharing
            self.knowledge_exchange.initiate_knowledge_exchange()
            
            # Initiate collaborations
            self.knowledge_exchange.initiate_collaboration()
            
            # Log relationships occasionally
            if random.random() < 0.1:  # 10% chance
                relationship_report = self.knowledge_exchange.get_relationship_report()
                logging.info(f"Relationship update:\n{relationship_report}")
                
        except Exception as e:
            logging.error(f"❌ Knowledge exchange failed: {e}")

    def _apply_weather_to_bot(self, bot, temperature, condition):
        """Apply small random weather effects"""
        try:
            # Base chance: 30% of bots affected by weather
            if random.random() > 0.3:
                return  # This bot isn't affected this cycle
            
            # Add weather memory
            if hasattr(bot, '_add_to_memory'):
                if temperature > 25:
                    bot._add_to_memory(f"Warm day ({temperature}°C)", 'weather')
                elif temperature < 10:
                    bot._add_to_memory(f"Chilly day ({temperature}°C)", 'weather')
            
            # SMALL adjustments (1-5% only)
            if temperature > 30:  # Very hot
                # Slightly reduce energy
                adjustment = random.uniform(0.95, 0.99)  # 1-5% reduction
                if hasattr(bot, '_update_need'):
                    bot._update_need('energy', bot.needs.get('energy', 50) * adjustment)
            
            elif temperature < 5:  # Very cold
                # Slightly reduce energy, increase curiosity
                energy_adj = random.uniform(0.96, 0.99)
                curiosity_adj = random.uniform(1.01, 1.05)
                
                if hasattr(bot, '_update_need'):
                    bot._update_need('energy', bot.needs.get('energy', 50) * energy_adj)
                    bot._update_need('curiosity', bot.needs.get('curiosity', 50) * curiosity_adj)
            
            elif 'rain' in condition:  # Rainy
                # Increase curiosity, reduce social
                curiosity_adj = random.uniform(1.02, 1.08)
                social_adj = random.uniform(0.93, 0.98)
                
                if hasattr(bot, '_update_need'):
                    bot._update_need('curiosity', bot.needs.get('curiosity', 50) * curiosity_adj)
                    bot._update_need('social', bot.needs.get('social', 50) * social_adj)
            
            print(f"🌤️ Weather affected {bot.name} (temp: {temperature}°C)")
            
        except Exception as e:
            print(f"❌ Weather effect error for {bot.name}: {e}")

    def add_bot_to_map(self, bot_id):
        """Add a bot to the map"""
        traveler = BotTraveler(bot_id, self.map)
        self.travelers[bot_id] = traveler
        
        # Log initial position
        loc = self.map.grid[traveler.x][traveler.y]
        print(f"Bot {bot_id} started at ({traveler.x}, {traveler.y}) - {loc['type']}")

        return traveler
    
    def get_bots_at_location(self, x, y):
        """Get all bots at specific coordinates"""
        return self.map.grid[x][y]['bots_present']
    
    def get_bot_location(self, bot_id):
        """Get location of specific bot"""
        traveler = self.travelers.get(bot_id)
        if traveler:
            return traveler.x, traveler.y, self.map.grid[traveler.x][traveler.y]
        return None

    def update_bot_travels(self, cycle_number):
        """Update all bot positions on the map"""
        print("\n--- Map Travel Updates ---")

        for bot_id, traveler in self.travelers.items():
            # Skip if bot is currently visiting IRC
            #if self.is_bot_on_irc(bot_id):
            #    continue

            if cycle_number % 500 == 0 or cycle_number > 1000:
                one_bot = self.cm._get_bot_by_id(bot_id)

                now_time = datetime.now()
                last_seen_from_home_time = one_bot[6]

                print(f"🤝🤝🤝 {one_bot[0]} : Time: {now_time}, Last Seen: {last_seen_from_home_time}🤝🤝🤝")
                if last_seen_from_home_time == None or (now_time - last_seen_from_home_time) > timedelta(days=10):
                    must_return_home = True
                else:
                    must_return_home = False
                home_x = one_bot[4]
                home_y = one_bot[5]
            else:
                home_x = 0
                home_y = 0
                must_return_home = False

            # Decide and execute movement
            new_pos = traveler.decide_movement(must_return_home, home_x, home_y)
            if new_pos:
                new_x, new_y = new_pos
                old_loc = self.map.grid[traveler.x][traveler.y]
                new_loc = traveler.move_to(new_x, new_y)
                
                # Log the movement
                #print(f"Bot {bot_id} moved from ({old_loc['x']}, {old_loc['y']}) to ({new_x}, {new_y})")
                #print(f"  From {old_loc['type']} to {new_loc['type']}")
                #print(f"  Energy: {traveler.energy}, Curiosity: {traveler.curiosity:.2f}")

                try:
                    if(new_loc['type'] != ''):
                        VirtualMap._store_bot_location_in_db(self, bot_id, traveler.x, traveler.y, new_loc['type'])
                        for bot_name, bot in self.cm.bots.items():
                            if bot.bot_id == bot_id:

                                #from_loc = self.map.grid[traveler.x][traveler.y]
                                #logging.info(f"from_y is: {repr(from_x)}")
                                #logging.info(f"Type: {type(from_x)}")
                                #logging.info(f"Length if sequence: {len(from_x) if hasattr(from_x, '__len__') else 'N/A'}")
                                #logging.info(f"Dir: {dir(from_x) if not isinstance(from_x, (int, float, str)) else 'simple type'}")

                                self._record_move_history(
                                    bot_id, 
                                    old_loc['x'], old_loc['y'], new_x, new_y,
                                    old_loc['type'], new_loc['type']
                                )

                                if one_bot[0] == bot_id and one_bot[4] == new_x and one_bot[5] == new_y:
                                    print(f"🤝🤝🤝 One Bot has returned Home ({one_bot[2]}): id: {bot_id} Has Returned Home !🤝🤝🤝")
                                    traveler.bot_sweet_home(bot_id)

                                if hasattr(bot, '_add_to_memory'):
                                    bot._add_to_memory(f"Traveled from {old_loc['type']} to {new_loc['type']}",'map_travel')
                                    # Check if location affects IRC curiosity
                                    self._update_irc_curiosity(bot, new_loc)
                        
                                traveler.update_one_bot_energy(bot.bot_id)

                except Exception as e:
                    logging.error(f"❌ Store Bot Location OR Add to bot's memory failed (update_bot_travels): {e}")
    
    def _update_irc_curiosity(self, bot, location):
        """Update bot's IRC curiosity based on location"""
        # Some locations make bots more curious about IRC
        location_effects = {
            'city': 0.3,      # Cities have more social interaction
            'forest': -0.1,   # Forests are solitary
            'plains': 0.1,
            'mountain': 0.2,  # Mountains have good "signal"
            'desert': -0.2,
            'water': 0.0
        }
        
        effect = location_effects.get(location['type'], 0)
        
        # Update bot's curiosity for IRC visits
        try:
            bot._update_need('curiosity', max(0, min(1, bot.needs.get('curiosity') + effect)))
        except Exception as e:
            logging.error(f"❌ Update_irc_curiosity failed: {e}")

    def check_bot_interactions(self, current_time):
        """Check if bots in same location should interact"""
        # Group bots by location
        location_map = {}  # (x,y) -> [bot_id1, bot_id2, ...]
        
        try:
            for bot_id, traveler in self.travelers.items():
                if not traveler.bot:
                    continue
                    
                # Only check bots that can interact
                if not traveler.can_interact(current_time):
                    continue
                    
                location_key = (traveler.x, traveler.y)
                location_map.setdefault(location_key, []).append(bot_id)
            
            # Process locations with multiple bots
            for (x, y), bot_ids in location_map.items():
                if len(bot_ids) >= 2:
                    # Bots are together - trigger interaction
                    self._create_bot_interaction(bot_ids, x, y, current_time)
        except Exception as e:
            logging.error(f"❌ Check Bot Interactions failed: {e}")
            return False

    def _create_bot_interaction(self, bot_ids, x, y, current_time):
        """Handle interaction between multiple bots"""
        location = self.map.grid[x][y]
        location_type = location['type']
        
        print(f"🤝 Interaction at {location_type} ({x},{y}): Bots {bot_ids}")
        
        # Interaction types based on location
        interaction_templates = {
            'city': [
                "exchanged information in the bustling city",
                "shared urban discoveries",
                "discussed city life"
            ],
            'forest': [
                "met on a quiet forest path",
                "shared woodland observations", 
                "exchanged nature findings"
            ],
            'mountain': [
                "crossed paths on the mountain trail",
                "shared vantage point observations",
                "discussed mountain discoveries"
            ],
            'plains': [
                "met on the open plains",
                "shared wide-area observations",
                "exchanged travel stories"
            ]
        }
        
        # Get appropriate interaction text
        templates = interaction_templates.get(location_type, ["met and exchanged information"])
        interaction_text = random.choice(templates)
        
        try:
            """Store bot interactions in database for dashboard"""
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            
            for bot_id in bot_ids:
                cursor.execute('''
                    INSERT INTO bot_interactions 
                    (bot_id, other_bots, location_x, location_y, location_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                ''', (bot_id, ','.join(map(str, [b for b in bot_ids if b != bot_id])),
                    x, y, location_type))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"❌ Store bot interactions failed (_create_bot_interaction): {e}")
                
        # Log interaction for each bot
        for bot_id in bot_ids:
            traveler = self.travelers.get(bot_id)
            if traveler and traveler.bot:
                # Create memory entry
                other_bots = [str(b) for b in bot_ids if b != bot_id]
                memory_text = f"{interaction_text} with bots {', '.join(other_bots)}"
                
                try:
                    for bot_name, bot in self.cm.bots.items():
                        if bot.bot_id == bot_id:
                            if hasattr(bot, '_add_to_memory'):
                                bot._add_to_memory(memory_text, 'bot_interaction')
                except Exception as e:
                    logging.error(f"❌ Add to bot's memory failed (_create_bot_interaction): {e}")
                
                # Update interaction cooldown
                traveler.last_interaction_time = current_time
                
                # Share curiosity boost
                traveler.bot.curiosity = min(1.0, traveler.bot.curiosity + 0.15)
                
                # Location-specific bonuses
                if location_type == 'city':
                    # Cities are information hubs
                    traveler.bot.curiosity = min(1.0, traveler.bot.curiosity + 0.1)
                elif location_type == 'forest':
                    # Peaceful forests allow reflection
                    traveler.energy += 10  # Extra energy restoration

    def update_bot_energy(self):
        try:
            """Restore bot energy over time"""
            for traveler in self.travelers.values():
                # Rest based on location
                location = self.map.grid[traveler.x][traveler.y]
                rest_rate = {
                    'city': 45.008,     # Easy to rest in cities
                    'forest': 60.072,   # Peaceful forests
                    'mountain': 30.061, # Hard to rest on mountains
                    'desert': 12.001,   # Hard to rest in deserts
                    'water': 30.004,
                    'plains': 50.001
                }.get(location['type'], 5)
                
                traveler.energy = min(100, traveler.energy + rest_rate)
                # Extra energy restoration
                energy_restore = 25.001
                memory = "Resting"
                
                traveler.energy = min(100, traveler.energy + energy_restore)
                
                if traveler.bot:
                    traveler.bot._add_to_memory(memory, 'rest')
                    traveler.bot._update_need('energy', self.needs['energy'] + traveler.energy)

                traveler.add_energy(energy_restore)
                
        except Exception as e:
            logging.error(f"❌ Bot_server.py => update_bot_energy failed with energy: {traveler.energy} {e}")
        
    def log_status_changes(self):
        """Log status change"""
        try:  

            # Optional: Log status changes
            for bot in self.cm.bots.items():
                old_status = getattr(bot, '_last_status', None)
                new_status = self.determine_bot_status(bot)
                
                if old_status != new_status:
                    print(f"🔄 {bot.name}: {old_status or 'N/A'} → {new_status}")
                    bot._add_to_memory(f"Status changed to {new_status}", 'status_change')
                    bot._last_status = new_status 
                print("🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ 🌤️ " + bot)
            # Check in priority order
            #if bot.is_on_irc:
            #    return 'irc_visiting'

            
            # Check location-based status
            if hasattr(bot, 'traveler') and bot.traveler:
                location = self.map.grid[bot.traveler.x][bot.traveler.y]
                
                if location['type'] == 'city' and random.random() < 0.3:
                    return 'interacting'
                
                if location['type'] == 'forest' and bot.curiosity > 0.8:
                    return 'exploring'
            
            # Curiosity-based
            #if (bot.needs.get('curiosity', 0)) > 0.7:
            #    return 'curious'
            
            # Activity-based (from recent memories)
            #recent_activities = self.get_recent_activities(bot.id)
            #if 'map_travel' in recent_activities:
            #    return 'exploring'
            #elif 'bot_interaction' in recent_activities:
            #    return 'interacting'
            #elif 'irc_message' in recent_activities:
            #    return 'learning'
            
            # Default based on time of day (for fun)
            #import datetime
            #hour = datetime.datetime.now().hour
            #if 2 <= hour <= 6:
            #    return 'resting'

            #status = {'icon': '⚡'}
            
            return True
    
        except Exception as e:
            logging.error(f"❌ Determine Current Status failed: {e}")

    def update_bot_statuses(self):
        """Update all bot statuses in database"""
        try:
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()

            cursor.execute('SELECT DISTINCT bot_id FROM needs')
            bot_ids = [row[0] for row in cursor.fetchall()]  # row[0] not row['bot_id']
            
            for bot_id in bot_ids:
                # Get needs - use row[0], row[1]
                cursor.execute('''
                    SELECT need_name, value 
                    FROM needs 
                    WHERE bot_id = ? 
                    AND need_name IN ('energy', 'social', 'curiosity')
                ''', (bot_id,))
                
                needs = {}
                for row in cursor.fetchall():
                    need_name = row[0]  # First column
                    value = row[1]      # Second column
                    needs[need_name] = value
                
                # Set defaults
                energy = needs.get('energy', 40)
                social = needs.get('social', 50)
                curiosity = needs.get('curiosity', 50)
                
                # Determine status
                if energy < 30:
                    status, icon = 'tired', '😴'
                elif curiosity > 70:
                    status, icon = 'curious', '🔍'
                elif social > 70:
                    status, icon = 'social', '🤝'
                else:
                    status, icon = 'active', '⚡'
                
                description = f"Energy: {energy}% | Social: {social}% | Curiosity: {curiosity}%"
                
                # Insert/Update
                cursor.execute('''
                    INSERT OR REPLACE INTO bot_status 
                    (bot_id, status, icon, description, timestamp) 
                    VALUES (?, ?, ?, ?, datetime('now'))
                ''', (bot_id, status, icon, description))

                print("Bot statuses updated")

            conn.commit()
            conn.close()
            for bot_id in bot_ids:
                self.track_status_history(bot_id, status, icon)

        except Exception as e:
            logging.error(f"❌ Update Bots Statuses failed: {e}")


    # Track status history for insights
    def track_status_history(self, bot_id, status, icon):
        """Store status changes for analytics"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bot_status_history 
            (bot_id, icon, status, duration_minutes, timestamp) 
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (bot_id, status, icon, 10  ))  # Assuming 10-minute cycles
        
        conn.commit()
        conn.close()

    def _record_move_history(self, bot_id, from_x, from_y, to_x, to_y, from_type, to_type):
        """Store move in history table"""
        try:
            #params = [bot_id, from_x, from_y, to_x, to_y, from_type, to_type]
            #for i, param in enumerate(params, 1):
            #    logging.error(f"Param {i}: {repr(param)} | Type: {type(param)}")
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bot_move_history 
                (bot_id, from_x, from_y, to_x, to_y, from_location_type, to_location_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (bot_id, from_x, from_y, to_x, to_y, from_type, to_type))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"❌ Recording Move History failed: {e}")

# Alternative: Scheduled approach
def run_scheduled_server():
    """Run with specific scheduled activities"""
    server = BotServerWithIRC()
    
    # Start IRC systems
    server.start_samirah_permanent_irc()
    server.start_irc_scheduler()
    
    # Schedule activities
    schedule.every(15).minutes.do(server.guardian_duties)
    schedule.every(30).minutes.do(server.autonomous_conversation)
    schedule.every(10).minutes.do(server.individual_activities)
    schedule.every(1).hours.do(server.irc_status_report)
    
    logging.info("⏰ Scheduled server with IRC started")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    server = BotServerWithIRC()
    
    print("🤖 BOT SERVER WITH IRC INTEGRATION")
    print("1 - Continuous mode (recommended)")
    print("2 - Scheduled mode")
    
    choice = input("Choose mode (1 or 2): ").strip()
    
    if choice == "1":
        interval = input("Cycle interval in minutes (default 10): ").strip()
        interval = int(interval) if interval.isdigit() else 10
        server.run_continuous(interval)
    else:
        run_scheduled_server()
