"""
Trailing Stop Loss System
Automatically raises stop loss as price increases to lock in profits
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TrailingStopManager:
    """Manages trailing stop losses for positions"""

    def __init__(self, trailing_pct: float = 0.03):
        """
        Initialize trailing stop manager

        Args:
            trailing_pct: Trailing percentage (default 3%)
        """
        self.trailing_pct = trailing_pct
        self.positions = {}  # ticker -> position data

    def add_position(self, ticker: str, entry_price: float, stop_loss: float):
        """
        Add a position to track

        Args:
            ticker: Stock ticker
            entry_price: Entry price
            stop_loss: Initial stop loss
        """
        self.positions[ticker] = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'highest_price': entry_price,
            'trailing_active': False
        }
        logger.info(f"Added trailing stop for {ticker}: Entry ${entry_price:.2f}, Stop ${stop_loss:.2f}")

    def update_position(self, ticker: str, current_price: float) -> Dict[str, Any]:
        """
        Update position and check if trailing stop should activate/update

        Args:
            ticker: Stock ticker
            current_price: Current market price

        Returns:
            Dictionary with stop status and alerts
        """
        if ticker not in self.positions:
            return {'error': f'{ticker} not found in positions'}

        pos = self.positions[ticker]
        result = {
            'ticker': ticker,
            'current_price': current_price,
            'entry_price': pos['entry_price'],
            'stop_loss': pos['stop_loss'],
            'highest_price': pos['highest_price'],
            'trailing_active': pos['trailing_active'],
            'stop_triggered': False,
            'stop_updated': False,
            'profit_pct': ((current_price / pos['entry_price']) - 1) * 100
        }

        # Update highest price seen
        if current_price > pos['highest_price']:
            pos['highest_price'] = current_price

            # Activate trailing once in profit
            if not pos['trailing_active'] and current_price > pos['entry_price']:
                pos['trailing_active'] = True
                result['trailing_activated'] = True
                logger.info(f"{ticker}: Trailing stop ACTIVATED at ${current_price:.2f}")

            # Update stop loss if trailing active
            if pos['trailing_active']:
                new_stop = pos['highest_price'] * (1 - self.trailing_pct)

                # Only raise stop loss, never lower it
                if new_stop > pos['stop_loss']:
                    old_stop = pos['stop_loss']
                    pos['stop_loss'] = new_stop
                    result['stop_updated'] = True
                    result['old_stop'] = old_stop
                    result['new_stop'] = new_stop

                    logger.info(f"{ticker}: Stop loss raised ${old_stop:.2f} → ${new_stop:.2f}")

        # Check if stop loss triggered
        if current_price <= pos['stop_loss']:
            result['stop_triggered'] = True
            result['reason'] = 'trailing_stop' if pos['trailing_active'] else 'initial_stop'
            logger.warning(f"{ticker}: STOP LOSS TRIGGERED at ${current_price:.2f}")

        return result

    def get_position(self, ticker: str) -> Dict[str, Any]:
        """Get current position data"""
        if ticker not in self.positions:
            return None
        return self.positions[ticker].copy()

    def remove_position(self, ticker: str):
        """Remove position from tracking"""
        if ticker in self.positions:
            del self.positions[ticker]
            logger.info(f"Removed trailing stop for {ticker}")

    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all tracked positions"""
        return self.positions.copy()


# Singleton instance
_trailing_stop_manager = None


def get_trailing_stop_manager(trailing_pct: float = 0.03) -> TrailingStopManager:
    """Get or create trailing stop manager"""
    global _trailing_stop_manager
    if _trailing_stop_manager is None:
        _trailing_stop_manager = TrailingStopManager(trailing_pct)
    return _trailing_stop_manager
