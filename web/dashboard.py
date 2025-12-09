from flask import Flask, render_template, jsonify, send_from_directory, request
import sqlite3
import os
import json
from datetime import datetime
import sys

app = Flask(__name__)

# Add the parent directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Now you can import config from project_root/config.py
from config import map_conf

# 🆕 Disable caching for development
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Serve static files
@app.route('/web/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def get_db_connection():
    db_path = 'data/bot_world.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/overview')
def get_overview():
    """Get system overview data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT cycle_number, total_currency, total_transactions, timestamp FROM cycle_records ORDER BY cycle_number DESC LIMIT 1')
    latest_cycle = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as bot_count FROM bots WHERE is_active = 1")
    bot_count = cursor.fetchone()['bot_count']
    
    cursor.execute("SELECT COUNT(*) as total_cycles FROM cycle_records")
    total_cycles = cursor.fetchone()['total_cycles']
    
    conn.close()
    
    return jsonify({
        'latest_cycle': dict(latest_cycle) if latest_cycle else None,
        'bot_count': bot_count,
        'total_cycles': total_cycles
    })

@app.route('/api/debug/raw_cycles')
def debug_raw_cycles():
    """Show all cycle data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cycle_number, total_currency, total_transactions, timestamp 
        FROM cycle_records 
        ORDER BY cycle_number DESC 
        LIMIT 10
    ''')
    
    cycles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'count': len(cycles),
        'cycles': cycles,
        'current_time': datetime.now().isoformat()
    })

@app.route('/api/recent_cycles')
def get_recent_cycles():
    """Get recent cycle data for charts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT cycle_number, total_currency, total_transactions, timestamp FROM cycle_records ORDER BY cycle_number DESC LIMIT 50')
    cycles = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(cycles)

@app.route('/api/current_bot_status')
def get_current_bot_status():
    """Get current status of all bots"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT MAX(cycle_number) as max_cycle FROM cycle_bot_stats')
    max_cycle = cursor.fetchone()['max_cycle']
    
    if max_cycle:
        cursor.execute('SELECT bot_name, energy, social, curiosity, balance FROM cycle_bot_stats WHERE cycle_number = ?', (max_cycle,))
        bot_status = [dict(row) for row in cursor.fetchall()]
    else:
        bot_status = []
    
    conn.close()
    return jsonify(bot_status)

@app.route('/api/bot_personalities')
def get_bot_personalities():
    """Get bot personality traits"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT b.name, p.trait_name, p.value 
        FROM bots b 
        JOIN personality p ON b.id = p.bot_id 
        WHERE b.is_active = 1
        ORDER BY b.name, p.trait_name
    ''')
    
    personalities = {}
    for row in cursor.fetchall():
        bot_name = row['name']
        trait_name = row['trait_name']
        value = row['value']
        
        if bot_name not in personalities:
            personalities[bot_name] = {}
        personalities[bot_name][trait_name] = value
    
    conn.close()
    return jsonify(personalities)

@app.route('/api/cycles')
def get_cycles():
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM cycle_records 
        ORDER BY cycle_number DESC 
        LIMIT 10
    ''')
    cycles = cursor.fetchall()
    conn.close()
    return jsonify(cycles)

@app.route('/api/bot_stats')
def get_bot_stats():
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM cycle_bot_stats 
        WHERE cycle_number = (SELECT MAX(cycle_number) FROM cycle_bot_stats)
    ''')
    stats = cursor.fetchall()
    conn.close()
    return jsonify(stats)

@app.route('/api/bots')
def get_all_bots():
    """Get list of all bots"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, fullname, species, created_at 
        FROM bots 
        WHERE is_active = 1
        ORDER BY name
    ''')
    bots = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(bots)

@app.route('/api/bot/<int:bot_id>/knowledge')
def get_bot_knowledge(bot_id):
    """Get all knowledge for a specific bot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, fact, source, learned_at, confidence 
        FROM knowledge 
        WHERE bot_id = ?
        ORDER BY learned_at DESC
    ''', (bot_id,))
    knowledge = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(knowledge)

@app.route('/api/bot/<int:bot_id>/knowledge', methods=['POST'])
def add_bot_knowledge(bot_id):
    """Add new knowledge to a bot"""
    data = request.json
    fact = data.get('fact')
    source = data.get('source', 'dashboard')
    
    if not fact:
        return jsonify({'error': 'Fact is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO knowledge (bot_id, fact, source, confidence)
            VALUES (?, ?, ?, ?)
        ''', (bot_id, fact, source, 1.0))
        
        conn.commit()
        knowledge_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': knowledge_id})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/<int:bot_id>/knowledge/<int:knowledge_id>', methods=['DELETE'])
