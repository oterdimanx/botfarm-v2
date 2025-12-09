# irc/irc_permanent_manual.py - Permanent IRC with manual control
import socket
import time
import threading
import re
import sqlite3
from datetime import datetime
from irc.irc_core import IRCCore, EnhancedIRCClient
from config import irc_conf

class PermanentManualIRC:
    def __init__(self, bot_id, server=irc_conf.IRC['servers']['efnet'][3], channel=irc_conf.IRC['connect']['channel']):
        self.bot_id = bot_id
        self.server = server
        self.port = irc_conf.IRC['connect']['port']
        self.channel = channel
        self.socket = None
        self.running = False
        self.control_thread = None

        # Load bot info
        self.bot_name = self._get_bot_name()
        self.nickname = self.bot_name.lower()

        irc_config = {
            'command_prefix':'!',
            'quit_messages': [
                'Je vais aller le dire à Roger et tu vas prendre cher.'
            ]
        }

        self.irc_core = IRCCore(self.nickname, irc_config)
        self.irc_enhanced = EnhancedIRCClient(self.irc_core)
        
    def _get_bot_name(self):
        """Get bot's actual name from database"""
        conn = sqlite3.connect('data/bot_world.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM bots WHERE id = ?', (self.bot_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "NanoBoT"
    
    def _add_irc_memory(self, event_type, details):
        try:
            """Add IRC experience to bot's memory"""
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            
            memory_text = f"[IRC {datetime.now().strftime('%H:%M')}] {event_type}: {details}"
            
            cursor.execute('''
                INSERT INTO memory (bot_id, event, event_type)
                VALUES (?, ?, ?)
            ''', (self.bot_id, memory_text, 'irc_experience'))
            
            conn.commit()
            conn.close()
            print(f"📝 {self.bot_name} remembered: {event_type}")
        except Exception as e:
            print(f"❌ _Add_irc_memory failed: {e}")
            return False

    def _get_last_seen(self, target):
        try:
            conn = sqlite3.connect('data/bot_world.db')
            cursor = conn.cursor()
            cursor.execute('SELECT event, timestamp FROM memory WHERE event LIKE (?) AND (event LIKE (?) OR event LIKE (?)) AND event_type = "irc_experience" ORDER BY ID desc LIMIT 1', ('%'+target+'%','%channel_part%','%channel_quit%'))
            result = cursor.fetchone()
            conn.close()
            return result if result else False
        except Exception as e:
            print(f"❌ get_last_seen failed: {e}")
            return False

    def connect(self):
        """Connect to IRC server"""
        print(f"🔗 Connecting {self.bot_name} to {self.server}...")
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.server, self.port))
            
            # Send registration
            self._send_raw(f"NICK {self.nickname}")
            self._send_raw(f"USER {self.nickname} 0 * :{self.bot_name}, the pretty one you'll never have")
            
            self.running = True
            
            # Start listener
            self._start_listener()
            
            # Wait for registration
            time.sleep(3)
            
            print(f"✅ {self.bot_name} connected to {self.server}!")
            self._add_irc_memory("connected", f"Connected to {self.server}")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def _send_raw(self, command):
        """Send raw IRC command"""
        if self.socket:
            try:
                full_command = f"{command}\r\n"
                self.socket.send(full_command.encode())
                #print(f"📤 {command}")
            except Exception as e:
                print(f"❌ Send failed: {e}")
    
    def join_channel(self, channel=None):
        """Join a channel"""
        target_channel = channel or self.channel
        if not target_channel.startswith('#'):
            target_channel = '#' + target_channel
            
        print(f"🚪 Joining {target_channel}...")
        self._send_raw(f"JOIN {target_channel}")
        self._add_irc_memory("channel_join", f"Joined {target_channel}")
        
        # Update current channel
        self.channel = target_channel
    
    def send_message(self, message, target=None):
        """Send message to channel or user"""
        target = target or self.channel

        self.on_message(target, self.channel, message)
        self.irc_core.handle_message(target, self.channel, message)

        self._send_raw(f"PRIVMSG {target} :{message}")
        self._add_irc_memory("message_sent", f"To {target}: {message[:50]}")
    
    def part_channel(self, channel=None, message="Leaving"):
        """Leave a channel"""
        target_channel = channel or self.channel
        if not target_channel.startswith('#'):
            target_channel = '#' + target_channel
            
        self._send_raw(f"PART {target_channel} :{message}")
        self._add_irc_memory("channel_leave", f"Left {target_channel}")

    def on_message(self, user, channel, message):
        print(f"[DEBUG] Received: {user} -> {channel}: {message}")  # Add this
        
        # 1. Auto-responses
        print(f"[DEBUG] Checking auto-responses...")  # Add this
        auto_responses = self.irc_core.handle_message(user, channel, message)
        print(f"[DEBUG] Auto-responses found: {auto_responses}")  # Add this
        
        for response in auto_responses:
            print(f"[DEBUG] Sending auto-response: {response}")  # Add this
            self.send_message(channel, response)
        
        # 2. Commands
        print(f"[DEBUG] Checking commands...")  # Add this
        parsed = self.irc_core.parse_command(message)
        if parsed:
            command, args = parsed
            print(f"[DEBUG] Command detected: {command} with args: {args}")  # Add this
            self.handle_user_command(user, channel, command, args)

    def _start_listener(self):
        """Start listener thread for PING/PONG and messages"""
        def listen():
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
                            self._handle_irc_message(line)
                            
                except socket.timeout:
                    continue
                except:
                    if self.running:
                        print("❌ Listen error - connection might be dead")
                    break
        
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()
    
    def _handle_irc_message(self, line):
        import re
        """Handle IRC messages"""
        # PING-PONG (critical!)
        if line.startswith("PING"):
            response = line.split()[1]
            self._send_raw(f"PONG {response}")
            return
        
        # Log interesting events
        #print(f"📥 {line}")
        parts = line.split()
        if len(parts) >= 4:
            user_info = parts[0]  # ":nick!user@host"
            user = user_info.split('!')[0][1:]  # "nick"
            channel = parts[2]  # "#channel"
            #message = line.split(':', 2)[-1]  # "Hello bot"
            #print(f"User: {user}, Channel: {channel}, Message: '{message}'")

        last_colon_index = line.rfind(':')
        if last_colon_index != -1:
            message = line[last_colon_index + 1:]
            #print(f"Message: '{message}'")

        seen_pattern = r'^!seen\s+@?(\S+)'
        seen_match = re.search(seen_pattern, message, re.IGNORECASE)
        if seen_match:
            target_user = seen_match.group(1)
            answer_result = self._get_last_seen(target_user)
            if answer_result:
                answer = target_user + ' a été vu pour la dernière fois le : ' + answer_result[1] + ' avec ce message : ' + answer_result[0]
                print(f"[ANSWER] returned: {answer}")
                self._send_raw(f"PRIVMSG {channel} :{answer}")
            else:
                self._send_raw(f"PRIVMSG {channel} :Désolé, je n'ai malheureusement pas vu " + target_user + " depuis un moment on dirait...C'est bon t'as pas trop la mort ?")

        if " PRIVMSG " in line and self.channel in line:
            self._add_irc_memory("heard_message", "Activity in channel #" + self.channel + " user: " + user + " => " + message)
            # Handle addressed external messages
            responses = self.irc_core.handle_message(user, channel, message)

            for response in responses:
                self._send_raw(f"PRIVMSG {channel} :{response}")

        if " JOIN " in line and self.channel in line:
            self._add_irc_memory("channel_join", line)

        elif " PART " in line and self.channel in line:
            self._add_irc_memory("channel_part", line)
        
        #elif " QUIT " in line and self.channel in line:
        #    self._add_irc_memory("channel_quit", line)
        #    print(f"[USER QUIT] returned: 📥📥📥📥📥📥📥📥📥📥📥📥📥📥")

    def start_manual_control(self):
        """Start manual control interface"""
        if not self.connect():
            return False
        
        print(f"\n🎮 MANUAL CONTROL ACTIVE for {self.bot_name}")
        print("=" * 50)
        print(f"Connected to: {self.server}")
        print(f"Current channel: {self.channel}")
        print(f"Nickname: {self.nickname}")
        print("\nAvailable commands:")
        print("  join [channel]                 - Join channel (default: #aguichor)")
        print("  msg <message>                  - Send message to current channel")
        print("  msg <channel> <message>        - Send to specific channel")
        print("  part [channel]                 - Leave channel")
        print("  status                         - Show connection status")
        print("  heartbeat                      - Send heartbeat message")
        print("  mode <target> <mode> <param>   - Set IRC modes")
        print("  setquit <message>              - Set custom quit message")
        print("  autoresponses list             - List auto-response patterns")
        print("  quit <message>                 - Quit with custom message")                       
        print("  quit                           - Disconnect")
        print("\nYou can type commands while the bot stays connected!")
        
        # Start background maintenance thread
        self._start_background_maintenance()
        
        try:
            while self.running:
                command = input(f"\n{self.bot_name}> ").strip()
                
                if not command:
                    continue
                    
                parts = command.strip().split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                if cmd == "join":
                    channel = parts[1] if len(parts) >= 2 else self.channel
                    self.join_channel(channel)
                    
                elif cmd == "msg":
                    if len(parts) >= 2:
                        # Check if first argument is a channel
                        if len(parts) >= 3 and parts[1].startswith('#'):
                            target = parts[1]
                            message = " ".join(parts[2:])
                        else:
                            target = self.channel
                            message = " ".join(parts[1:])
                        self.send_message(message, target)
                    else:
                        print("❌ Usage: msg <message> OR msg <channel> <message>")
                        
                elif cmd == "part":
                    channel = parts[1] if len(parts) >= 2 else self.channel
                    message = " ".join(parts[2:]) if len(parts) >= 3 else "Leaving"
                    self.part_channel(channel, message)
                    
                elif cmd == "status":
                    print(f"🤖 Bot: {self.bot_name}")
                    print(f"🌐 Server: {self.server}")
                    print(f"📍 Channel: {self.channel}")
                    print(f"🔗 Connected: {self.running}")
                    
                elif cmd == "heartbeat":
                    self.send_message(f"💚 {self.bot_name} heartbeat - still connected!")

                elif cmd == "mode":
                    try:
                        if len(args) >= 3:
                            target = args[0]
                            mode = args[1]
                            param = args[2]
                            print(f"DEBUG: Sending MODE {target} {mode} {param}")  # ADD THIS
                            self._send_raw(f"MODE {target} {mode} {param}")
                            print(f"Set mode {mode} on {target} for {param}")
                    except Exception as e:
                        print(f"ERROR in mode command: {e}")
                        import traceback
                        traceback.print_exc()
                
                elif cmd == "setquit":
                    msg = " ".join(args)
                    self.irc_core.set_custom_quit(msg)
                    #print(f"Custom quit message set: {msg}")
                    self._send_raw("Quit :{msg}");

                    import time;
                    time.sleep(0.5)
                
                elif cmd == "autoresponses":
                    if args and args[0] == "list":
                        print("Auto-response patterns:")
                        for pattern in self.irc_core.auto_responses.keys():
                            print(f"  {pattern}")
                    elif args and args[0] == "add":
                        # Add new auto-response
                        pass
                
                elif cmd == "help":
                    print("""
                            New commands available:
                            mode <target> <mode> <param> - Set IRC modes
                            setquit <message>            - Set custom quit message
                            autoresponses list           - List auto-response patterns
                            quit <message>               - Quit with custom message
                    """)

                elif cmd in ["quit", "exit"]:
                    break
                    
                else:
                    print("❌ Unknown command. Type 'help' to see available commands")
                    
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
        
        finally:
            self.disconnect()
    
    def _start_background_maintenance(self):
        """Start background thread to maintain connection"""
        def maintain():
            while self.running:
                time.sleep(30)  # Check every 30 seconds
                # Connection is maintained by the listener handling PING/PONG
        
        thread = threading.Thread(target=maintain, daemon=True)
        thread.start()
    
    def disconnect(self):
        """Clean disconnect"""
        print(f"🔌 Disconnecting {self.bot_name}...")
        self.running = False
        if self.socket:
            try:
                self._send_raw("QUIT :Je vais le dire à Roger il va venir te casser la bouche.")
                self.socket.close()
            except:
                pass
        print(f"✅ {self.bot_name} disconnected")
    
    def start_in_background(self):
        """Start in background (for integration with bot server)"""
        self.control_thread = threading.Thread(
            target=self.start_manual_control,
            daemon=True
        )
        self.control_thread.start()
        return self.control_thread

