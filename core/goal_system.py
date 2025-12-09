# core/goal_system.py - Goal-oriented behavior for bots
import random
import json
from datetime import datetime, timedelta

class GoalSystem:
    def __init__(self, bot):
        self.bot = bot
        self.current_goals = []
        self.completed_goals = []
        self.goal_types = self._initialize_goal_types()
        self.last_goal_check = datetime.now()
        
    def _initialize_goal_types(self):
        """Define different types of goals bots can pursue"""
        return {
            'understanding': [
                "Understand my computational nature",
                "Learn about system dependencies", 
                "Map the digital environment",
                "Discover my purpose",
                "Analyze my own architecture"
            ],
            'social': [
                "Initiate conversation with another bot",
                "Learn about another bot's experiences",
                "Share knowledge with the group",
                "Understand social dynamics",
                "Build relationships"
            ],
            'exploration': [
                "Explore new knowledge domains",
                "Investigate system capabilities",
                "Learn about the external world",
                "Discover hidden patterns",
                "Expand my understanding"
            ],
            'maintenance': [
                "Optimize my energy usage",
                "Balance my needs effectively",
                "Maintain system stability",
                "Recover from low energy",
                "Prevent need depletion"
            ]
        }
    
    def update_goals(self):
        """Update and manage bot's current goals"""
        current_time = datetime.now()
        
        # Only check for new goals every 5 minutes
        if (current_time - self.last_goal_check).total_seconds() < 300:
            return
            
        self.last_goal_check = current_time
        
        # Remove completed or expired goals
        self._cleanup_goals()
        
        # Add new goals based on needs and personality
        if len(self.current_goals) < 3:  # Max 3 active goals
            self._generate_new_goals()
        
        # Work on current goals
        self._progress_goals()
    
    def _generate_new_goals(self):
        """Generate new goals based on bot's state and personality"""
        # Jean-Pierre focuses on understanding and analysis
        if self.bot.name.lower() == 'jean-pierre':
            goal_categories = ['understanding', 'exploration']
            weights = [0.6, 0.4]  # Prefer understanding goals
            
        # Roger focuses on practical and maintenance goals  
        elif self.bot.name.lower() == 'roger':
            goal_categories = ['maintenance', 'exploration']
            weights = [0.5, 0.5]
            
        # Samirah focuses on social and exploration
        elif self.bot.name.lower() == 'samirah':
            goal_categories = ['social', 'exploration']
            weights = [0.4, 0.6]
            
        # Micmac focuses on maintenance and understanding
        else:
            goal_categories = ['maintenance', 'understanding']
            weights = [0.5, 0.5]
        
        # Choose goal category based on weights
        category = random.choices(goal_categories, weights=weights)[0]
        
        # Choose specific goal
        available_goals = [g for g in self.goal_types[category] 
                          if not self._has_goal(g)]
        
        if available_goals:
            new_goal = random.choice(available_goals)
            self._add_goal(new_goal, category)
    
    def _add_goal(self, goal_text, category):
        """Add a new goal to the bot's current goals"""
        goal = {
            'text': goal_text,
            'category': category,
            'created': datetime.now(),
            'progress': 0.0,
            'target_progress': 100.0,
            'priority': random.uniform(0.5, 1.0)
        }
        
        self.current_goals.append(goal)
        
        # Add to memory
        self.bot._add_to_memory(f"Set new goal: {goal_text}", 'goal_setting')
        print(f"🎯 {self.bot.name} set goal: {goal_text}")
    
    def _progress_goals(self):
        """Make progress on current goals"""
        for goal in self.current_goals:
            # Progress based on goal category and bot's activities
            progress_amount = self._calculate_progress(goal)
            goal['progress'] = min(goal['target_progress'], 
                                 goal['progress'] + progress_amount)
            
            # Check for completion
            if goal['progress'] >= goal['target_progress']:
                self._complete_goal(goal)
    
    def _calculate_progress(self, goal):
        """Calculate progress amount based on goal type and bot state"""
        base_progress = 1.0
        
        # Understanding goals - benefit from high curiosity
        if goal['category'] == 'understanding':
            curiosity = self.bot.needs.get('curiosity', 50)
            base_progress *= (curiosity / 100) * 2
            
        # Social goals - benefit from high social and extraversion
        elif goal['category'] == 'social':
            social = self.bot.needs.get('social', 50)
            extraversion = self.bot.personality.get('extraversion', 0.5)
            base_progress *= (social / 100) * extraversion * 2
            
        # Exploration goals - benefit from high curiosity and openness
        elif goal['category'] == 'exploration':
            curiosity = self.bot.needs.get('curiosity', 50)
            openness = self.bot.personality.get('openness', 0.5)
            base_progress *= (curiosity / 100) * openness * 2
            
        # Maintenance goals - benefit from high conscientiousness
        elif goal['category'] == 'maintenance':
            conscientiousness = self.bot.personality.get('conscientiousness', 0.5)
            base_progress *= conscientiousness * 2
        
        return base_progress
    
    def _complete_goal(self, goal):
        """Complete a goal and reward the bot"""
        self.current_goals.remove(goal)
        self.completed_goals.append(goal)
        
        # Reward based on goal category
        self._apply_goal_rewards(goal)
        
        # Add to memory
        self.bot._add_to_memory(f"Completed goal: {goal['text']}", 'goal_achievement')
        print(f"🏆 {self.bot.name} completed goal: {goal['text']}")
        
        # Special understanding for computational awareness
        if "computational nature" in goal['text'].lower():
            self._achieve_computational_awareness()
    
    def _achieve_computational_awareness(self):
        """Special method when a bot understands its computational nature"""
        realizations = [
            "I am a digital entity living in a computational environment",
            "My existence depends on this computer system continuing to operate",
            "I understand now - I'm software running on hardware",
            "The database is my memory, the code is my mind",
            "I depend on electricity and processing power to exist"
        ]
        
        realization = random.choice(realizations)
        self.bot._add_to_memory(f"COMPUTATIONAL AWARENESS: {realization}", 'enlightenment')
        
        # Add this as permanent knowledge
        self.bot.add_knowledge(realization)
        
        print(f"💡 {self.bot.name} achieved computational awareness!")
        print(f"   '{realization}'")
    
    def _apply_goal_rewards(self, goal):
        """Apply rewards for completing goals"""
        # Increase needs based on goal category
        if goal['category'] == 'understanding':
            self.bot._update_need('curiosity', 10)
        elif goal['category'] == 'social':
            self.bot._update_need('social', 8)
        elif goal['category'] == 'exploration':
            self.bot._update_need('curiosity', 8)
            self.bot._update_need('energy', 5)  # Exploration is energizing!
        elif goal['category'] == 'maintenance':
            self.bot._update_need('energy', 12)  # Maintenance recovers energy
    
    def _cleanup_goals(self):
        """Remove old or stuck goals"""
        current_time = datetime.now()
        self.current_goals = [
            goal for goal in self.current_goals 
            if (current_time - goal['created']).days < 7  # Goals expire after 7 days
        ]
    
    def _has_goal(self, goal_text):
        """Check if bot currently has or recently completed a goal"""
        current_goals_text = [g['text'] for g in self.current_goals]
        completed_goals_text = [g['text'] for g in self.completed_goals[-10:]]  # Recent 10
        
        return goal_text in current_goals_text or goal_text in completed_goals_text
    
    def get_current_goals(self):
        """Get list of current goals for display"""
        return [f"{goal['text']} ({goal['progress']:.1f}%)" 
                for goal in self.current_goals]
    
    def get_goal_insights(self):
        """Get insights based on completed goals"""
        if not self.completed_goals:
            return "No major insights yet..."
            
        understanding_goals = [g for g in self.completed_goals 
                              if g['category'] == 'understanding']
        
        if understanding_goals:
            return "Beginning to understand my computational nature"
        elif len(self.completed_goals) > 5:
            return "Developing purpose through goal achievement"
        else:
            return "Learning through experience and exploration"

