import re
import random
import time
from datetime import datetime

class IRCCore:
    def __init__(self, nickname, config):
        self.nickname = nickname

        if config is None:
            config = {}

        self.command_prefix = config.get('command_prefix', '!')
        
        # Mode handling
        self.supported_modes = {
            'op': '+o',
            'deop': '-o', 
            'voice': '+v',
            'devoice': '-v',
            'ban': '+b',
            'unban': '-b',
            'key': '+k',
            'limit': '+l'
        }
        
        # Custom quit messages
        self.quit_messages = config.get('quit_messages', [
            "Leaving...",
            "Goodbye!",
            "See you later!",
            "Bot out!"
        ])
        self.custom_quit = None
        
        # Auto-response patterns
        self.auto_responses = self._load_auto_responses()
        
    def _load_auto_responses(self):
        """Load auto-response patterns"""
        return {
            # Basic greetings
            r'^(hi|hello|hey)\s+{}'.format(self.nickname): [
                "Hello!",
                "Hi there!",
                "Hey!"
            ],
            r'good (morning|afternoon|evening)': [
                "Good {0}!"
            ],
            # Bot mentions
            r'{}\s*[:,-]?\s+(what|who|how|why)'.format(self.nickname): [
                "I'm a bot exploring the IRC ecosystem!",
                "I'm here to learn and interact!"
            ],
            # Channel events
            r'welcome.*{}'.format(self.nickname): [
                "Thanks! Happy to be here!"
            ]
        }
    
    def handle_message(self, user, channel, message):
        """Process incoming messages for auto-responses"""
        responses = []
        response_sets = {
            'greetings': [
            "Salut les connards !",
            "Alors, ça gicle {user} ?".format(user=user),
            "Quoi de neuf ? Toujours macroniste ?",
            "Salut!",
            "Hello toi! Mais surtout comment vas-tu {user} ?".format(user=user),
            "Ah mais c'est bien toi l'pot qu'est cap de 'm sess :)",
            "Salut {user}!".format(user=user)
        ],
            'farewell': ["Luss les loss", "Prend mon bulletin et colle le toi dans le fion", "Marre de ces petits prouts", "Je vais aller le dire à Roger il va venir te casser la gueule."],
            'thanks': ["Pas de souci ! Tu me payeras en cartouches AES mon salo", "Je suis là pour ça.", "Tu sais moi je suis un robot j'en ai rien à foutre. Je suis pas ta pute non plus."]
        }
        # Debug: print what we're checking
        #print(f"[PATTERN DEBUG] Checking: '{message}'")
        #print(f"[PATTERN DEBUG] My nickname: '{self.nickname}'")
        # Test the exact pattern
        import re
        pattern = r'^(hi|bonjour|Bonjour|lo|lu|lut|hello|hey|salut|Salut|kikooe|wesh|ça se papasse|Comment vas-tu|mais comment vas-tu|la pêche [?]|la forme [?]|celas se passy)\s+' + self.nickname
        #print(f"[PATTERN DEBUG] Pattern: {pattern}")
        #print(f"[PATTERN DEBUG] Match result: {re.search(pattern, message, re.IGNORECASE)}")
        # Test simpler patterns
        #print(f"[PATTERN DEBUG] Simple check 1 - 'hi ' + nickname: {'hi ' + self.nickname}")
        #print(f"[PATTERN DEBUG] Simple check 2 - nickname in message: {self.nickname in message}")
        #print(f"[PATTERN DEBUG] Simple check 3 - 'hi' in message: {'hi' in message.lower()}")
        
        # Check for greetings
        greeting_pattern = r'^(hi|bonjour|Bonjour|lo|lu|lut|hello|hey|salut|Salut|kikooe|wesh|ça se papasse|Comment vas-tu|mais comment vas-tu|la pêche [?]|la forme [?]|celas se passy)\s+{}'.format(self.nickname)

        if re.search(greeting_pattern, message, re.IGNORECASE):
            responses.append(random.choice(response_sets['greetings']))
        
        # Check for thanks messages
        thanks_pattern = r'^(parfait merci|ok cimer|ok merci|ah merci|Merci|merchi|merki|merci beaucoup|merci!|merci !|Merci|merci|saint cloud !|saint cloud|cimer|Cimer|cool|Thank you)\s+{}'.format(self.nickname)
        if re.search(thanks_pattern, message, re.IGNORECASE):
            responses.append(random.choice(response_sets['thanks']))

        farewell_pattern =  r'^(Laisse tomber j ai la shnek en travaux je reviendrai vous victimer|repose en paix, petite hirondelle|Part|Quit|Bon débarras !)\s+{}'.format(self.nickname)
        if re.search(farewell_pattern, message, re.IGNORECASE):
            responses.append(random.choice(response_sets['farewell']))
        
        #print(f"[IRC Core] Returning responses: {responses}")
        return responses
    
    def parse_command(self, message):
        """Parse !commands from messages"""
        if not message.startswith(self.command_prefix):
            return None
        
        parts = message[len(self.command_prefix):].strip().split()
        if not parts:
            return None
            
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    def generate_mode_command(self, mode_type, target=None, extra=None):
        """Generate MODE command string"""
        if mode_type not in self.supported_modes:
            return None
            
        mode = self.supported_modes[mode_type]
        
        if mode_type in ['op', 'deop', 'voice', 'devoice']:
            if not target:
                return None
            return f"MODE {target} {mode} {extra}" if extra else f"MODE {target} {mode}"
        
        elif mode_type in ['ban', 'unban']:
            if not target:
                return None
            return f"MODE {target} {mode} {extra}"
            
        elif mode_type == 'key':
            if not target or not extra:
                return None
            return f"MODE {target} {mode} {extra}"
            
        elif mode_type == 'limit':
            if not target or not extra:
                return None
            return f"MODE {target} {mode} {extra}"
            
        return None
    
    def get_quit_message(self, custom_msg=None):
        """Get quit message (custom, random, or provided)"""
        if custom_msg:
            return custom_msg
        elif self.custom_quit:
            return self.custom_quit
        else:
            return random.choice(self.quit_messages)
    
    def set_custom_quit(self, message):
        """Set a custom quit message"""
        self.custom_quit = message
        return f"Custom quit message set: '{message}'"