def delete_bot_knowledge(bot_id, knowledge_id):
    """Delete knowledge from a bot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM knowledge WHERE id = ? AND bot_id = ?', (knowledge_id, bot_id))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/<int:bot_id>/needs', methods=['PUT'])
def update_bot_needs(bot_id):
    """Update bot needs"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        for need_name, value in data.items():
            cursor.execute('''
                UPDATE needs 
                SET value = ?, last_updated = CURRENT_TIMESTAMP
                WHERE bot_id = ? AND need_name = ?
            ''', (float(value), bot_id, need_name))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather')
def get_weather():
    """Get latest weather data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT data_json, collected_at 
        FROM external_data 
        WHERE data_type = 'weather' 
        ORDER BY collected_at DESC 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        weather_data = json.loads(result['data_json'])
        
        # Extract simple info
        current = weather_data.get('current_condition', [{}])[0]
        location = weather_data.get('nearest_area', [{}])[0].get('areaName', [{}])[0].get('value', 'Unknown')
        
        return jsonify({
            'location': location,
            'temperature': current.get('temp_C', 'Unknown'),
            'condition': current.get('weatherDesc', [{}])[0].get('value', 'Unknown'),
            'humidity': current.get('humidity', 'Unknown'),
            'collected_at': result['collected_at']
        })
    
    return jsonify({'error': 'No weather data available'})

@app.route('/api/weather_history')
def get_weather_history():
    """Get weather history for chart - ALWAYS returns valid JSON"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data_json, collected_at 
            FROM external_data 
            WHERE data_type = 'weather' 
            ORDER BY collected_at DESC 
            LIMIT 24
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        weather_history = []
        for row in results:
            try:
                data = json.loads(row['data_json'])
                current = data.get('current_condition', [{}])[0]
                
                temp = current.get('temp_C', 0)
                humidity = current.get('humidity', 0)
                
                # Convert to numbers if possible
                try:
                    temp = float(temp)
                except:
                    temp = 0
                
                try:
                    humidity = float(humidity)
                except:
                    humidity = 0
                
                weather_history.append({
                    'time': row['collected_at'],
                    'temperature': temp,
                    'humidity': humidity
                })
            except json.JSONDecodeError:
                # Skip invalid JSON
                continue
        
        return jsonify(weather_history)
        
    except Exception as e:
        # Always return valid JSON, even on error
        return jsonify([])

@app.route('/api/debug/status')
def debug_status():
    """Debug endpoint to see what data is available"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check cycle_records
    cursor.execute("SELECT MAX(cycle_number) as latest_cycle, COUNT(*) as total FROM cycle_records")
    cycle_info = cursor.fetchone()
    
    # Check cycle_bot_stats  
    cursor.execute("SELECT MAX(cycle_number) as latest_bot_cycle, COUNT(*) as total FROM cycle_bot_stats")
    bot_stats_info = cursor.fetchone()
    
    # Check if bot server is running (simplified)
    cursor.execute("SELECT COUNT(*) as active_bots FROM bots WHERE is_active = 1")
    active_bots = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'cycle_records': {
            'latest_cycle': cycle_info['latest_cycle'],
            'total_records': cycle_info['total']
        },
        'cycle_bot_stats': {
            'latest_cycle': bot_stats_info['latest_bot_cycle'],
            'total_records': bot_stats_info['total']
        },
        'active_bots': active_bots['active_bots'],
        'flask_server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/debug/latest_data')
def debug_latest_data():
    """Show latest data from all tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get latest cycle data
    cursor.execute('''
        SELECT cr.cycle_number, cr.total_currency, cr.timestamp,
               COUNT(cbs.id) as bot_count
        FROM cycle_records cr
        LEFT JOIN cycle_bot_stats cbs ON cr.cycle_number = cbs.cycle_number
        WHERE cr.cycle_number = (SELECT MAX(cycle_number) FROM cycle_records)
        GROUP BY cr.cycle_number
    ''')
    
    latest_data = cursor.fetchone()
    conn.close()
    
    return jsonify(dict(latest_data) if latest_data else {})