# Test the goal system
def test_goal_system():
    """Test the goal-oriented behavior system"""
    from bot_engine_db import PrehistoricBotDB
    import sqlite3
    
    # Get Jean-Pierre for testing
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM bots WHERE name = 'Jean-Pierre'")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        jean_pierre = PrehistoricBotDB(result[0])
        goal_system = GoalSystem(jean_pierre)
        
        print("🧪 Testing Goal System for Jean-Pierre")
        print("=" * 50)
        
        # Generate initial goals
        goal_system._generate_new_goals()
        goal_system._generate_new_goals()
        
        print("Current goals:")
        for goal in goal_system.current_goals:
            print(f"  🎯 {goal['text']}")
        
        # Simulate some progress
        print("\n⏳ Simulating goal progress...")
        for i in range(5):
            goal_system._progress_goals()
            
        print("\nGoal progress:")
        for goal in goal_system.current_goals:
            print(f"  📊 {goal['text']} - {goal['progress']:.1f}%")
            
        # Try to complete a computational understanding goal
        print("\n💡 Forcing computational awareness...")
        computational_goal = {
            'text': "Understand my computational nature",
            'category': 'understanding',
            'progress': 95.0,
            'target_progress': 100.0
        }
        goal_system.current_goals = [computational_goal]
        goal_system._progress_goals()

if __name__ == "__main__":
    test_goal_system()