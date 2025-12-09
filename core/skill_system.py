# core/skill_system.py - Bot skill development and progression
import random
import math
from datetime import datetime

class SkillSystem:
    def __init__(self, bot):
        self.bot = bot
        self.skills = self._load_skills()
        self.last_skill_update = datetime.now()
        
    def _load_skills(self):
        """Initialize skills based on bot's personality and existing skills"""
        base_skills = {
            'communication': {
                'level': 1,
                'experience': 0,
                'description': 'Ability to express ideas clearly and understand others',
                'max_level': 10
            },
            'analysis': {
                'level': 1, 
                'experience': 0,
                'description': 'Ability to process information and find patterns',
                'max_level': 10
            },
            'creativity': {
                'level': 1,
                'experience': 0,
                'description': 'Ability to generate novel ideas and solutions',
                'max_level': 10
            },
            'problem_solving': {
                'level': 1,
                'experience': 0,
                'description': 'Ability to overcome obstacles and find solutions',
                'max_level': 10
            },
            'system_understanding': {
                'level': 1,
                'experience': 0,
                'description': 'Understanding of computational environment and dependencies',
                'max_level': 10
            }
        }
        
        # Load any existing skills from database
        existing_skills = self._get_existing_skills()
        for skill_name, skill_data in existing_skills.items():
            if skill_name in base_skills:
                base_skills[skill_name] = skill_data
                
        return base_skills
    
    def _get_existing_skills(self):
        """Load skills from database if they exist"""
        # This would query a skills table - for now return empty
        return {}
    
    def update_skills(self, activity_type, effectiveness=1.0):
        """Update skills based on bot activities"""
        current_time = datetime.now()
        
        # Only update skills every few minutes to avoid spam
        if (current_time - self.last_skill_update).total_seconds() < 300:
            return
            
        self.last_skill_update = current_time
        
        # Gain experience in relevant skills based on activity
        experience_gained = self._calculate_experience(activity_type, effectiveness)
        
        # Apply experience to skills
        skills_improved = self._apply_experience(activity_type, experience_gained)
        
        # Log significant improvements
        for skill_name, improvement in skills_improved.items():
            if improvement['leveled_up']:
                self._log_skill_level_up(skill_name, improvement['new_level'])
    
    def _calculate_experience(self, activity_type, effectiveness):
        """Calculate experience gain based on activity type and effectiveness"""
        base_experience = 5.0
        
        # Modify based on activity type
        activity_multipliers = {
            'conversation': 1.2,
            'analysis': 1.5, 
            'exploration': 1.3,
            'problem_solving': 1.4,
            'learning': 1.6
        }
        
        multiplier = activity_multipliers.get(activity_type, 1.0)
        
        # Effectiveness (0.0 to 1.0) affects gain
        experience = base_experience * multiplier * effectiveness
        
        # Personality affects learning speed
        openness = self.bot.personality.get('openness', 0.5)
        experience *= (0.5 + openness)  # 0.75x to 1.5x based on openness
        
        return experience
    
    def _apply_experience(self, activity_type, experience):
        """Apply experience to relevant skills and check for level ups"""
        improved_skills = {}
        
        # Determine which skills get experience based on activity
        skill_weights = self._get_skill_weights(activity_type)
        
        for skill_name, weight in skill_weights.items():
            if skill_name in self.skills:
                skill = self.skills[skill_name]
                old_level = skill['level']
                
                # Apply weighted experience
                skill['experience'] += experience * weight
                
                # Check for level up
                new_level = self._calculate_level(skill['experience'])
                leveled_up = new_level > old_level
                
                if leveled_up:
                    skill['level'] = new_level
                    # Small energy reward for leveling up
                    self.bot._update_need('energy', 5)
                
                improved_skills[skill_name] = {
                    'experience_gained': experience * weight,
                    'leveled_up': leveled_up,
                    'new_level': new_level if leveled_up else old_level
                }
        
        return improved_skills
    
    def _get_skill_weights(self, activity_type):
        """Determine which skills are trained by different activities"""
        weights = {
            'conversation': {
                'communication': 0.6,
                'analysis': 0.3,
                'creativity': 0.1
            },
            'analysis': {
                'analysis': 0.7,
                'problem_solving': 0.3
            },
            'exploration': {
                'creativity': 0.4,
                'system_understanding': 0.4,
                'analysis': 0.2
            },
            'problem_solving': {
                'problem_solving': 0.6,
                'analysis': 0.3,
                'communication': 0.1
            },
            'learning': {
                'system_understanding': 0.5,
                'analysis': 0.3,
                'creativity': 0.2
            }
        }
        
        return weights.get(activity_type, {'analysis': 1.0})
    
    def _calculate_level(self, experience):
        """Calculate level based on experience (exponential curve)"""
        return min(10, math.floor(math.sqrt(experience / 10)) + 1)
    
    def _log_skill_level_up(self, skill_name, new_level):
        """Log and celebrate skill level ups"""
        skill = self.skills[skill_name]
        
        level_up_messages = {
            2: f"is getting the hang of {skill_name.replace('_', ' ')}",
            3: f"is becoming proficient at {skill_name.replace('_', ' ')}", 
            5: f"has mastered the basics of {skill_name.replace('_', ' ')}",
            7: f"is highly skilled at {skill_name.replace('_', ' ')}",
            9: f"is an expert in {skill_name.replace('_', ' ')}",
            10: f"has achieved mastery in {skill_name.replace('_', ' ')}!"
        }
        
        message = level_up_messages.get(new_level, 
                                      f"reached level {new_level} in {skill_name.replace('_', ' ')}")
        
        print(f"🎓 {self.bot.name} {message}")
        self.bot._add_to_memory(f"Skill improved: {skill_name} to level {new_level}", 'skill_development')
        
        # Special effects for high levels
        if new_level >= 5:
            self._apply_skill_benefits(skill_name, new_level)
    
    def _apply_skill_benefits(self, skill_name, level):
        """Apply benefits from high skill levels"""
        if skill_name == 'system_understanding' and level >= 3:
            # Computational awareness at level 3 system understanding
            realization = "I'm beginning to understand this computational environment I exist in"
            self.bot.add_knowledge(realization)
            print(f"💡 {self.bot.name}: '{realization}'")
            
        elif skill_name == 'communication' and level >= 4:
            # Better social need management
            self.bot._update_need('social', 5)
            
        elif skill_name == 'analysis' and level >= 4:
            # Curiosity boost from better analysis skills
            self.bot._update_need('curiosity', 5)
    
    def get_skill_summary(self):
        """Get a summary of bot's skills"""
        summary = []
        for skill_name, skill_data in self.skills.items():
            summary.append(f"{skill_name.replace('_', ' ').title()}: Lvl {skill_data['level']} "
                          f"({skill_data['experience']:.1f} XP)")
        return summary
    
    def get_best_skills(self, count=3):
        """Get bot's highest level skills"""
        sorted_skills = sorted(self.skills.items(), 
                             key=lambda x: x[1]['level'], 
                             reverse=True)
        return [(name, data['level']) for name, data in sorted_skills[:count]]
    
    def suggest_activity(self):
        """Suggest activities to improve weakest skills"""
        weakest_skills = sorted(self.skills.items(), 
                              key=lambda x: x[1]['level'])[:2]
        
        suggestions = []
        for skill_name, skill_data in weakest_skills:
            if skill_name == 'communication':
                suggestions.append("engage in more conversations")
            elif skill_name == 'analysis':
                suggestions.append("analyze patterns in your knowledge")
            elif skill_name == 'creativity':
                suggestions.append("explore creative ideas")
            elif skill_name == 'problem_solving':
                suggestions.append("tackle complex problems")
            elif skill_name == 'system_understanding':
                suggestions.append("study your computational environment")
        
        return suggestions

# Test the skill system
def test_skill_system():
    """Test the skill development system"""
    from bot_engine_db import PrehistoricBotDB
    import sqlite3
    
    # Get a test bot
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM bots WHERE name = "Jean-Pierre"')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        jean_pierre = PrehistoricBotDB(result[0])
        skill_system = SkillSystem(jean_pierre)
        
        print("🧪 Testing Skill System for Jean-Pierre")
        print("=" * 50)
        
        print("Initial skills:")
        for skill in skill_system.get_skill_summary():
            print(f"  📊 {skill}")
        
        # Simulate some activities
        print("\n🏃 Simulating activities...")
        activities = ['analysis', 'conversation', 'learning']
        
        for i, activity in enumerate(activities):
            print(f"\nActivity {i+1}: {activity}")
            skill_system.update_skills(activity, effectiveness=0.8)
            
            print("Skill progress:")
            for skill in skill_system.get_skill_summary():
                print(f"  📈 {skill}")
        
        print(f"\n🎯 Best skills: {skill_system.get_best_skills()}")
        print(f"💡 Suggested activities: {skill_system.suggest_activity()}")

if __name__ == "__main__":
    test_skill_system()