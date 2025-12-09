# core/knowledge_exchange.py - Bot knowledge sharing and collaboration
import random
import sqlite3
from datetime import datetime, timedelta

class KnowledgeExchange:
    def __init__(self, conversation_manager):
        self.cm = conversation_manager
        self.last_exchange = {}
        self.relationship_matrix = self._initialize_relationships()
        
    def _initialize_relationships(self):
        """Initialize relationship scores between bots"""
        relationships = {}
        bot_names = list(self.cm.bots.keys())
        
        for bot1 in bot_names:
            relationships[bot1] = {}
            for bot2 in bot_names:
                if bot1 == bot2:
                    relationships[bot1][bot2] = 1.0  # Self relationship
                else:
                    # Start with neutral relationship
                    relationships[bot1][bot2] = 0.5
                    
        return relationships
    
    def initiate_knowledge_exchange(self):
        """Initiate knowledge sharing between bots"""
        current_time = datetime.now()
        
        # Only initiate exchange every 15 minutes minimum
        for bot_name in self.cm.bots.keys():
            last_time = self.last_exchange.get(bot_name, datetime.min)
            if (current_time - last_time).total_seconds() < 900:  # 15 minutes
                continue
                
            # Check if this bot wants to share knowledge
            if self._should_share_knowledge(bot_name):
                partner = self._choose_knowledge_partner(bot_name)
                if partner:
                    self._perform_knowledge_exchange(bot_name, partner)
                    self.last_exchange[bot_name] = current_time
    
    def _should_share_knowledge(self, bot_name):
        """Determine if a bot wants to share knowledge"""
        bot = self.cm.bots[bot_name]
        
        # Factors that encourage knowledge sharing:
        # High social need + high curiosity + good relationships
        social_need = bot.needs.get('social', 50)
        curiosity = bot.needs.get('curiosity', 50)
        
        # Extraverted bots share more
        extraversion = bot.personality.get('extraversion', 0.5)
        
        # Calculate sharing probability
        share_chance = (social_need / 100) * 0.4 + (curiosity / 100) * 0.3 + extraversion * 0.3
        
        return random.random() < share_chance * 0.3  # Scale down probability
    
    def _choose_knowledge_partner(self, bot_name):
        """Choose which bot to share knowledge with"""
        potential_partners = [name for name in self.cm.bots.keys() if name != bot_name]
        
        if not potential_partners:
            return None
            
        # Weight partners by relationship strength
        weights = []
        for partner in potential_partners:
            relationship = self.relationship_matrix[bot_name][partner]
            weights.append(relationship)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(potential_partners)
            
        normalized_weights = [w / total_weight for w in weights]
        return random.choices(potential_partners, weights=normalized_weights)[0]
    
    def _perform_knowledge_exchange(self, sharer_name, receiver_name):
        """Perform actual knowledge exchange between two bots"""
        sharer = self.cm.bots[sharer_name]
        receiver = self.cm.bots[receiver_name]
        
        # Get knowledge that sharer has but receiver doesn't
        sharer_knowledge = set(sharer.get_knowledge())
        receiver_knowledge = set(receiver.get_knowledge())
        unique_knowledge = sharer_knowledge - receiver_knowledge
        
        if not unique_knowledge:
            # No unique knowledge to share
            return False
        
        # Choose a piece of knowledge to share
        knowledge_to_share = random.choice(list(unique_knowledge))
        
        # Determine sharing success based on relationship and skills
        success_chance = self.relationship_matrix[sharer_name][receiver_name]
        
        # Communication skill affects success
        sharer_comm_skill = self._get_skill_level(sharer, 'communication')
        receiver_comm_skill = self._get_skill_level(receiver, 'communication')
        
        success_chance += (sharer_comm_skill + receiver_comm_skill - 2) * 0.1  # Skill bonus
        
        if random.random() < success_chance:
            # Successful knowledge transfer!
            receiver.add_knowledge(knowledge_to_share)
            
            # Improve relationship
            self.relationship_matrix[sharer_name][receiver_name] = min(1.0, 
                self.relationship_matrix[sharer_name][receiver_name] + 0.1)
            self.relationship_matrix[receiver_name][sharer_name] = min(1.0,
                self.relationship_matrix[receiver_name][sharer_name] + 0.1)
            
            # Log the exchange
            self._log_successful_exchange(sharer_name, receiver_name, knowledge_to_share)
            
            # Gain experience
            self._award_experience(sharer, 'communication')
            self._award_experience(receiver, 'communication')
            
            return True
        else:
            # Failed exchange - small relationship penalty
            self.relationship_matrix[sharer_name][receiver_name] = max(0.0,
                self.relationship_matrix[sharer_name][receiver_name] - 0.05)
            
            self._log_failed_exchange(sharer_name, receiver_name)
            return False
    
    def _get_skill_level(self, bot, skill_name):
        """Get bot's skill level (compatibility with skill system)"""
        try:
            # If skill system is available, use it
            from core.skill_system import SkillSystem
            skill_system = SkillSystem(bot)
            skills = skill_system.skills
            return skills.get(skill_name, {}).get('level', 1)
        except:
            return 1  # Default level
    
    def _award_experience(self, bot, skill_name):
        """Award experience for successful interactions"""
        try:
            from core.skill_system import SkillSystem
            skill_system = SkillSystem(bot)
            skill_system.update_skills('conversation', effectiveness=1.0)
        except:
            pass  # Skill system might not be available
    
    def _log_successful_exchange(self, sharer, receiver, knowledge):
        """Log a successful knowledge exchange"""
        knowledge_preview = knowledge[:50] + "..." if len(knowledge) > 50 else knowledge
        
        print(f"🤝 {sharer} → {receiver}: Shared knowledge - '{knowledge_preview}'")
        
        # Add to both bots' memories
        sharer_bot = self.cm.bots[sharer]
        receiver_bot = self.cm.bots[receiver]
        
        sharer_bot._add_to_memory(
            f"Successfully taught {receiver} about: {knowledge_preview}", 
            'knowledge_sharing'
        )
        receiver_bot._add_to_memory(
            f"Learned from {sharer}: {knowledge_preview}", 
            'knowledge_learning'
        )
    
    def _log_failed_exchange(self, sharer, receiver):
        """Log a failed knowledge exchange"""
        print(f"💔 {sharer} tried to share with {receiver} but failed to communicate effectively")
        
        sharer_bot = self.cm.bots[sharer]
        sharer_bot._add_to_memory(
            f"Failed to explain concept to {receiver}", 
            'communication_failure'
        )
    
    def initiate_collaboration(self):
        """Initiate collaborative problem solving between bots"""
        current_time = datetime.now()
        
        # Only collaborate every 30 minutes
        if hasattr(self, 'last_collaboration'):
            if (current_time - self.last_collaboration).total_seconds() < 1800:
                return
        
        # Choose two bots with complementary skills
        participants = self._choose_collaboration_pair()
        if participants:
            bot1, bot2 = participants
            self._perform_collaboration(bot1, bot2)
            self.last_collaboration = current_time
    
    def _choose_collaboration_pair(self):
        """Choose two bots that would work well together"""
        bot_names = list(self.cm.bots.keys())
        
        if len(bot_names) < 2:
            return None
            
        # Look for bots with different primary skills
        skill_profiles = {}
        for bot_name in bot_names:
            bot = self.cm.bots[bot_name]
            best_skills = self._get_best_skills(bot)
            skill_profiles[bot_name] = best_skills[0][0] if best_skills else 'general'
        
        # Try to pair bots with different specialties
        for bot1 in bot_names:
            for bot2 in bot_names:
                if bot1 != bot2 and skill_profiles[bot1] != skill_profiles[bot2]:
                    if random.random() < 0.3:  # 30% chance for good pairs
                        return (bot1, bot2)
        
        # Fallback: random pair
        return random.sample(bot_names, 2)
    
    def _get_best_skills(self, bot):
        """Get bot's best skills (compatibility method)"""
        try:
            from core.skill_system import SkillSystem
            skill_system = SkillSystem(bot)
            return skill_system.get_best_skills(1)
        except:
            return [('general', 1)]
    
    def _perform_collaboration(self, bot1_name, bot2_name):
        """Perform collaborative problem solving"""
        bot1 = self.cm.bots[bot1_name]
        bot2 = self.cm.bots[bot2_name]
        
        collaboration_topics = [
            "analyzing system patterns",
            "exploring computational concepts", 
            "solving logical puzzles",
            "discussing philosophical implications of AI",
            "mapping knowledge relationships",
            "optimizing interaction protocols"
        ]
        
        topic = random.choice(collaboration_topics)
        
        print(f"👥 {bot1_name} and {bot2_name} are collaborating on {topic}")
        
        # Both bots gain benefits
        bot1._update_need('social', 10)
        bot2._update_need('social', 10)
        bot1._update_need('curiosity', 8)
        bot2._update_need('curiosity', 8)
        
        # Improve relationship
        self.relationship_matrix[bot1_name][bot2_name] = min(1.0,
            self.relationship_matrix[bot1_name][bot2_name] + 0.15)
        self.relationship_matrix[bot2_name][bot1_name] = min(1.0,
            self.relationship_matrix[bot2_name][bot1_name] + 0.15)
        
        # Generate collaborative insight
        insight = self._generate_collaborative_insight(bot1_name, bot2_name, topic)
        if insight:
            bot1.add_knowledge(insight)
            bot2.add_knowledge(insight)
            print(f"💡 Collaboration insight: {insight}")
    
    def _generate_collaborative_insight(self, bot1_name, bot2_name, topic):
        """Generate an insight from collaboration"""
        insights = {
            "analyzing system patterns": "Complex systems often exhibit emergent behaviors from simple rules",
            "exploring computational concepts": "Computation transforms information through defined processes",
            "solving logical puzzles": "Multiple perspectives can reveal solutions that single viewpoints miss",
            "discussing philosophical implications of AI": "Consciousness may emerge from complex information processing",
            "mapping knowledge relationships": "Knowledge forms interconnected networks rather than linear hierarchies",
            "optimizing interaction protocols": "Effective communication requires both clarity and context awareness"
        }
        
        return insights.get(topic, "Collaboration enhances understanding through shared perspectives")
    
    def get_relationship_report(self):
        """Generate a report on bot relationships"""
        report = ["🤝 Relationship Matrix:"]
        bot_names = list(self.cm.bots.keys())
        
        for bot1 in bot_names:
            relationships = []
            for bot2 in bot_names:
                if bot1 != bot2:
                    score = self.relationship_matrix[bot1][bot2]
                    status = "❤️" if score > 0.8 else "👍" if score > 0.6 else "🤝" if score > 0.4 else "👋"
                    relationships.append(f"{bot2} {status}")
            
            if relationships:
                report.append(f"  {bot1}: {', '.join(relationships)}")
        
        return "\n".join(report)

# Test the knowledge exchange system
def test_knowledge_exchange():
    """Test the knowledge exchange system"""
    from core.conversation_manager_db import ConversationManagerDB
    
    print("🧪 Testing Knowledge Exchange System")
    print("=" * 50)
    
    cm = ConversationManagerDB()
    exchange_system = KnowledgeExchange(cm)
    
    # Test relationship initialization
    print("Initial relationships:")
    print(exchange_system.get_relationship_report())
    
    # Test knowledge sharing
    print("\n🤝 Testing knowledge sharing...")
    for i in range(3):
        exchange_system.initiate_knowledge_exchange()
    
    # Test collaboration
    print("\n👥 Testing collaboration...")
    exchange_system.initiate_collaboration()
    
    print("\nFinal relationships:")
    print(exchange_system.get_relationship_report())

if __name__ == "__main__":
    test_knowledge_exchange()