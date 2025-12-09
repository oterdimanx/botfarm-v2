import json
import random
import sqlite3
from datetime import datetime, timedelta
from math import sqrt
import logging

class AirportSystem:
    def __init__(self, db_path='data/bot_world.db'):
        self.db_path = db_path
        self.airports = self.load_airports()
        self.logger = logging.getLogger('airport_system')

    def process_departures(self):
        """Process airport queues - move bots from queue to destination"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all airports
        cursor.execute('SELECT id, queue, capacity, destinations, fee FROM airports')
        all_airports = cursor.fetchall()
        
        for airport_id, queue_json, capacity, dest_json, fee in all_airports:
            queue = json.loads(queue_json) if queue_json else []
            destinations = json.loads(dest_json) if dest_json else []
            
            if not queue or not destinations:
                continue
            
            # Process up to capacity
            to_process = min(len(queue), capacity)
            
            for _ in range(to_process):
                bot_id = queue.pop(0)
                
                # Select random destination
                dest_id = random.choice(destinations)
                
                # Get destination coordinates
                cursor.execute('SELECT x, y FROM airports WHERE id = ?', (dest_id,))
                dest = cursor.fetchone()
                
                if dest:
                    # Teleport bot
                    cursor.execute(
                        'UPDATE bot_locations SET x = ?, y = ? WHERE bot_id = ?',
                        (dest[0], dest[1], bot_id)
                    )
                    
                    # Log the flight
                    cursor.execute('''
                        INSERT INTO memory (bot_id, event_type, event)
                        VALUES (?, ?, ?)
                    ''', (bot_id, 'airport_travel', 
                        f"Flew from airport {airport_id} to {dest_id} for ${fee}"))
                    
                    # Option B: Just print/log (simplest)
                    print(f"Bot {bot_id} flew from airport {airport_id} to {dest_id}")
            
            # Update queue in database
            cursor.execute(
                'UPDATE airports SET queue = ?, last_departure = ? WHERE id = ?',
                (json.dumps(queue), datetime.now().isoformat(), airport_id)
            )
        
        conn.commit()
        conn.close()
        return True
    
    def add_airport_connection(self, airport1_id, airport2_id):
        """Add bidirectional connection between airports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for airport_id, other_id in [(airport1_id, airport2_id), (airport2_id, airport1_id)]:
            cursor.execute('SELECT destinations FROM airports WHERE id = ?', (airport_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                destinations = json.loads(result[0])
                if other_id not in destinations:
                    destinations.append(other_id)
            else:
                destinations = [other_id]
            
            cursor.execute(
                'UPDATE airports SET destinations = ? WHERE id = ?',
                (json.dumps(destinations), airport_id)
            )
        
        conn.commit()
        conn.close()

    def load_airports(self):
        """Load all airports from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, x, y, name, fee, capacity, destinations, queue
            FROM airports
        ''')
        
        airports = []
        for row in cursor.fetchall():
            airports.append({
                'id': row[0],
                'x': row[1],
                'y': row[2],
                'name': row[3],
                'fee': row[4],
                'capacity': row[5],
                'destinations': json.loads(row[6]) if row[6] else [],
                'queue': json.loads(row[7]) if row[7] else []
            })
        
        conn.close()
        return airports
    
    def calculate_distance(self, x1, y1, x2, y2):
        """Calculate Euclidean distance between two points"""
        return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def find_nearest_airport(self, x, y, max_distance=20):
        """Find the nearest airport within max_distance"""
        nearest = None
        min_dist = float('inf')
        
        for airport in self.airports:
            dist = self.calculate_distance(x, y, airport['x'], airport['y'])
            if dist < min_dist and dist <= max_distance:
                min_dist = dist
                nearest = airport
        
        return nearest
    
    def bot_wants_to_go_home(self, bot, home_x, home_y):
        """Check if bot needs to go home and can afford airport"""
        distance_home = self.calculate_distance(bot['x'], bot['y'], home_x, home_y)
        
        # Bot attributes (adjust based on your bot structure)
        energy = bot.get('energy', 100)
        health = bot.get('health', 100)
        money = bot.get('money', 0)
        
        # Urgency factors (0-3 scale)
        urgency = (
            (energy < 20) * 3 +      # Low energy = urgent
            (health < 30) * 2 +       # Low health = urgent  
            (distance_home > 50) * 1  # Far from home = somewhat urgent
        )
        
        if urgency >= 3 and money >= 100:  # Threshold
            nearest_airport = self.find_nearest_airport(bot['x'], bot['y'])
            if nearest_airport:
                return {
                    'action': 'use_airport',
                    'airport_id': nearest_airport['id'],
                    'airport_name': nearest_airport['name'],
                    'cost': nearest_airport['fee'],
                    'distance_to_airport': self.calculate_distance(
                        bot['x'], bot['y'], 
                        nearest_airport['x'], nearest_airport['y']
                    )
                }
        return None
    
    def add_to_queue(self, airport_id, bot_id):
        """Add bot to airport queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current queue
        cursor.execute('SELECT queue FROM airports WHERE id = ?', (airport_id,))
        result = cursor.fetchone()
        queue = json.loads(result[0]) if result and result[0] else []
        
        # Add bot if not already in queue
        if bot_id not in queue:
            queue.append(bot_id)
            cursor.execute(
                'UPDATE airports SET queue = ? WHERE id = ?',
                (json.dumps(queue), airport_id)
            )
        
        conn.commit()
        conn.close()
        
        # Update in-memory cache
        for airport in self.airports:
            if airport['id'] == airport_id:
                if bot_id not in airport['queue']:
                    airport['queue'].append(bot_id)
                break
    
    def process_airport_queue(self, get_bot_func, update_bot_func, log_event_func):
        """Move bots through airports each cycle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for airport in self.airports:
            if airport['queue'] and len(airport['departures']) < airport['capacity']:
                # Process up to capacity
                for _ in range(min(airport['capacity'], len(airport['queue']))):
                    bot_id = airport['queue'].pop(0)
                    
                    # Get bot from database
                    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
                    bot_row = cursor.fetchone()
                    
                    if bot_row:
                        # Create bot dict (adjust column indices based on your schema)
                        bot = {
                            'id': bot_row[0],
                            'name': bot_row[1],
                            'x': bot_row[2],
                            'y': bot_row[3],
                            'money': bot_row.get('money', 0)  # Adjust column name
                        }
                        
                        if bot['money'] >= airport['fee']:
                            # Deduct money
                            new_money = bot['money'] - airport['fee']
                            cursor.execute(
                                'UPDATE bots SET money = ? WHERE id = ?',
                                (new_money, bot_id)
                            )
                            
                            # Select destination
                            if airport['destinations']:
                                dest_id = random.choice(airport['destinations'])
                                
                                # Get destination airport
                                cursor.execute(
                                    'SELECT x, y, name FROM airports WHERE id = ?',
                                    (dest_id,)
                                )
                                dest_result = cursor.fetchone()
                                
                                if dest_result:
                                    # Teleport bot
                                    cursor.execute(
                                        'UPDATE bots SET x = ?, y = ? WHERE id = ?',
                                        (dest_result[0], dest_result[1], bot_id)
                                    )
                                    
                                    # Log event
                                    if log_event_func:
                                        log_event_func(
                                            f"Bot {bot['name']} ({bot_id}) "
                                            f"flew from {airport['name']} to {dest_result[2]}"
                                        )
            
            # Update queue in database
            cursor.execute(
                'UPDATE airports SET queue = ?, last_departure = ? WHERE id = ?',
                (json.dumps(airport['queue']), datetime.now().isoformat(), airport['id'])
            )
        
        conn.commit()
        conn.close()
    
    def create_airport(self, x, y, name, fee=100, capacity=5):
        """Create a new airport"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO airports (x, y, name, fee, capacity, destinations, queue)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (x, y, name, fee, capacity, json.dumps([]), json.dumps([])))
        
        airport_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Add to cache
        self.airports.append({
            'id': airport_id,
            'x': x,
            'y': y,
            'name': name,
            'fee': fee,
            'capacity': capacity,
            'destinations': [],
            'queue': []
        })
        
        return airport_id
    
    def add_destination(self, airport_id, destination_id):
        """Add a destination route between airports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current destinations
        cursor.execute('SELECT destinations FROM airports WHERE id = ?', (airport_id,))
        result = cursor.fetchone()
        destinations = json.loads(result[0]) if result and result[0] else []
        
        if destination_id not in destinations:
            destinations.append(destination_id)
            cursor.execute(
                'UPDATE airports SET destinations = ? WHERE id = ?',
                (json.dumps(destinations), airport_id)
            )
        
        conn.commit()
        conn.close()
        
        # Update cache
        for airport in self.airports:
            if airport['id'] == airport_id:
                if destination_id not in airport['destinations']:
                    airport['destinations'].append(destination_id)
                break
    
    def get_airport_stats(self, airport_id):
        """Get statistics for an airport"""
        for airport in self.airports:
            if airport['id'] == airport_id:
                return {
                    'id': airport['id'],
                    'name': airport['name'],
                    'location': (airport['x'], airport['y']),
                    'fee': airport['fee'],
                    'capacity': airport['capacity'],
                    'queue_length': len(airport['queue']),
                    'destinations': len(airport['destinations']),
                    'revenue_today': 0  # You could track this
                }
        return None
    
    def auto_assign_bots_to_airports(self):
        """Automatically add bots to airports if they need to go home urgently"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        try:
            # Get bots far from home with money
            cursor.execute('''
                SELECT id, bl.x, bl.y, home_x, home_y, c.balance 
                FROM bots 
                LEFT JOIN bot_locations bl ON bots.id = bl.bot_id
                LEFT JOIN bot_currency c ON bots.id = c.bot_id
                WHERE c.balance > 100 OR c.balance IS NULL
            ''')
            
            for bot_id, x, y, home_x, home_y, balance in cursor.fetchall():
                # Calculate distance to home
                distance = ((home_x - x) ** 2 + (home_y - y) ** 2) ** 0.5
                
                if distance > 40 and balance > 100:  # Far from home
                    # Find nearest airport
                    cursor.execute('''
                        SELECT id, fee, (ABS(x - ?) + ABS(y - ?)) as dist
                        FROM airports 
                        ORDER BY dist LIMIT 1
                    ''', (x, y))
                    
                    nearest = cursor.fetchone()
                    if nearest and balance >= nearest[1]:
                        # Add to queue
                        airport_id, fee, dist = nearest
                        cursor.execute('SELECT queue FROM airports WHERE id = ?', (airport_id,))
                        queue_json = cursor.fetchone()[0]
                        queue = json.loads(queue_json) if queue_json else []
                        
                        if bot_id not in queue:
                            queue.append(bot_id)
                            cursor.execute(
                                'UPDATE airports SET queue = ? WHERE id = ?',
                                (json.dumps(queue), airport_id)
                            )
                            cursor.execute(
                                'UPDATE bot_currency SET balance = balance - ? WHERE bot_id = ?',
                                (fee, bot_id)
                            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            self.logger.error(f"auto_assign_bots_to_airports error: {e}")
            import traceback
            traceback.print_exc()