@app.route('/api/bot/<int:bot_id>/memories')
def get_bot_memories(bot_id):
    """Get all memories for a bot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, event, event_type, timestamp 
        FROM memory 
        WHERE bot_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 500
    ''', (bot_id,))
    
    memories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(memories)

@app.route('/api/bot/<int:bot_id>/memories/<event_type>')
def get_bot_memories_by_type(bot_id, event_type):
    """Get memories of specific type for a bot"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, event, event_type, timestamp
        FROM memory 
        WHERE bot_id = ? AND event_type = ? 
        ORDER BY timestamp DESC 
        LIMIT 500
    ''', (bot_id, event_type))
    
    memories = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify(memories)

@app.route('/manage')
def manage():
    """Bot management interface"""
    return render_template('manage.html')

@app.route('/')
def dashboard():
    """Home page - redirect to dashboard"""
    return render_template('index.html')

@app.route('/api/map/state')
def get_map_state():
    """Get map state from database only"""
    from config import map_conf
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all bot locations
    cursor.execute('''
        SELECT bot_id, x, y, location_type, timestamp 
        FROM bot_locations 
        ORDER BY timestamp DESC
        LIMIT 500
    ''')
    
    bot_locations = {}
    for row in cursor.fetchall():
        bot_locations[row['bot_id']] = {
            'x': row['x'],
            'y': row['y'],
            'location_type': row['location_type'],
            'last_update': row['timestamp']
        }
    
    conn.close()
    
    # Return data for dashboard
    return jsonify({
        'bots': bot_locations,
        'map_info': {
            'width': map_conf.MAP_WIDTH,  # Hardcode or store in config
            'height': map_conf.MAP_HEIGHT
        }
    })

@app.route('/api/map/interactions/recent')
def get_recent_interactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT bot_id, other_bots, location_x, location_y, location_type, timestamp
        FROM bot_interactions
        WHERE timestamp > datetime('now', '-120 hours')
        ORDER BY timestamp DESC
        LIMIT 100
    ''')
    
    interactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(interactions)

@app.route('/map')
def map_page():
    """Main map visualization page"""
    return render_template('map.html')

