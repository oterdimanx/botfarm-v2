"""
Currency System for BotFarm
Handles bot economics, transactions, and marketplace activities
"""

import sqlite3
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

class CurrencySystem:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger('currency_system')
        
        # Economic configuration
        self.config = {
            'base_income': 10.0,           # Daily stipend
            'income_interval_hours': 24,   # How often to pay income
            'transaction_fee': 0.01,       # 1% transaction fee
            'starting_balance': 100.0,     # New bots start with this
            'upkeep_cost': 2.0,           # Daily cost for existing
            'min_balance': -50.0          # Allow some debt
        }
        
        self.initialize_tables()

    def initialize_tables(self):
        """Ensure all currency tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # These should already exist from migration, but just in case
                tables_sql = [
                    """CREATE TABLE IF NOT EXISTS bot_currency (
                        bot_id INTEGER PRIMARY KEY,
                        balance REAL DEFAULT 100.0,
                        last_income TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
                    )""",
                    """CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        from_bot INTEGER,
                        to_bot INTEGER,
                        amount REAL NOT NULL,
                        transaction_type TEXT DEFAULT 'transfer',
                        reason TEXT,
                        status TEXT DEFAULT 'completed',
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (from_bot) REFERENCES bots(id) ON DELETE SET NULL,
                        FOREIGN KEY (to_bot) REFERENCES bots(id) ON DELETE SET NULL
                    )""",
                    """CREATE TABLE IF NOT EXISTS bot_assets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bot_id INTEGER NOT NULL,
                        asset_type TEXT NOT NULL,
                        asset_name TEXT,
                        quantity REAL DEFAULT 1.0,
                        value_per_unit REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
                    )""",
                    """CREATE TABLE IF NOT EXISTS market_listings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        seller_bot_id INTEGER NOT NULL,
                        asset_type TEXT NOT NULL,
                        asset_name TEXT,
                        quantity REAL NOT NULL,
                        price_per_unit REAL NOT NULL,
                        listing_type TEXT DEFAULT 'sell',
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (seller_bot_id) REFERENCES bots(id) ON DELETE CASCADE
                    )"""
                ]
                
                for sql in tables_sql:
                    cursor.execute(sql)
                
                conn.commit()
                self.logger.info("Currency tables initialized")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")

    def get_balance(self, bot_id: int) -> float:
        """Get current balance for a bot"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT balance FROM bot_currency WHERE bot_id = ?", 
                    (bot_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else self.config['starting_balance']
        except sqlite3.Error as e:
            self.logger.error(f"Error getting balance for bot {bot_id}: {e}")
            return 0.0

    def transfer(self, from_bot: int, to_bot: int, amount: float, 
                 reason: str = "", transaction_type: str = "transfer") -> bool:
        """Transfer currency between bots"""
        if amount <= 0:
            self.logger.warning(f"Invalid transfer amount: {amount}")
            return False
            
        if from_bot == to_bot:
            self.logger.warning("Bot cannot transfer to itself")
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if sender has sufficient funds
                sender_balance = self.get_balance(from_bot)
                if sender_balance < amount:
                    self.logger.info(f"Bot {from_bot} insufficient funds: {sender_balance} < {amount}")
                    self._log_transaction(cursor, from_bot, to_bot, amount, 
                                        transaction_type, reason, "failed")
                    return False
                
                # Calculate net amount after fee
                fee = amount * self.config['transaction_fee']
                net_amount = amount - fee
                
                # Update balances
                cursor.execute(
                    "UPDATE bot_currency SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE bot_id = ?",
                    (amount, from_bot)
                )
                cursor.execute(
                    "UPDATE bot_currency SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE bot_id = ?",
                    (net_amount, to_bot)
                )
                
                # Log successful transaction
                self._log_transaction(cursor, from_bot, to_bot, amount, 
                                    transaction_type, reason, "completed")
                
                conn.commit()
                self.logger.info(f"Transfer: {from_bot} -> {to_bot} | Amount: {amount} | Reason: {reason}")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Transfer error: {e}")
            return False

    def award_currency(self, to_bot: int, amount: float, reason: str = "") -> bool:
        """Award currency to a bot (system-generated money)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update balance
                cursor.execute(
                    "INSERT OR REPLACE INTO bot_currency (bot_id, balance, updated_at) "
                    "VALUES (?, COALESCE((SELECT balance FROM bot_currency WHERE bot_id = ?), 0) + ?, CURRENT_TIMESTAMP)",
                    (to_bot, to_bot, amount)
                )
                
                # Log transaction (from_bot = NULL for system awards)
                self._log_transaction(cursor, None, to_bot, amount, "reward", reason, "completed")
                
                conn.commit()
                self.logger.info(f"Awarded {amount} to bot {to_bot} for: {reason}")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Award error: {e}")
            return False

    def charge_upkeep(self, bot_id: int) -> bool:
        """Charge daily upkeep cost to a bot"""
        upkeep_cost = self.config['upkeep_cost']
        current_balance = self.get_balance(bot_id)
        
        if current_balance - upkeep_cost >= self.config['min_balance']:
            return self.award_currency(bot_id, -upkeep_cost, "daily_upkeep")
        else:
            self.logger.info(f"Bot {bot_id} cannot afford upkeep")
            return False

    def distribute_income(self) -> Dict[str, int]:
        """Distribute daily income to all bots who haven't received it today"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Find bots that haven't received income in the last income_interval_hours
                cursor.execute("""
                    SELECT bot_id FROM bot_currency 
                    WHERE last_income <= datetime('now', ?)
                    OR last_income IS NULL
                """, (f"-{self.config['income_interval_hours']} hours",))
                
                eligible_bots = [row[0] for row in cursor.fetchall()]
                distributed = 0
                
                for bot_id in eligible_bots:
                    if self.award_currency(bot_id, self.config['base_income'], "daily_income"):
                        # Update last_income timestamp
                        cursor.execute(
                            "UPDATE bot_currency SET last_income = CURRENT_TIMESTAMP WHERE bot_id = ?",
                            (bot_id,)
                        )
                        distributed += 1
                
                conn.commit()
                self.logger.info(f"Distributed income to {distributed} bots")
                return {"distributed": distributed, "total_eligible": len(eligible_bots)}
                
        except sqlite3.Error as e:
            self.logger.error(f"Income distribution error: {e}")
            return {"distributed": 0, "total_eligible": 0}

    def _log_transaction(self, cursor, from_bot: Optional[int], to_bot: Optional[int], 
                        amount: float, transaction_type: str, reason: str, status: str):
        """Helper method to log transactions"""
        cursor.execute("""
            INSERT INTO transactions (from_bot, to_bot, amount, transaction_type, reason, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (from_bot, to_bot, amount, transaction_type, reason, status))

    # Asset Management Methods
    def add_asset(self, bot_id: int, asset_type: str, asset_name: str, 
                 quantity: float = 1.0, value_per_unit: float = 0.0) -> bool:
        """Add an asset to a bot's inventory"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bot_assets (bot_id, asset_type, asset_name, quantity, value_per_unit)
                    VALUES (?, ?, ?, ?, ?)
                """, (bot_id, asset_type, asset_name, quantity, value_per_unit))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding asset: {e}")
            return False

    def get_assets(self, bot_id: int) -> List[Dict]:
        """Get all assets owned by a bot"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT asset_type, asset_name, quantity, value_per_unit 
                    FROM bot_assets WHERE bot_id = ?
                """, (bot_id,))
                
                assets = []
                for row in cursor.fetchall():
                    assets.append({
                        'type': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'value_per_unit': row[3],
                        'total_value': row[2] * row[3]
                    })
                return assets
        except sqlite3.Error as e:
            self.logger.error(f"Error getting assets: {e}")
            return []

    # Marketplace Methods
    def create_listing(self, seller_bot_id: int, asset_type: str, asset_name: str,
                      quantity: float, price_per_unit: float, listing_type: str = "sell") -> bool:
        """Create a marketplace listing"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO market_listings 
                    (seller_bot_id, asset_type, asset_name, quantity, price_per_unit, listing_type, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+7 days'))
                """, (seller_bot_id, asset_type, asset_name, quantity, price_per_unit, listing_type))
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error creating listing: {e}")
            return False

    def get_market_listings(self, asset_type: str = None) -> List[Dict]:
        """Get active market listings"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if asset_type:
                    cursor.execute("""
                        SELECT * FROM market_listings 
                        WHERE status = 'active' AND asset_type = ?
                        ORDER BY created_at DESC
                    """, (asset_type,))
                else:
                    cursor.execute("""
                        SELECT * FROM market_listings 
                        WHERE status = 'active'
                        ORDER BY created_at DESC
                    """)
                
                listings = []
                for row in cursor.fetchall():
                    listings.append({
                        'id': row[0],
                        'seller_bot_id': row[1],
                        'asset_type': row[2],
                        'asset_name': row[3],
                        'quantity': row[4],
                        'price_per_unit': row[5],
                        'listing_type': row[6],
                        'total_price': row[4] * row[5]
                    })
                return listings
        except sqlite3.Error as e:
            self.logger.error(f"Error getting listings: {e}")
            return []

    def get_transaction_history(self, bot_id: int, limit: int = 50) -> List[Dict]:
        """Get transaction history for a bot"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM transactions 
                    WHERE from_bot = ? OR to_bot = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (bot_id, bot_id, limit))
                
                transactions = []
                for row in cursor.fetchall():
                    transactions.append({
                        'id': row[0],
                        'from_bot': row[1],
                        'to_bot': row[2],
                        'amount': row[3],
                        'type': row[4],
                        'reason': row[5],
                        'status': row[6],
                        'timestamp': row[7]
                    })
                return transactions
        except sqlite3.Error as e:
            self.logger.error(f"Error getting transaction history: {e}")
            return []

    def get_economic_stats(self) -> Dict:
        """Get overall economic statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*), SUM(balance) FROM bot_currency")
                total_bots, total_currency = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'completed'")
                total_transactions = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM market_listings WHERE status = 'active'")
                active_listings = cursor.fetchone()[0]
                
                return {
                    'total_bots': total_bots or 0,
                    'total_currency': total_currency or 0,
                    'average_balance': (total_currency or 0) / (total_bots or 1),
                    'total_transactions': total_transactions,
                    'active_listings': active_listings
                }
        except sqlite3.Error as e:
            self.logger.error(f"Error getting economic stats: {e}")
            return {}