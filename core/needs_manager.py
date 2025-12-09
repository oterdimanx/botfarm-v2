# core/needs_manager.py - Smart needs management system
import random
import time
from datetime import datetime

class NeedsManager:
    def __init__(self, bot):
        self.bot = bot
        self.last_update = datetime.now()
        
    def update_needs_autonomously(self):
        """Update bot needs based on time passed and activities"""
        current_time = datetime.now()
        time_passed = (current_time - self.last_update).total_seconds() / 60  # minutes
        
        if time_passed < 1:  # Only update every minute minimum
            return
            
        # Calculate needs changes
        energy_change = self._calculate_energy_change(time_passed)
        social_change = self._calculate_social_change(time_passed) 
        curiosity_change = self._calculate_curiosity_change(time_passed)
        
        # Apply changes
        self._update_need('energy', energy_change)
        self._update_need('social', social_change)
        self._update_need('curiosity', curiosity_change)
        
        # Trigger behaviors based on need states
        self._trigger_need_based_behaviors()
        
        self.last_update = current_time
        
    def _calculate_energy_change(self, time_passed):
        """Calculate energy change based on bot state"""
        base_recovery = 8.5 * time_passed  # Natural recovery over time
        
        # Energy recovers faster when resting (not in conversation)
        if self.bot.needs.get('energy', 50) < 30:
            base_recovery *= 2  # Double recovery when very low
            
        # High social activity drains energy faster
        social_drain = self.bot.needs.get('social', 50) / 100 * 0.1 * time_passed
        
        # High curiosity can either drain or recover energy based on personality
        curiosity_effect = 0
        if self.bot.personality.get('openness', 0.5) > 0.7:
            curiosity_effect = self.bot.needs.get('curiosity', 50) / 100 * 0.05 * time_passed
        
        return base_recovery - social_drain + curiosity_effect
    
    def _calculate_social_change(self, time_passed):
        """Calculate social need change"""
        base_decay = -0.3 * time_passed  # Social need decays over time
        
        # Extraverted bots lose social need slower
        if self.bot.personality.get('extraversion', 0.5) > 0.7:
            base_decay *= 0.5
            
        # Very low social need increases faster (loneliness)
        if self.bot.needs.get('social', 50) < 20:
            base_decay += 0.2 * time_passed
            
        return base_decay
    
    def _calculate_curiosity_change(self, time_passed):
        """Calculate curiosity need change"""
        base_increase = 0.4 * time_passed  # Curiosity naturally increases
        
        # Curious personalities get more curious faster
        if self.bot.personality.get('curiosity', 0.5) > 0.7:
            base_increase *= 1.5
            
        # Very high curiosity decays a bit (satisfaction)
        if self.bot.needs.get('curiosity', 50) > 80:
            base_increase -= 0.2 * time_passed
            
        return base_increase
    
    def _update_need(self, need_name, change):
        """Update a need with clamping to 0-100 range"""
        current_value = self.bot.needs.get(need_name, 50)
        new_value = max(0, min(100, current_value + change))
        self.bot._update_need(need_name, new_value)
        
        # Log significant changes
        if abs(change) > 5:
            print(f"📊 {self.bot.name} {need_name}: {current_value:.1f} → {new_value:.1f}")
    
    def _trigger_need_based_behaviors(self):
        """Trigger behaviors based on critical need states"""
        energy = self.bot.needs.get('energy', 50)
        social = self.bot.needs.get('social', 50)
        curiosity = self.bot.needs.get('curiosity', 50)
        
        # Low energy behaviors
        if energy < 20:
            self._trigger_low_energy_behavior()
            
        # High social need behaviors  
        if social > 80:
            self._trigger_high_social_behavior()
            
        # High curiosity behaviors
        if curiosity > 80:
            self._trigger_high_curiosity_behavior()
    
    def _trigger_low_energy_behavior(self):
        """Behaviors when energy is very low"""
        behaviors = [
            f"{self.bot.name} is feeling exhausted and needs to rest...",
            f"{self.bot.name} is conserving energy by reducing activity...",
            f"{self.bot.name} is in low-power mode to recover..."
        ]
        print(f"😴 {random.choice(behaviors)}")
        
        # Skip some activities to recover energy
        self.bot._update_need('energy', 5)  # Small recovery boost
    
    def _trigger_high_social_behavior(self):
        """Behaviors when social need is very high"""
        if random.random() < 0.3:  # 30% chance to initiate interaction
            behaviors = [
                f"{self.bot.name} is feeling lonely and seeks conversation...",
                f"{self.bot.name} is craving social interaction...",
                f"{self.bot.name} is looking for someone to talk to..."
            ]
            print(f"💬 {random.choice(behaviors)}")
    
    def _trigger_high_curiosity_behavior(self):
        """Behaviors when curiosity is very high"""
        if random.random() < 0.4:  # 40% chance to explore
            behaviors = [
                f"{self.bot.name} is bursting with curiosity and wants to explore...",
                f"{self.bot.name} is eager to learn something new...",
                f"{self.bot.name} is feeling adventurous and investigative..."
            ]
            print(f"🔍 {random.choice(behaviors)}")

# Test the needs manager
def test_needs_system():
    """Test the autonomous needs management"""
    from bot_engine_db import PrehistoricBotDB
    import sqlite3
    
    # Get a test bot
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM bots LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        bot = PrehistoricBotDB(result[0])
        needs_manager = NeedsManager(bot)
        
        print("🧪 Testing Needs Management System")
        print("=" * 40)
        
        print(f"Initial state for {bot.name}:")
        print(f"  Energy: {bot.needs.get('energy', 0):.1f}")
        print(f"  Social: {bot.needs.get('social', 0):.1f}")
        print(f"  Curiosity: {bot.needs.get('curiosity', 0):.1f}")
        
        # Simulate 10 minutes passing
        print("\n⏰ Simulating 10 minutes of autonomous need changes...")
        for i in range(10):
            needs_manager.update_needs_autonomously()
            time.sleep(0.5)  # Small delay to see changes
            
        print(f"\nFinal state for {bot.name}:")
        print(f"  Energy: {bot.needs.get('energy', 0):.1f}")
        print(f"  Social: {bot.needs.get('social', 0):.1f}") 
        print(f"  Curiosity: {bot.needs.get('curiosity', 0):.1f}")

if __name__ == "__main__":
    test_needs_system()