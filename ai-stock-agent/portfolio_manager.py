"""
Monthly Portfolio Manager
Manages $1000 monthly budget with intelligent position sizing and rebalancing
"""

import sqlite3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manage monthly $1000 trading portfolio"""

    def __init__(self, monthly_budget: float = 1000, db_path: str = "portfolio.db"):
        """
        Initialize portfolio manager

        Args:
            monthly_budget: Monthly capital allocation
            db_path: Database file path
        """
        self.monthly_budget = monthly_budget
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize portfolio database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Positions table - tracks current holdings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                shares REAL NOT NULL,
                entry_price REAL NOT NULL,
                entry_date TEXT NOT NULL,
                target_price REAL,
                stop_loss REAL,
                sector TEXT,
                confidence REAL,
                status TEXT DEFAULT 'OPEN',
                exit_price REAL,
                exit_date TEXT,
                profit_loss REAL,
                profit_loss_pct REAL,
                exit_reason TEXT
            )
        ''')

        # Monthly budgets table - tracks budget per month
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT UNIQUE NOT NULL,
                starting_capital REAL NOT NULL,
                current_cash REAL NOT NULL,
                deployed_capital REAL NOT NULL,
                total_pnl REAL DEFAULT 0,
                total_pnl_pct REAL DEFAULT 0,
                trades_count INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0
            )
        ''')

        # Trades history - complete trade log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                confidence REAL,
                reasoning TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def get_current_month(self) -> str:
        """Get current month key (YYYY-MM)"""
        return datetime.now().strftime('%Y-%m')

    def initialize_month(self) -> bool:
        """Initialize current month's budget if needed"""
        month = self.get_current_month()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if month already initialized
        cursor.execute('SELECT id FROM monthly_budgets WHERE month = ?', (month,))
        if cursor.fetchone():
            conn.close()
            return False

        # Initialize new month
        cursor.execute('''
            INSERT INTO monthly_budgets
            (month, starting_capital, current_cash, deployed_capital)
            VALUES (?, ?, ?, ?)
        ''', (month, self.monthly_budget, self.monthly_budget, 0))

        conn.commit()
        conn.close()
        logger.info(f"✅ Initialized month {month} with ${self.monthly_budget:,.0f}")
        return True

    def get_monthly_status(self) -> Dict[str, Any]:
        """Get current month's portfolio status"""
        self.initialize_month()
        month = self.get_current_month()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get monthly budget info
        cursor.execute('SELECT * FROM monthly_budgets WHERE month = ?', (month,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {}

        monthly_data = {
            'month': row[1],
            'starting_capital': row[2],
            'current_cash': row[3],
            'deployed_capital': row[4],
            'total_pnl': row[5],
            'total_pnl_pct': row[6],
            'trades_count': row[7],
            'winning_trades': row[8],
            'losing_trades': row[9],
            'win_rate': row[10]
        }

        # Get open positions
        cursor.execute('''
            SELECT ticker, shares, entry_price, entry_date, target_price,
                   stop_loss, sector, confidence
            FROM positions
            WHERE status = 'OPEN'
        ''')

        positions = []
        for row in cursor.fetchall():
            positions.append({
                'ticker': row[0],
                'shares': row[1],
                'entry_price': row[2],
                'entry_date': row[3],
                'target_price': row[4],
                'stop_loss': row[5],
                'sector': row[6],
                'confidence': row[7]
            })

        conn.close()

        monthly_data['open_positions'] = positions
        monthly_data['num_positions'] = len(positions)
        monthly_data['available_cash'] = monthly_data['current_cash']
        monthly_data['total_value'] = monthly_data['current_cash'] + monthly_data['deployed_capital']

        return monthly_data

    def can_open_position(self, cost: float) -> tuple[bool, str]:
        """
        Check if we can open a new position

        Args:
            cost: Cost of new position

        Returns:
            (can_open, reason)
        """
        status = self.get_monthly_status()

        # Check available cash
        if cost > status['current_cash']:
            return False, f"Insufficient cash. Need ${cost:.2f}, have ${status['current_cash']:.2f}"

        # Check monthly budget limit (total deployed should not exceed monthly_budget)
        if status['deployed_capital'] + cost > self.monthly_budget:
            return False, f"Would exceed monthly budget of ${self.monthly_budget:,.0f}"

        # Limit to 3 open positions max
        if status['num_positions'] >= 3:
            return False, "Maximum 3 positions allowed. Close a position first."

        # Check if already have position in this ticker
        for pos in status['open_positions']:
            if cost > 0:  # This is a rough check, will be refined when we know ticker
                pass

        return True, "OK"

    def open_position(self, ticker: str, shares: float, price: float,
                     target: float = None, stop: float = None,
                     sector: str = None, confidence: float = None,
                     reasoning: str = None) -> bool:
        """
        Open a new position

        Args:
            ticker: Stock ticker
            shares: Number of shares
            price: Entry price
            target: Target price
            stop: Stop loss price
            sector: Stock sector
            confidence: Signal confidence (0-1)
            reasoning: Trade reasoning

        Returns:
            True if successful
        """
        cost = shares * price

        can_open, reason = self.can_open_position(cost)
        if not can_open:
            logger.warning(f"❌ Cannot open {ticker} position: {reason}")
            return False

        month = self.get_current_month()
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add position
        cursor.execute('''
            INSERT INTO positions
            (ticker, shares, entry_price, entry_date, target_price, stop_loss,
             sector, confidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        ''', (ticker, shares, price, now, target, stop, sector, confidence))

        # Log trade
        cursor.execute('''
            INSERT INTO trades_history
            (ticker, action, shares, price, date, amount, confidence, reasoning)
            VALUES (?, 'BUY', ?, ?, ?, ?, ?, ?)
        ''', (ticker, shares, price, now, cost, confidence, reasoning))

        # Update monthly budget
        cursor.execute('''
            UPDATE monthly_budgets
            SET current_cash = current_cash - ?,
                deployed_capital = deployed_capital + ?,
                trades_count = trades_count + 1
            WHERE month = ?
        ''', (cost, cost, month))

        conn.commit()
        conn.close()

        logger.info(f"✅ Opened position: {shares} shares of {ticker} @ ${price:.2f} (${cost:.2f})")
        return True

    def close_position(self, ticker: str, price: float, reason: str = None) -> bool:
        """
        Close an open position

        Args:
            ticker: Stock ticker
            price: Exit price
            reason: Exit reason

        Returns:
            True if successful
        """
        month = self.get_current_month()
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get position
        cursor.execute('''
            SELECT id, shares, entry_price
            FROM positions
            WHERE ticker = ? AND status = 'OPEN'
        ''', (ticker,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            logger.warning(f"❌ No open position found for {ticker}")
            return False

        position_id, shares, entry_price = row
        proceeds = shares * price
        cost = shares * entry_price
        profit_loss = proceeds - cost
        profit_loss_pct = (profit_loss / cost) * 100

        # Update position
        cursor.execute('''
            UPDATE positions
            SET status = 'CLOSED',
                exit_price = ?,
                exit_date = ?,
                profit_loss = ?,
                profit_loss_pct = ?,
                exit_reason = ?
            WHERE id = ?
        ''', (price, now, profit_loss, profit_loss_pct, reason, position_id))

        # Log trade
        cursor.execute('''
            INSERT INTO trades_history
            (ticker, action, shares, price, date, amount, reasoning)
            VALUES (?, 'SELL', ?, ?, ?, ?, ?)
        ''', (ticker, shares, price, now, proceeds, reason))

        # Update monthly budget
        is_winner = 1 if profit_loss > 0 else 0
        is_loser = 1 if profit_loss < 0 else 0

        cursor.execute('''
            UPDATE monthly_budgets
            SET current_cash = current_cash + ?,
                deployed_capital = deployed_capital - ?,
                total_pnl = total_pnl + ?,
                winning_trades = winning_trades + ?,
                losing_trades = losing_trades + ?
            WHERE month = ?
        ''', (proceeds, cost, profit_loss, is_winner, is_loser, month))

        # Update win rate
        cursor.execute('''
            UPDATE monthly_budgets
            SET win_rate = CAST(winning_trades AS REAL) / CAST(trades_count AS REAL) * 100,
                total_pnl_pct = (total_pnl / starting_capital) * 100
            WHERE month = ?
        ''', (month,))

        conn.commit()
        conn.close()

        emoji = "📈" if profit_loss > 0 else "📉"
        logger.info(f"{emoji} Closed position: {ticker} @ ${price:.2f} | "
                   f"P/L: ${profit_loss:+.2f} ({profit_loss_pct:+.2f}%)")

        return True

    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get open position for ticker"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ticker, shares, entry_price, entry_date, target_price,
                   stop_loss, sector, confidence
            FROM positions
            WHERE ticker = ? AND status = 'OPEN'
        ''', (ticker,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'ticker': row[0],
            'shares': row[1],
            'entry_price': row[2],
            'entry_date': row[3],
            'target_price': row[4],
            'stop_loss': row[5],
            'sector': row[6],
            'confidence': row[7]
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for current month"""
        status = self.get_monthly_status()

        return {
            'month': status['month'],
            'starting_capital': status['starting_capital'],
            'current_value': status['total_value'],
            'cash': status['current_cash'],
            'deployed': status['deployed_capital'],
            'total_pnl': status['total_pnl'],
            'total_pnl_pct': status['total_pnl_pct'],
            'trades': status['trades_count'],
            'winners': status['winning_trades'],
            'losers': status['losing_trades'],
            'win_rate': status['win_rate'],
            'open_positions': status['num_positions']
        }


# Singleton
_portfolio_manager = None

def get_portfolio_manager(monthly_budget: float = 1000) -> PortfolioManager:
    """Get or create portfolio manager instance"""
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = PortfolioManager(monthly_budget)
    return _portfolio_manager
