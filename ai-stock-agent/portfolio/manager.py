"""
Portfolio and Budget Manager.
Tracks monthly investment budget, positions, and enforces spending limits.
"""

import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
import sys
from decimal import Decimal

sys.path.append(str(Path(__file__).parent.parent))
from app.config import PORTFOLIO_DB_PATH, MONTHLY_BUDGET

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manages investment portfolio, budget tracking, and position logging."""

    def __init__(self, db_path: Path = PORTFOLIO_DB_PATH):
        """
        Initialize the Portfolio Manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Budget tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_budget (
                year_month TEXT PRIMARY KEY,
                total_budget REAL,
                spent REAL,
                remaining REAL,
                last_reset TIMESTAMP
            )
        """)

        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                amount REAL NOT NULL,
                confidence REAL,
                decision_date TIMESTAMP,
                year_month TEXT,
                reasoning TEXT,
                status TEXT DEFAULT 'open'
            )
        """)

        # Notifications log (prevent duplicates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                decision TEXT,
                confidence REAL,
                suggested_amount REAL,
                notification_date TIMESTAMP,
                year_month TEXT,
                UNIQUE(ticker, year_month, notification_date)
            )
        """)

        # Trade history for backtesting
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT,  -- BUY, SELL, HOLD
                amount REAL,
                price REAL,
                confidence REAL,
                trade_date TIMESTAMP,
                reasoning TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Portfolio database initialized")

    def _get_current_year_month(self) -> str:
        """Get current year-month key (e.g., '2024-01')."""
        return datetime.now().strftime('%Y-%m')

    def get_budget_status(self) -> Dict[str, float]:
        """
        Get current month's budget status.

        Returns:
            Dictionary with total, spent, and remaining budget
        """
        year_month = self._get_current_year_month()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT total_budget, spent, remaining FROM monthly_budget WHERE year_month = ?",
            (year_month,)
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "total": result[0],
                "spent": result[1],
                "remaining": result[2]
            }
        else:
            # Initialize new month
            return self._reset_monthly_budget()

    def _reset_monthly_budget(self) -> Dict[str, float]:
        """
        Reset budget for new month.

        Returns:
            Budget status dictionary
        """
        year_month = self._get_current_year_month()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO monthly_budget (year_month, total_budget, spent, remaining, last_reset)
            VALUES (?, ?, ?, ?, ?)
        """, (year_month, MONTHLY_BUDGET, 0.0, MONTHLY_BUDGET, datetime.now()))

        conn.commit()
        conn.close()

        logger.info(f"Reset monthly budget for {year_month}: ${MONTHLY_BUDGET}")

        return {
            "total": MONTHLY_BUDGET,
            "spent": 0.0,
            "remaining": MONTHLY_BUDGET
        }

    def can_invest(self, amount: float) -> bool:
        """
        Check if investment amount is within remaining budget.

        Args:
            amount: Proposed investment amount

        Returns:
            True if investment is affordable, False otherwise
        """
        budget = self.get_budget_status()
        can_afford = amount <= budget["remaining"]

        if not can_afford:
            logger.warning(
                f"Investment of ${amount:.2f} exceeds remaining budget of ${budget['remaining']:.2f}"
            )

        return can_afford

    def record_investment(
        self,
        ticker: str,
        amount: float,
        confidence: float,
        reasoning: str = ""
    ) -> bool:
        """
        Record a new investment and update budget.

        Args:
            ticker: Stock ticker symbol
            amount: Investment amount
            confidence: Decision confidence score
            reasoning: Explanation for the investment

        Returns:
            True if successful, False otherwise
        """
        if not self.can_invest(amount):
            logger.error(f"Cannot record investment: insufficient budget")
            return False

        year_month = self._get_current_year_month()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Record position
            cursor.execute("""
                INSERT INTO positions (ticker, amount, confidence, decision_date, year_month, reasoning, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ticker, amount, confidence, datetime.now(), year_month, reasoning, 'open'))

            # Update budget
            budget = self.get_budget_status()
            new_spent = budget["spent"] + amount
            new_remaining = budget["total"] - new_spent

            cursor.execute("""
                UPDATE monthly_budget
                SET spent = ?, remaining = ?
                WHERE year_month = ?
            """, (new_spent, new_remaining, year_month))

            conn.commit()
            logger.info(f"Recorded investment: {ticker} ${amount:.2f} (Confidence: {confidence:.2%})")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error recording investment: {str(e)}")
            return False

        finally:
            conn.close()

    def log_notification(
        self,
        ticker: str,
        decision: str,
        confidence: float,
        suggested_amount: float
    ) -> bool:
        """
        Log that a notification was sent (prevents duplicates).

        Args:
            ticker: Stock ticker
            decision: Decision type (BUY/HOLD/SELL)
            confidence: Confidence score
            suggested_amount: Suggested investment amount

        Returns:
            True if logged, False if duplicate
        """
        year_month = self._get_current_year_month()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO notifications (ticker, decision, confidence, suggested_amount, notification_date, year_month)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ticker, decision, confidence, suggested_amount, datetime.now(), year_month))

            conn.commit()
            logger.info(f"Logged notification for {ticker}")
            return True

        except sqlite3.IntegrityError:
            # Duplicate notification
            logger.info(f"Duplicate notification for {ticker} in {year_month}, skipping")
            return False

        except Exception as e:
            logger.error(f"Error logging notification: {str(e)}")
            return False

        finally:
            conn.close()

    def get_positions(self, status: str = 'open') -> List[Dict]:
        """
        Get all positions with specified status.

        Args:
            status: Position status ('open', 'closed', or 'all')

        Returns:
            List of position dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status == 'all':
            cursor.execute("SELECT * FROM positions ORDER BY decision_date DESC")
        else:
            cursor.execute("SELECT * FROM positions WHERE status = ? ORDER BY decision_date DESC", (status,))

        columns = [desc[0] for desc in cursor.description]
        positions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return positions

    def get_monthly_summary(self) -> Dict:
        """
        Get summary of current month's activity.

        Returns:
            Dictionary with monthly statistics
        """
        year_month = self._get_current_year_month()
        budget = self.get_budget_status()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count positions this month
        cursor.execute(
            "SELECT COUNT(*) FROM positions WHERE year_month = ?",
            (year_month,)
        )
        num_positions = cursor.fetchone()[0]

        # Count notifications
        cursor.execute(
            "SELECT COUNT(*) FROM notifications WHERE year_month = ?",
            (year_month,)
        )
        num_notifications = cursor.fetchone()[0]

        conn.close()

        return {
            "year_month": year_month,
            "budget": budget,
            "num_positions": num_positions,
            "num_notifications": num_notifications
        }

    def record_trade(
        self,
        ticker: str,
        action: str,
        amount: float,
        price: float,
        confidence: float,
        reasoning: str = ""
    ):
        """
        Record a trade for backtesting purposes.

        Args:
            ticker: Stock ticker
            action: BUY, SELL, or HOLD
            amount: Investment amount
            price: Stock price at trade time
            confidence: Decision confidence
            reasoning: Trade reasoning
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO trade_history (ticker, action, amount, price, confidence, trade_date, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ticker, action, amount, price, confidence, datetime.now(), reasoning))

            conn.commit()
            logger.debug(f"Recorded trade: {action} {ticker} @ ${price:.2f}")

        except Exception as e:
            logger.error(f"Error recording trade: {str(e)}")

        finally:
            conn.close()


# Singleton instance
_portfolio_manager_instance = None


def get_portfolio_manager() -> PortfolioManager:
    """Get or create the PortfolioManager singleton."""
    global _portfolio_manager_instance
    if _portfolio_manager_instance is None:
        _portfolio_manager_instance = PortfolioManager()
    return _portfolio_manager_instance
