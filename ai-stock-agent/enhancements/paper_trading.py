"""
Paper Trading System
Simulate trades without risking real money
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PaperTradingAccount:
    """Simulated trading account"""

    def __init__(self, starting_balance: float = 10000, data_file: str = "data/paper_trades.json"):
        """
        Initialize paper trading account

        Args:
            starting_balance: Starting cash balance
            data_file: File to save trades
        """
        self.data_file = Path(data_file)
        self.starting_balance = starting_balance

        # Load existing data or create new
        if self.data_file.exists():
            self.load_account()
        else:
            self.cash = starting_balance
            self.positions = {}  # ticker -> {shares, avg_price, total_cost}
            self.trades = []  # List of all trades
            self.save_account()

    def buy(self, ticker: str, shares: int, price: float) -> Dict[str, Any]:
        """
        Execute paper buy order

        Args:
            ticker: Stock ticker
            shares: Number of shares
            price: Price per share

        Returns:
            Trade result dictionary
        """
        cost = shares * price

        if cost > self.cash:
            return {
                'success': False,
                'error': f'Insufficient funds. Need ${cost:.2f}, have ${self.cash:.2f}'
            }

        # Update cash
        self.cash -= cost

        # Update position
        if ticker in self.positions:
            pos = self.positions[ticker]
            total_shares = pos['shares'] + shares
            total_cost = pos['total_cost'] + cost
            avg_price = total_cost / total_shares

            self.positions[ticker] = {
                'shares': total_shares,
                'avg_price': avg_price,
                'total_cost': total_cost
            }
        else:
            self.positions[ticker] = {
                'shares': shares,
                'avg_price': price,
                'total_cost': cost
            }

        # Record trade
        trade = {
            'type': 'BUY',
            'ticker': ticker,
            'shares': shares,
            'price': price,
            'cost': cost,
            'timestamp': datetime.now().isoformat(),
            'cash_remaining': self.cash
        }
        self.trades.append(trade)
        self.save_account()

        logger.info(f"📝 PAPER BUY: {shares} shares of {ticker} @ ${price:.2f} (${cost:.2f})")

        return {
            'success': True,
            'trade': trade,
            'position': self.positions[ticker].copy()
        }

    def sell(self, ticker: str, shares: int, price: float) -> Dict[str, Any]:
        """
        Execute paper sell order

        Args:
            ticker: Stock ticker
            shares: Number of shares
            price: Price per share

        Returns:
            Trade result dictionary
        """
        if ticker not in self.positions:
            return {
                'success': False,
                'error': f'No position in {ticker}'
            }

        pos = self.positions[ticker]
        if shares > pos['shares']:
            return {
                'success': False,
                'error': f'Insufficient shares. Have {pos["shares"]}, trying to sell {shares}'
            }

        # Calculate proceeds and profit/loss
        proceeds = shares * price
        cost_basis = (pos['total_cost'] / pos['shares']) * shares
        profit_loss = proceeds - cost_basis
        profit_loss_pct = (profit_loss / cost_basis) * 100

        # Update cash
        self.cash += proceeds

        # Update position
        if shares == pos['shares']:
            # Closing entire position
            del self.positions[ticker]
        else:
            # Partial sell
            remaining_shares = pos['shares'] - shares
            remaining_cost = pos['total_cost'] - cost_basis

            self.positions[ticker] = {
                'shares': remaining_shares,
                'avg_price': remaining_cost / remaining_shares,
                'total_cost': remaining_cost
            }

        # Record trade
        trade = {
            'type': 'SELL',
            'ticker': ticker,
            'shares': shares,
            'price': price,
            'proceeds': proceeds,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'timestamp': datetime.now().isoformat(),
            'cash_remaining': self.cash
        }
        self.trades.append(trade)
        self.save_account()

        symbol = "📈" if profit_loss > 0 else "📉"
        logger.info(f"📝 PAPER SELL: {shares} shares of {ticker} @ ${price:.2f} {symbol} P/L: ${profit_loss:.2f} ({profit_loss_pct:+.2f}%)")

        return {
            'success': True,
            'trade': trade,
            'position': self.positions.get(ticker, {}).copy() if ticker in self.positions else None
        }

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate current portfolio value

        Args:
            current_prices: Dictionary of ticker -> current price

        Returns:
            Portfolio value breakdown
        """
        positions_value = 0
        position_details = []

        for ticker, pos in self.positions.items():
            current_price = current_prices.get(ticker, pos['avg_price'])
            market_value = pos['shares'] * current_price
            unrealized_pl = market_value - pos['total_cost']
            unrealized_pl_pct = (unrealized_pl / pos['total_cost']) * 100

            positions_value += market_value

            position_details.append({
                'ticker': ticker,
                'shares': pos['shares'],
                'avg_price': pos['avg_price'],
                'current_price': current_price,
                'market_value': market_value,
                'unrealized_pl': unrealized_pl,
                'unrealized_pl_pct': unrealized_pl_pct
            })

        total_value = self.cash + positions_value
        total_return = total_value - self.starting_balance
        total_return_pct = (total_return / self.starting_balance) * 100

        return {
            'cash': self.cash,
            'positions_value': positions_value,
            'total_value': total_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'positions': position_details
        }

    def get_trade_history(self, limit: int = None) -> List[Dict]:
        """Get trade history"""
        if limit:
            return self.trades[-limit:]
        return self.trades.copy()

    def save_account(self):
        """Save account state to file"""
        data = {
            'starting_balance': self.starting_balance,
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_account(self):
        """Load account state from file"""
        with open(self.data_file, 'r') as f:
            data = json.load(f)

        self.starting_balance = data.get('starting_balance', 10000)
        self.cash = data.get('cash', self.starting_balance)
        self.positions = data.get('positions', {})
        self.trades = data.get('trades', [])

        logger.info(f"Loaded paper trading account: ${self.cash:.2f} cash, {len(self.positions)} positions")

    def reset_account(self):
        """Reset account to starting balance"""
        self.cash = self.starting_balance
        self.positions = {}
        self.trades = []
        self.save_account()
        logger.info(f"Paper trading account reset to ${self.starting_balance:.2f}")


# Singleton instance
_paper_account = None


def get_paper_account(starting_balance: float = 10000) -> PaperTradingAccount:
    """Get or create paper trading account"""
    global _paper_account
    if _paper_account is None:
        _paper_account = PaperTradingAccount(starting_balance)
    return _paper_account