# Interactive launcher
def launch_permanent_manual():
    """Launch permanent manual control with bot selection"""
    import random
    
    # Get available bots
    conn = sqlite3.connect('data/bot_world.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM bots WHERE is_active = 1')
    bots = cursor.fetchall()
    conn.close()
    
    print("🎮 PERMANENT MANUAL IRC CONTROL")
    print("=" * 50)
    
    if not bots:
        print("❌ No active bots found!")
        return
    
    print("🤖 Available bots:")
    for i, (bot_id, bot_name) in enumerate(bots, 1):
        print(f"  {i}. {bot_name} (ID: {bot_id})")
    
    # Bot selection
    choice = input(f"\nSelect bot (1-{len(bots)}): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(bots)):
        print("❌ Invalid selection")
        return
        
    bot_id, bot_name = bots[int(choice) - 1]
    
    # Server selection
    servers = irc_conf.IRC['servers']['efnet']

    print("\n🌐 Available servers:")
    for i, server in enumerate(servers, 1):
        print(f"  {i}. {server}")
    
    server_choice = input(f"Select server (1-{len(servers)}): ").strip()
    if server_choice.isdigit() and 1 <= int(server_choice) <= len(servers):
        selected_server = servers[int(server_choice) - 1]
    else:
        selected_server = servers[0]
    
    # Channel selection
    default_channel = irc_conf.IRC['connect']['channel']
    channel = input(f"Channel (default {default_channel}): ").strip()
    if not channel:
        channel = default_channel
    
    print(f"\n🚀 Launching permanent manual control...")
    print(f"   Bot: {bot_name}")
    print(f"   Server: {selected_server}") 
    print(f"   Channel: {channel}")
    print(f"   You'll have full command control!")
    
    # Create and start controller
    controller = PermanentManualIRC(
        bot_id=bot_id,
        server=selected_server,
        channel=channel
    )
    
    controller.start_manual_control()

if __name__ == "__main__":
    launch_permanent_manual()