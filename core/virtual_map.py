import sqlite3
import logging
from config import map_conf

class VirtualMap:
    def __init__(self, width=map_conf.MAP_WIDTH, height=map_conf.MAP_HEIGHT):
        self.width = width
        self.height = height
        self.location_types = map_conf.LOCATION_TYPES

        # Generate zoned biome map
        biome_map = self._generate_zoned_map()
        
        # Create grid with zones
        self.grid = [[self._create_location(x, y, biome_map) 
                     for y in range(height)] 
                    for x in range(width)]
        
        # Store terrain in database
        self._initialize_terrain_db()
    
    def _generate_zoned_map(self):
        """Divide map into zones with dominant biomes"""
        import random
        biome_map = [[None for _ in range(self.height)] 
                    for _ in range(self.width)]
        
        # Zone definitions: (x_range, y_range, primary_biome, secondary_biome, mix_ratio)
        zones = [
            # Forest zone - northwest
            ((0, 15), (0, 15), 'forest', 'plains', 0.8),
            
            # Plains zone - north central  
            ((15, 35), (0, 20), 'plains', 'forest', 0.7),
            
            # Mountain zone - northeast
            ((35, 50), (0, 15), 'mountain', 'forest', 0.6),
            
            # Desert zone - southwest
            ((0, 20), (15, 35), 'desert', 'plains', 0.9),
            
            # City zone - center (rare cities)
            ((20, 30), (20, 30), 'city', 'plains', 0.2),
            
            # Water zone - southeast (lake/river)
            ((40, 50), (15, 35), 'water', 'plains', 0.8),
            
            # Southern plains - bottom
            ((0, 50), (35, 50), 'plains', 'forest', 0.5),
            
            # Central transition area - mixed
            ((30, 40), (15, 25), 'plains', 'forest', 0.6),
        ]
        
        for x in range(self.width):
            for y in range(self.height):
                # Check each zone
                biome_assigned = False
                for (x1, x2), (y1, y2), primary, secondary, ratio in zones:
                    if x1 <= x < x2 and y1 <= y < y2:
                        # Use primary biome most of the time, secondary sometimes
                        biome_map[x][y] = primary if random.random() < ratio else secondary
                        biome_assigned = True
                        break
                
                # Default to plains if not in any zone
                if not biome_assigned:
                    biome_map[x][y] = 'plains'
        
        return biome_map
    
    def _create_location(self, x, y, biome_map):
        """Create location with biome from map"""
        loc_type = biome_map[x][y]
        
        return {
            'x': x,
            'y': y,
            'type': loc_type,
            'properties': self.location_types[loc_type].copy(),
            'bots_present': [],
            'events': []
        }
    
    def _initialize_terrain_db(self):
        """Store terrain in database ONLY if empty"""
        conn = sqlite3.connect('data/bot_world.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS map_terrain (
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                terrain_type TEXT NOT NULL,
                movement_cost INTEGER,
                interest REAL,
                PRIMARY KEY (x, y)
            )
        ''')
        
        # Check if table already has data
        cursor.execute('SELECT COUNT(*) FROM map_terrain')
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Table is empty - insert all cells
            print(f"Initializing terrain database with {self.width}x{self.height} cells...")
            for x in range(self.width):
                for y in range(self.height):
                    cell = self.grid[x][y]
                    cursor.execute('''
                        INSERT INTO map_terrain (x, y, terrain_type, movement_cost, interest)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (x, y, cell['type'], 
                        cell['properties']['movement_cost'],
                        cell['properties']['interest']))
            conn.commit()
            print("Terrain database initialized")
        else:
            # Load existing terrain into map.grid
            print(f"Loading existing terrain ({count} cells)...")
            cursor.execute('SELECT x, y, terrain_type FROM map_terrain')
            for row in cursor.fetchall():
                x, y = row['x'], row['y']
                terrain_type = row['terrain_type']
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.grid[x][y]['type'] = terrain_type
                    # Update properties too if needed
                    if terrain_type in self.location_types:
                        self.grid[x][y]['properties'] = self.location_types[terrain_type].copy()
        
        conn.close()
        print(f"Terrain initialized: {self.width}x{self.height} cells")
        print("Zones: Forest NW, Plains N, Mountains NE, Desert SW, City Center, Water SE")

    def load_bot_positions(self):
        """Load bot positions from database on restart"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bot_id, x, y, location_type
            FROM bot_locations 
            ORDER BY timestamp DESC
        ''')
        
        bot_positions = {}
        for row in cursor.fetchall():
            bot_id = row[0]
            # Only take the most recent position per bot
            if bot_id not in bot_positions:
                bot_positions[bot_id] = {
                    'x': row[1],
                    'y': row[2],
                    'type': row[3]
                }
        
        conn.close()
        logging.info(f"Loaded positions for {len(bot_positions)} bots from database")
        return bot_positions

    def _store_bot_location_in_db(self, bot_id, x, y, location_type):
        """Store bot location in database for dashboard"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO bot_locations 
            (bot_id, x, y, location_type, timestamp) 
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (bot_id, x, y, location_type))
        
        conn.commit()
        conn.close()

    def assign_bot_homes(self, bot_ids):
        """Assign AND SAVE home cells for bots"""
        import random
        import sqlite3
        
        # 1. Find good locations
        good_locations = []
        for x in range(self.width):
            for y in range(self.height):
                cell = self.grid[x][y]
                if cell['type'] not in ['water', 'mountain']:
                    good_locations.append((x, y))
        
        random.shuffle(good_locations)
        
        # 2. Assign to bots
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        for i, bot_id in enumerate(bot_ids):
            if i < len(good_locations):
                x, y = good_locations[i]
                
                # Update map in memory
                self.grid[x][y]['is_home'] = True
                self.grid[x][y]['home_owner'] = bot_id
                
                # Update database
                cursor.execute('''
                    UPDATE bots 
                    SET home_x = ?, home_y = ?
                    WHERE id = ?
                ''', (x, y, bot_id))
                
                logging.info(f"✅ Assigned home for bot {bot_id} at ({x},{y})")
        
        conn.commit()
        conn.close()
        
        logging.info(f"Homes assigned for {min(len(bot_ids), len(good_locations))} bots")
    
    def homeless_bots(self):
        """Return True if any bot is missing home coordinates"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM bots 
            WHERE id IN (1, 2, 3, 5) 
            AND (home_x IS NULL OR home_y IS NULL)
            LIMIT 1
        ''')
        
        missing = cursor.fetchone() is not None
        conn.close()
        
        if missing:
            logging.info("Some bots are missing home coordinates")
        else:
            logging.info("All bots have home coordinates")
        
        return missing