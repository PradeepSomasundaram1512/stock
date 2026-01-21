"""
Backtesting Database - Stores all recommendations and outcomes for performance tracking.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


class BacktestDatabase:
    """Manages backtesting data storage and retrieval."""

    def __init__(self, db_path: str = "data/backtest.db"):
        """Initialize the backtest database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Recommendations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    recommendation_date TIMESTAMP NOT NULL,
                    decision TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    price_target REAL,
                    stop_loss REAL,
                    risk_level TEXT,
                    time_horizon TEXT,
                    reasoning TEXT,
                    key_factors TEXT,

                    -- Technical data
                    rsi REAL,
                    macd_signal TEXT,
                    trend TEXT,
                    volatility REAL,

                    -- Fundamental data
                    pe_ratio REAL,
                    valuation_score REAL,
                    health_score REAL,
                    growth_score REAL,

                    -- News data
                    news_sentiment TEXT,
                    news_sentiment_score REAL,
                    news_count INTEGER,

                    -- Market context
                    market_trend TEXT,
                    market_vix REAL,

                    -- Tracking fields
                    is_closed BOOLEAN DEFAULT 0,
                    exit_date TIMESTAMP,
                    exit_price REAL,
                    exit_reason TEXT,
                    profit_loss_pct REAL,
                    outcome TEXT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker
                ON recommendations(ticker)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_date
                ON recommendations(recommendation_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision
                ON recommendations(decision)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_closed
                ON recommendations(is_closed)
            """)

            # Daily prices table (for tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL NOT NULL,
                    volume INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, date)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker_date
                ON daily_prices(ticker, date)
            """)

            conn.commit()
            logger.info("Backtest database initialized")

    def save_recommendation(
        self,
        ticker: str,
        decision_data: Dict[str, Any],
        technical_data: Dict[str, Any],
        fundamental_data: Dict[str, Any],
        news_data: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> int:
        """
        Save a recommendation to the database.

        Returns:
            Recommendation ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            features = technical_data.get('features', {})
            decision = decision_data  # decision_data IS the decision dict

            cursor.execute("""
                INSERT INTO recommendations (
                    ticker, recommendation_date, decision, confidence,
                    entry_price, price_target, stop_loss, risk_level, time_horizon,
                    reasoning, key_factors,
                    rsi, macd_signal, trend, volatility,
                    pe_ratio, valuation_score, health_score, growth_score,
                    news_sentiment, news_sentiment_score, news_count,
                    market_trend, market_vix
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                datetime.now(),
                decision.get('decision', 'HOLD'),
                decision.get('confidence', 0.5),
                features.get('latest_price', 0),
                decision.get('price_target'),
                decision.get('stop_loss'),
                decision.get('risk_level'),
                decision.get('time_horizon'),
                decision.get('reasoning', ''),
                json.dumps(decision.get('key_factors', [])),
                features.get('rsi'),
                features.get('macd_signal'),
                features.get('trend'),
                features.get('volatility'),
                fundamental_data.get('pe_ratio'),
                fundamental_data.get('valuation_score'),
                fundamental_data.get('health_score'),
                fundamental_data.get('growth_score'),
                news_data.get('sentiment'),
                news_data.get('sentiment_score'),
                news_data.get('news_count'),
                market_data.get('market_trend'),
                market_data.get('volatility_index')
            ))

            conn.commit()
            rec_id = cursor.lastrowid
            logger.info(f"Saved recommendation {rec_id} for {ticker}: {decision.get('decision')}")
            return rec_id

    def update_price(self, ticker: str, date: datetime, close: float,
                     open_price: float = None, high: float = None,
                     low: float = None, volume: int = None):
        """Update daily price for a ticker."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO daily_prices
                (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ticker, date.date(), open_price, high, low, close, volume))

            conn.commit()

    def close_recommendation(
        self,
        rec_id: int,
        exit_price: float,
        exit_reason: str = "Manual close"
    ):
        """
        Close a recommendation and calculate P&L.

        Args:
            rec_id: Recommendation ID
            exit_price: Exit price
            exit_reason: Reason for closing
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get recommendation details
            cursor.execute("""
                SELECT entry_price, decision, price_target, stop_loss
                FROM recommendations WHERE id = ?
            """, (rec_id,))

            row = cursor.fetchone()
            if not row:
                logger.error(f"Recommendation {rec_id} not found")
                return

            entry_price, decision, price_target, stop_loss = row

            # Calculate profit/loss percentage
            if decision == 'BUY':
                profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100
            elif decision == 'SELL':
                profit_loss_pct = ((entry_price - exit_price) / entry_price) * 100
            else:  # HOLD
                profit_loss_pct = 0

            # Determine outcome
            if abs(profit_loss_pct) < 1:
                outcome = 'neutral'
            elif profit_loss_pct > 0:
                outcome = 'win'
            else:
                outcome = 'loss'

            # Update recommendation
            cursor.execute("""
                UPDATE recommendations
                SET is_closed = 1,
                    exit_date = ?,
                    exit_price = ?,
                    exit_reason = ?,
                    profit_loss_pct = ?,
                    outcome = ?
                WHERE id = ?
            """, (datetime.now(), exit_price, exit_reason, profit_loss_pct, outcome, rec_id))

            conn.commit()
            logger.info(f"Closed recommendation {rec_id}: {outcome} ({profit_loss_pct:+.2f}%)")

    def get_open_recommendations(self, ticker: str = None) -> List[Dict[str, Any]]:
        """Get all open recommendations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if ticker:
                cursor.execute("""
                    SELECT * FROM recommendations
                    WHERE is_closed = 0 AND ticker = ?
                    ORDER BY recommendation_date DESC
                """, (ticker,))
            else:
                cursor.execute("""
                    SELECT * FROM recommendations
                    WHERE is_closed = 0
                    ORDER BY recommendation_date DESC
                """)

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_performance_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            decision_type: Filter by BUY/SELL/HOLD

        Returns:
            Performance metrics dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            where_clauses = ["is_closed = 1"]
            params = []

            if start_date:
                where_clauses.append("recommendation_date >= ?")
                params.append(start_date)

            if end_date:
                where_clauses.append("recommendation_date <= ?")
                params.append(end_date)

            if decision_type:
                where_clauses.append("decision = ?")
                params.append(decision_type)

            where_sql = " AND ".join(where_clauses)

            # Get all closed recommendations
            cursor.execute(f"""
                SELECT
                    profit_loss_pct,
                    outcome,
                    decision,
                    confidence,
                    risk_level
                FROM recommendations
                WHERE {where_sql}
            """, params)

            rows = cursor.fetchall()

            if not rows:
                return {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'neutrals': 0,
                    'win_rate': 0,
                    'avg_return': 0,
                    'total_return': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'profit_factor': 0
                }

            # Calculate metrics
            total_trades = len(rows)
            profits = [row[0] for row in rows]
            outcomes = [row[1] for row in rows]

            wins = outcomes.count('win')
            losses = outcomes.count('loss')
            neutrals = outcomes.count('neutral')

            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            avg_return = sum(profits) / total_trades if total_trades > 0 else 0
            total_return = sum(profits)

            # Calculate Sharpe ratio (simplified)
            import numpy as np
            if len(profits) > 1:
                returns_std = np.std(profits)
                sharpe_ratio = (avg_return / returns_std) if returns_std > 0 else 0
            else:
                sharpe_ratio = 0

            # Calculate max drawdown
            cumulative = np.cumsum(profits)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = running_max - cumulative
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0

            # Average win/loss
            winning_trades = [p for p in profits if p > 0]
            losing_trades = [p for p in profits if p < 0]

            avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0

            return {
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'neutrals': neutrals,
                'win_rate': round(win_rate, 2),
                'avg_return': round(avg_return, 2),
                'total_return': round(total_return, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown, 2),
                'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0
            }

    def get_recommendation_history(
        self,
        ticker: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recommendation history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if ticker:
                cursor.execute("""
                    SELECT * FROM recommendations
                    WHERE ticker = ?
                    ORDER BY recommendation_date DESC
                    LIMIT ?
                """, (ticker, limit))
            else:
                cursor.execute("""
                    SELECT * FROM recommendations
                    ORDER BY recommendation_date DESC
                    LIMIT ?
                """, (limit,))

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Singleton instance
_backtest_db_instance = None


def get_backtest_db() -> BacktestDatabase:
    """Get or create the BacktestDatabase singleton."""
    global _backtest_db_instance
    if _backtest_db_instance is None:
        _backtest_db_instance = BacktestDatabase()
    return _backtest_db_instance
