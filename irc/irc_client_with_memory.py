# irc_client_with_memory.py - Helper to Save Bot's Memories
import socket
import time
import threading
import re
import sqlite3
from datetime import datetime
from config import irc_conf

class IRCClientWithMemory:
    def __init__(self, bot_id, server=irc_conf.IRC['servers']['efnet'][3], nickname=None, channel=irc_conf.IRC['connect']['channel']):
        self.bot_id = bot_id
        self.server = server
        self.port = irc_conf.IRC['connect']['port']
        self.nickname = nickname.lower() if nickname else f"bot{bot_id}"
        self.channel = channel
        self.socket = None
        self.running = True
        self._stay_connected = False
        
        # Load bot info from database
        self.bot_name = self._get_bot_name()
        
    def _get_bot_name(self):
        """Get bot's actual name from database"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM bots WHERE id = ?', (self.bot_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "UnknownBot"
    
    def _add_irc_memory(self, event_type, details):
        try:
            """Add IRC experience to bot's memory in the main database"""
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            
            memory_text = f"[IRC {datetime.now().strftime('%H:%M')}] {event_type}: {details}"
            
            cursor.execute('''
                INSERT INTO memory (bot_id, event, event_type)
                VALUES (?, ?, ?)
            ''', (self.bot_id, memory_text, 'irc_experience'))
            
            conn.commit()
            conn.close()
            print(f"📝 {self.bot_name}  -- remembered: {event_type}")
        except Exception as e:
            print(f"❌ _Add_irc_memory failed: {e}")
            return False
    
    def connect(self):
        """Connect to IRC and join channel"""
        print(f"🤖 {self.bot_name} connecting to IRC as {self.nickname}")
        print(f"📍 Channel: {self.channel}")
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.server, self.port))
            
            # Register
            self.send(f"NICK {self.nickname}")
            self.send(f"USER {self.nickname} 0 * :{self.bot_name} Bot")
            
            # Start listener
            self.start_listener()
            
            # Wait for registration
            time.sleep(4)
            
            # Join channel
            self.send(f"JOIN {self.channel}")
            time.sleep(5)
            
            # Record the visit
            self._add_irc_memory("channel_join", f"Joined {self.channel} as {self.nickname}")
            
            # Send greeting
            greeting = f"Hello! {self.bot_name} here, exploring the IRC world!"
            self.send_message(greeting)
            self._add_irc_memory("greeting_sent", f"Greeted users in {self.channel}")
            
            print(f"✅ {self.bot_name} is now in {self.channel}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send(self, command):
        """Send raw IRC command"""
        if self.socket:
            self.socket.send(f"{command}\r\n".encode())
            print(f"📤 {command}")
    
    def send_message(self, text):
        """Send message to channel"""
        self.send(f"PRIVMSG {self.channel} :{text}")
    
    def listen(self):
        """Listen for IRC messages and record experiences"""
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(1024).decode(errors='ignore')
                if not data:
                    break
                    
                buffer += data
                lines = buffer.split("\r\n")
                buffer = lines.pop()
                
                for line in lines:
                    line = line.strip()
                    if line:
                        print(f"📥 {line}")
                        self.handle_line(line)
                        
            except socket.timeout:
                continue
            except:
                break
    
    def handle_line(self, line):
        """Handle IRC messages and create memories"""
        # PING-PONG
        if line.startswith("PING"):
            response = line.split()[1]
            self.send(f"PONG {response}")
            return
        
        # Channel messages
        match = re.match(r":([^!]+)!.* PRIVMSG (#?\w+) :(.+)", line)
        if match:
            sender, target, message = match.groups()
            
            if target.lower() == self.channel.lower():
                print(f"💬 {sender} in {target}: {message}")
                
                # Record the interaction
                self._add_irc_memory(
                    "channel_message", 
                    f"Heard {sender} say: '{message[:50]}{'...' if len(message) > 50 else ''}'"
                )
                
                # Respond if mentioned
                if self.nickname.lower() in message.lower() or self.bot_name.lower() in message.lower():
                    response = f"Hello {sender}! {self.bot_name} here. You mentioned me!"
                    self.send_message(response)
                    self._add_irc_memory("direct_mention", f"Responded to {sender}")
    
    def start_listener(self):
        """Start listener thread"""
        thread = threading.Thread(target=self.listen, daemon=True)
        thread.start()
    
    def visit_channel(self, minutes=10):
        """Visit IRC channel for specified time"""
        print(f"⏰ {self.bot_name} visiting {self.channel} for {minutes} minutes...")
        
        try:
            for i in range(minutes * 60):
                if not self.running:
                    break
                time.sleep(1)
                
                # Periodic status updates
                if i % 120 == 0 and i > 0:  # Every 2 minutes
                    status = f"Still observing {self.channel}..."
                    self.send_message(status)
                    self._add_irc_memory("status_update", "Sent periodic check-in")
                    
        except KeyboardInterrupt:
            print(f"\n⏹️ {self.bot_name} ending visit early")
        
        # Record departure
        self._add_irc_memory("channel_leave", f"Left {self.channel} after {minutes} minutes")
        
        self.send_message(f"Leaving now. Thanks for the chat!")
        time.sleep(2)
        self.disconnect()
        
        print(f"✅ {self.bot_name}'s IRC visit completed")
    
    def disconnect(self):
        """Clean disconnect"""
        self.running = False
        if self.socket:
            try:
                self.send(f"PART {self.channel} :Goodbye!")
                self.send("QUIT :Bot signing off")
                self.socket.close()
            except:
                pass

# Test on bot computer
def test_bot_irc():
    """Test IRC with actual bot from database"""
    import random
    
    # Connect to local database
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    
    # Get all active bots
    cursor.execute('SELECT id, name FROM bots WHERE is_active = 1')
    bots = cursor.fetchall()
    conn.close()
    
    print("🤖 AVAILABLE BOTS FOR IRC:")
    for i, (bot_id, bot_name) in enumerate(bots, 1):
        print(f"  {i}. {bot_name} (ID: {bot_id})")
    
    if not bots:
        print("❌ No active bots found!")
        return
    
    choice = input(f"\nWhich bot? (1-{len(bots)}): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(bots):
        bot_id, bot_name = bots[int(choice) - 1]
        
        client = IRCClientWithMemory(
            bot_id=bot_id,
            nickname=bot_name.lower(), # Use bot's actual name in lowercase
            channel=irc_conf.IRC['connect']['channel']
        )
        
        if client.connect():
            client.visit_channel(minutes=5)
        else:
            print("❌ IRC connection failed")
    else:
        print("❌ Invalid selection")

if __name__ == "__main__":
    test_bot_irc()