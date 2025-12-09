from datetime import datetime
import logging
import sqlite3

class BotTraveler:
    def __init__(self, bot_id, map_instance, bot_object=None, start_x=None, start_y=None):
        self.bot_id = bot_id
        self.map = map_instance
        self.x, self.y = self._random_start_position()
        self.destination = None
        self.bot = bot_object
        self.travelers = {}

        # Use saved position if provided, otherwise random
        if start_x is not None and start_y is not None:
            self.x, self.y = start_x, start_y
        else:
            self.x, self.y = self._random_start_position()

        self.last_interaction_time = 0  # Track when bots last interacted
        self.energy = self._load_energy()
        self.curiosity = self._load_curiosity()
        # Place on map
        self._place_on_map()
    
    def _load_energy(self):
        """Get current energy from needs table"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM needs WHERE need_name = "energy" AND bot_id = ?', (self.bot_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 100

    def _load_curiosity(self):
        """Get current curiosity from needs table"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM needs WHERE need_name = "curiosity" AND bot_id = ?', (self.bot_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 100

    def _place_on_map(self):
        """Add bot to map grid at its position"""
        if 0 <= self.x < self.map.width and 0 <= self.y < self.map.height:
            self.map.grid[self.x][self.y]['bots_present'].append(self.bot_id)

    def can_interact(self, current_time):
        """Check if bot can interact (cooldown)"""
        return current_time - self.last_interaction_time > 1800  # 1800 seconds cooldown

    def _random_start_position(self):
        """Place bot at random location"""
        import random
        return random.randint(0, self.map.width-1), random.randint(0, self.map.height-1)
    
    def decide_movement(self, has_to_go_home=False, home_x_axis=0, home_y_axis=0):
        """Decide where to move based on curiosity and energy"""
        try:
            if self.energy < 10:
                return None  # Too tired to move
            # Sometimes return home (when tired or curious low)
            if self.energy < 30 or self.curiosity < 0.3 or has_to_go_home == True:
                if self._distance_to_home() > 5 or has_to_go_home == True:  # Far from home
                    return self._move_toward_home(home_x_axis,home_y_axis)
            # Higher curiosity = more likely to explore far away
            import random
            if random.random() < self.curiosity:
                # Explore new area
                directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (-1,-1), (1,1), (-1,1), (1,-1)]
                dx, dy = random.choice(directions)
                new_x = self.x + dx
                new_y = self.y + dy
                
                # Check bounds
                if 0 <= new_x < self.map.width and 0 <= new_y < self.map.height:
                    movement_cost = self.map.grid[new_x][new_y]['properties']['movement_cost']
                    if self.energy >= movement_cost:
                        self.energy -= movement_cost
                        return new_x, new_y
            
            return None  # Stay put
        except Exception as e:
            logging.error(f"❌ decide movement (BotTraveler) failed: {e}")
            return False
    
    def move_to(self, new_x, new_y):
        """Execute movement"""
        # Remove from current location
        current_loc = self.map.grid[self.x][self.y]
        if self.bot_id in current_loc['bots_present']:
            current_loc['bots_present'].remove(self.bot_id)
        
        # Add to new location
        new_loc = self.map.grid[new_x][new_y]
        new_loc['bots_present'].append(self.bot_id)
        
        # Update position and consume energy
        movement_cost = new_loc['properties']['movement_cost']
        self.energy -= movement_cost
        self.x, self.y = new_x, new_y
        
        # Gain interest from new location
        location_interest = new_loc['properties']['interest']
        self.curiosity = min(1.0, self.curiosity + location_interest * 0.1)
        
        return new_loc
    
    def _distance_to_home(self):
        if not hasattr(self, 'home_x'):
            return 0
        return abs(self.x - self.home_x) + abs(self.y - self.home_y)
    
    def _move_toward_home(self,home_x_axis,home_y_axis):
        """Return a move direction toward home"""
        if self.x < home_x_axis:
            return (self.x + 1, self.y)
        elif self.x > home_x_axis:
            return (self.x - 1, self.y)
        elif self.y < home_y_axis:
            return (self.x, self.y + 1)
        elif self.y > home_y_axis:
            return (self.x, self.y - 1)
        return None  # Already home

    def update_bot_energy(self):
        """Not to be confused with bot_server.py update_bot_energy"""
        try:
            print(f"✅✅✅✅✅ update_bot_energy ✅✅✅✅✅")
            for traveler in self.travelers.values():
                # Extra energy restoration at home
                if traveler.x == traveler.home_x and traveler.y == traveler.home_y:
                    energy_restore = 85  # Fast rest at home
                    memory = "Resting comfortably at home"
                else:
                    energy_restore = 10   # Normal rest
                    memory = "Resting"
                
                traveler.energy = min(100, traveler.energy + energy_restore)
                
                traveler._add_to_memory(memory, 'rest')
                traveler._update_need('energy', self.needs['energy'] + energy_restore)
                traveler.add_energy(energy_restore)

        except Exception as e:
            print(f"❌ update_bot_energy failed: {e}")
            return False

    def update_one_bot_energy(self, bot_id):
        try:
            energy_restore = 40
            print(f"✅✅✅✅✅ update_one_bot_energy {bot_id} => {energy_restore} ✅✅✅✅✅")
            self.add_energy_for_one_bot(energy_restore,bot_id)

        except Exception as e:
            print(f"❌ update_one_bot_energy failed: {e}")
            return False

    def use_energy(self, amount):
        """Use energy and update both memory AND database"""
        self.energy = max(0, self.energy - amount)
        
        # SYNC TO DATABASE
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE needs SET value = ?, updated_at = ? WHERE need_name = "energy" AND bot_id = ?',
            (self.energy, datetime.date, self.bot_id)
        )
        conn.commit()
        conn.close()
        
        return self.energy
    
    def add_energy(self, amount):
        """Add energy and sync to database"""
        self.energy = min(100, self.energy + amount)
        
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE needs SET value = ? WHERE need_name = "energy" AND bot_id = ?',
            (self.energy, self.bot_id)
        )
        conn.commit()
        conn.close()
        
        return self.energy
    
    def add_energy_for_one_bot(self, amount, bot_id):
        """Add energy and sync to database"""
        from datetime import datetime
        self.energy = min(100, self.energy + amount)
        if(not self.bot_id):
            self.bot_id = bot_id
        
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE needs SET value = ?, last_updated = ? WHERE need_name = "energy" AND bot_id = ?',
            (self.energy, datetime.now().isoformat(), self.bot_id)
        )
        conn.commit()
        conn.close()
        
        return self.energy

    def bot_sweet_home(self, bot_id):
        """Mark Home Return to database and Update Bot Status History"""
        from datetime import datetime
        if(not self.bot_id):
            self.bot_id = bot_id
        
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE bot SET last_seen_home = ? WHERE bot_id = ?',
            (datetime.now(), self.bot_id)
        )
        conn.commit()
        conn.close()