@app.route('/api/map/data')
def map_data():
    """Get all data needed for map visualization"""
    from config import map_conf
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get bot locations
        cursor.execute('''
            SELECT b.bot_id, b.x, b.y, b.location_type, b.timestamp,
                bots.name as bot_name, bs.description as description,
                bots.home_x, bots.home_y
            FROM bot_locations b
            LEFT JOIN bots ON b.bot_id = bots.id
            LEFT JOIN bot_status bs ON b.bot_id = bs.bot_id
            ORDER BY b.timestamp DESC
        ''')
        
        bots = []
        bot_homes = []
        for row in cursor.fetchall():
            bots.append({
                'id': row['bot_id'],
                'name': row['bot_name'] or f"Bot {row['bot_id']}",
                'x': row['x'],
                'y': row['y'],
                'home_x' : row['home_x'],
                'home_y' : row['home_y'],
                'type': row['location_type'],
                'status': row['description'],
                'last_seen': row['timestamp']
            })
            bot_homes.append({
                'id': row['bot_id'],
                'name': row['bot_name'] or f"Bot {row['bot_name']}",
                'x' : row['home_x'],
                'y' : row['home_y'],
                'type': row['location_type']
            })
        
        # Get recent interactions
        cursor.execute('''
            SELECT location_x, location_y, location_type, 
                GROUP_CONCAT(bot_id) as bot_ids, 
                MAX(timestamp) as last_interaction
            FROM bot_interactions
            WHERE timestamp > datetime('now', '-120 hour')
            GROUP BY location_x, location_y, location_type
            LIMIT 100
        ''')
        
        interactions = []
        for row in cursor.fetchall():
            interactions.append({
                'x': row['location_x'],
                'y': row['location_y'],
                'type': row['location_type'],
                'bot_ids': row['bot_ids'].split(',') if row['bot_ids'] else [],
                'last_interaction': row['last_interaction']
            })
        
        conn.close()
        
        return jsonify({
            'bots': bots,
            'interactions': interactions,
            'bot_homes': bot_homes,
            'map_info': {
                'width': map_conf.MAP_WIDTH,
                'height': map_conf.MAP_HEIGHT,
                'cell_size': map_conf.CELL_SIZE
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }),500

@app.route('/api/bot/<int:bot_id>/move-history')
def get_bot_move_history(bot_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT from_x, from_y, to_x, to_y, 
               from_location_type, to_location_type,
               timestamp
        FROM bot_move_history
        WHERE bot_id = ?
        ORDER BY timestamp DESC
        LIMIT 200
    ''', (bot_id,))
    
    moves = []
    for row in cursor.fetchall():
        moves.append({
            'from': {
                'x': row[0], 
                'y': row[1],
                'type': row[4]  # from_location_type
            },
            'to': {
                'x': row[2], 
                'y': row[3],
                'type': row[5]  # to_location_type
            },
            'timestamp': row[6]
        })
    
    conn.close()
    return jsonify({'bot_id': bot_id, 'moves': moves})

@app.route('/api/map/terrain')
def get_map_terrain():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT x, y, terrain_type 
        FROM map_terrain 
        ORDER BY x, y
    ''')
    
    terrain = []
    for row in cursor.fetchall():
        terrain.append({
            'x': row[0],
            'y': row[1],
            'type': row[2]
        })
    
    conn.close()
    return jsonify({'terrain': terrain})

@app.route('/api/config')
def get_config():
    """Expose Python config to JavaScript"""
    from config import map_conf  # Import your config module
    
    return jsonify({
        'map': {
            'width': map_conf.MAP_WIDTH,
            'height': map_conf.MAP_HEIGHT,
            'cell_size': map_conf.CELL_SIZE,
        },
        'colors': {
            'terrain': map_conf.TERRAIN_COLORS,
            'bots': getattr(map_conf, 'BOT_COLORS', {}),  # Use getattr for optional
        },
        # Add any other config values JavaScript needs
    })

# Airport API endpoints
@app.route('/api/airports')
def get_airports():
    """Get all airports"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, x, y, name, fee, capacity, destinations, queue, last_departure
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
            'queue': json.loads(row[7]) if row[7] else [],
            'last_departure': row[8]
        })
    
    conn.close()
    return jsonify(airports)

@app.route('/api/bot/<int:bot_id>/use_airport/<int:airport_id>', methods=['POST'])
def use_airport(bot_id, airport_id):
    """Bot attempts to use an airport"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get bot money
    cursor.execute('SELECT balance FROM bot_currency WHERE bot_id = ?', (bot_id,))
    bot_money = cursor.fetchone()[0]
    
    # Get airport fee
    cursor.execute('SELECT fee, queue FROM airports WHERE id = ?', (airport_id,))
    airport = cursor.fetchone()
    
    if not airport:
        conn.close()
        return jsonify({'error': 'Airport not found'}), 404
    
    fee, queue_json = airport
    queue = json.loads(queue_json) if queue_json else []
    
    if bot_money < fee:
        conn.close()
        return jsonify({'error': 'Insufficient funds'}), 400
    
    # Add bot to queue
    if bot_id not in queue:
        queue.append(bot_id)
        cursor.execute(
            'UPDATE airports SET queue = ? WHERE id = ?',
            (json.dumps(queue), airport_id)
        )
        
        # Deduct money from bot
        cursor.execute(
            'UPDATE bot_currency SET balance = balance - ? WHERE bot_id = ?',
            (fee, bot_id)
        )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': f'Bot {bot_id} added to airport queue',
        'position_in_queue': len(queue)
    })

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🚀 Starting Bot Farm Dashboard...")
    print("📊 Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)