# Enhanced IRC Client with modes
class EnhancedIRCClient:
    def __init__(self, irc_core):
        self.core = irc_core
        self.connection = None
        
    def send_mode(self, target, mode_type, extra_param=None):
        """Send mode command to IRC server"""
        cmd = self.core.generate_mode_command(mode_type, target, extra_param)
        if cmd:
            self._send_raw(cmd)
            return f"Sent: {cmd}"
        return "Invalid mode command"
    
    def handle_irc_command(self, user, channel, command, args):
        """Handle !commands from users"""
        responses = []
        
        if command == "op":
            target = args[0] if args else user
            responses.append(self.send_mode(channel, 'op', target))
            
        elif command == "voice":
            target = args[0] if args else user
            responses.append(self.send_mode(channel, 'voice', target))
            
        elif command == "ban":
            if args:
                responses.append(self.send_mode(channel, 'ban', args[0]))
                
        elif command == "key":
            if len(args) >= 2:
                responses.append(self.send_mode(args[0], 'key', args[1]))
                
        elif command == "setquit":
            if args:
                msg = " ".join(args)
                responses.append(self.core.set_custom_quit(msg))
                
        elif command == "quit":
            msg = " ".join(args) if args else None
            quit_msg = self.core.get_quit_message(msg)
            self._send_raw(f"QUIT :{quit_msg}")
            responses.append(f"Quitting: {quit_msg}")
            
        elif command == "modes":
            modes = ", ".join(self.core.supported_modes.keys())
            responses.append(f"Available modes: {modes}")
        
        return responses