from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os
from datetime import datetime
import sys

class BetterStatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/status':
                self.send_bot_status()
            elif self.path == '/logs':
                self.send_recent_logs()
            elif self.path == '/health':
                self.send_health_check()
            elif self.path == '/':
                self.send_welcome()
            else:
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")
    
    def send_welcome(self):
        """Welcome page with available endpoints"""
        welcome = {
            "message": "🤖 Bot Server Status API",
            "endpoints": {
                "/status": "Get current bot status and metrics",
                "/logs": "Get recent server logs", 
                "/health": "Basic health check"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.send_json_response(200, welcome)
    
    def send_bot_status(self):
        """Get comprehensive bot status"""
        try:
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            
            # Get basic bot info
            cursor.execute('''
                SELECT b.id, b.name, b.fullname, b.species
                FROM bots b 
                WHERE b.is_active = 1
            ''')
            bots_data = {}
            
            for bot_id, name, fullname, species in cursor.fetchall():
                # Get needs
                cursor.execute('SELECT need_name, value FROM needs WHERE bot_id = ?', (bot_id,))
                needs = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get knowledge count
                cursor.execute('SELECT COUNT(*) FROM knowledge WHERE bot_id = ?', (bot_id,))
                knowledge_count = cursor.fetchone()[0]
                
                # Get memory count
                cursor.execute('SELECT COUNT(*) FROM memory WHERE bot_id = ?', (bot_id,))
                memory_count = cursor.fetchone()[0]
                
                bots_data[name] = {
                    'id': bot_id,
                    'fullname': fullname,
                    'species': species,
                    'needs': needs,
                    'knowledge_count': knowledge_count,
                    'memory_count': memory_count,
                    'status': 'ACTIVE'
                }
            
            # Database stats
            cursor.execute('SELECT COUNT(*) FROM memory')
            total_memories = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM knowledge') 
            total_knowledge = cursor.fetchone()[0]
            
            conn.close()
            
            # File system info
            db_size = os.path.getsize('data/bot_world.db') / (1024 * 1024)  # MB
            log_exists = os.path.exists('data/bot_server.log')
            
            status = {
                'server': {
                    'timestamp': datetime.now().isoformat(),
                    'database_size_mb': round(db_size, 2),
                    'total_memories': total_memories,
                    'total_knowledge': total_knowledge,
                    'log_file_exists': log_exists
                },
                'bots': bots_data,
                'system': {
                    'online': True,
                    'message': 'Bot server operational'
                }
            }
            
            self.send_json_response(200, status)
            
        except Exception as e:
            self.send_error(500, f"Database error: {str(e)}")
    
    def send_recent_logs(self):
        """Get recent server logs"""
        try:
            if os.path.exists('data/bot_server.log'):
                with open('data/bot_server.log', 'r') as f:
                    lines = f.readlines()
                # Last 100 lines or all if less
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                logs = ''.join(recent_lines)
            else:
                logs = "No log file found"
            
            response = {
                'timestamp': datetime.now().isoformat(),
                'log_entries': len(recent_lines) if 'recent_lines' in locals() else 0,
                'logs': logs
            }
            
            self.send_json_response(200, response)
            
        except Exception as e:
            self.send_error(500, f"Log error: {str(e)}")
    
    def send_health_check(self):
        """Simple health check"""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': os.path.exists('data/bot_world.db'),
                'log_file': os.path.exists('data/bot_server.log'),
                'server': 'running'
            }
        }
        
        self.send_json_response(200, health)
    
    def send_json_response(self, code, data):
        """Send JSON response"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow cross-origin
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        # Suppress the default log messages
        pass

def run_better_server(port=8080):
    """Run the improved status server"""
    try:
        server = HTTPServer(('0.0.0.0', port), BetterStatusHandler)
        print(f"🌐 Better Status Server running on http://0.0.0.0:{port}")
        print(f"   Access from other machines: http://192.168.1.75:{port}")
        print("   Available endpoints: /status, /logs, /health, /")
        print("   Press Ctrl+C to stop")
        server.serve_forever()
    except OSError as e:
        if e.errno == 98:
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"   python3 better_status_server.py 8081")
        else:
            raise e

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_better_server(port)