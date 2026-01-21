"""
Backtesting Engine - Simulates trading based on historical recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import yfinance as yf
import pandas as pd
from backtesting.database import get_backtest_db

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtesting engine that simulates historical trading.
    """

    def __init__(self, initial_capital: float = 100000):
        """
        Initialize the backtest engine.

        Args:
            initial_capital: Starting capital for simulation
        """
        self.db = get_backtest_db()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # ticker -> {shares, entry_price, rec_id}
        self.trade_history = []

    def run_backtest(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        decision_graph,
        hold_days: int = 30
    ) -> Dict[str, Any]:
        """
        Run backtest for a single stock.

        Args:
            ticker: Stock ticker
            start_date: Start date for backtest
            end_date: End date for backtest
            decision_graph: Decision graph instance to generate signals
            hold_days: Number of days to hold positions

        Returns:
            Backtest results
        """
        logger.info(f"Running backtest for {ticker} from {start_date} to {end_date}")

        # Get historical data
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date, interval='1d')

        if hist.empty:
            logger.error(f"No historical data for {ticker}")
            return {'error': 'No historical data'}

        # Simulate trading day by day
        for current_date in pd.date_range(start=start_date, end=end_date, freq='D'):
            # Skip weekends
            if current_date.weekday() >= 5:
                continue

            # Check if we have price data for this date
            if current_date not in hist.index:
                continue

            current_price = hist.loc[current_date, 'Close']

            # Update database with price
            self.db.update_price(
                ticker,
                current_date,
                current_price,
                hist.loc[current_date, 'Open'],
                hist.loc[current_date, 'High'],
                hist.loc[current_date, 'Low'],
                hist.loc[current_date, 'Volume']
            )

            # Check if we should close existing positions
            self._check_position_closes(ticker, current_date, current_price, hold_days)

            # Generate new signal (once per week to avoid overtrading)
            if current_date.weekday() == 0:  # Monday
                self._generate_signal(ticker, current_date, decision_graph)

            # Check if we should open new position
            self._check_position_opens(ticker, current_date, current_price)

        # Close any remaining positions
        self._close_all_positions(ticker, end_date, hist.iloc[-1]['Close'])

        # Calculate results
        final_capital = self.current_capital
        for pos in self.positions.values():
            final_capital += pos['shares'] * hist.iloc[-1]['Close']

        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        return {
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': round(total_return, 2),
            'num_trades': len(self.trade_history),
            'trade_history': self.trade_history
        }

    def _generate_signal(
        self,
        ticker: str,
        date: datetime,
        decision_graph
    ):
        """Generate trading signal for a date."""
        try:
            # Run analysis for this point in time
            # Note: In real backtest, we'd use data only up to 'date'
            result = decision_graph.run(ticker, period='6mo', interval='1d')

            if result.get('error'):
                return

            # Save recommendation
            self.db.save_recommendation(
                ticker,
                result,
                result.get('features', {}),
                result.get('fundamentals', {}),
                result.get('news_analysis', {}),
                result.get('market_context', {})
            )

        except Exception as e:
            logger.error(f"Error generating signal for {ticker} on {date}: {e}")

    def _check_position_opens(self, ticker: str, date: datetime, price: float):
        """Check if we should open a new position."""
        # Get latest open recommendation
        open_recs = self.db.get_open_recommendations(ticker)

        for rec in open_recs:
            decision = rec['decision']
            confidence = rec['confidence']

            # Only take high confidence signals
            if confidence < 0.70:
                continue

            # Check if we already have a position
            if ticker in self.positions:
                continue

            # Calculate position size based on confidence
            risk_per_trade = 0.02  # 2% of capital per trade
            position_size = self.current_capital * risk_per_trade * confidence

            shares = int(position_size / price)

            if shares > 0 and decision == 'BUY':
                cost = shares * price
                if cost <= self.current_capital:
                    # Open position
                    self.current_capital -= cost
                    self.positions[ticker] = {
                        'shares': shares,
                        'entry_price': price,
                        'entry_date': date,
                        'rec_id': rec['id']
                    }

                    self.trade_history.append({
                        'ticker': ticker,
                        'action': 'BUY',
                        'date': date,
                        'price': price,
                        'shares': shares,
                        'value': cost
                    })

                    logger.info(f"Opened BUY position: {ticker} x{shares} @ ${price:.2f}")

    def _check_position_closes(
        self,
        ticker: str,
        date: datetime,
        price: float,
        hold_days: int
    ):
        """Check if we should close existing positions."""
        if ticker not in self.positions:
            return

        pos = self.positions[ticker]
        entry_date = pos['entry_date']
        entry_price = pos['entry_price']
        rec_id = pos['rec_id']

        # Get recommendation details
        recs = self.db.get_open_recommendations(ticker)
        rec = next((r for r in recs if r['id'] == rec_id), None)

        if not rec:
            return

        should_close = False
        exit_reason = ""

        # Check stop loss
        if rec.get('stop_loss'):
            if price <= rec['stop_loss']:
                should_close = True
                exit_reason = "Stop loss hit"

        # Check price target
        if rec.get('price_target'):
            if price >= rec['price_target']:
                should_close = True
                exit_reason = "Price target reached"

        # Check holding period
        days_held = (date - entry_date).days
        if days_held >= hold_days:
            should_close = True
            exit_reason = f"Held for {hold_days} days"

        if should_close:
            # Close position
            proceeds = pos['shares'] * price
            self.current_capital += proceeds

            self.trade_history.append({
                'ticker': ticker,
                'action': 'SELL',
                'date': date,
                'price': price,
                'shares': pos['shares'],
                'value': proceeds
            })

            # Update database
            self.db.close_recommendation(rec_id, price, exit_reason)

            # Calculate P&L
            profit = proceeds - (pos['shares'] * entry_price)
            profit_pct = (profit / (pos['shares'] * entry_price)) * 100

            logger.info(
                f"Closed position: {ticker} x{pos['shares']} @ ${price:.2f} "
                f"({exit_reason}) P&L: ${profit:.2f} ({profit_pct:+.2f}%)"
            )

            del self.positions[ticker]

    def _close_all_positions(self, ticker: str, date: datetime, price: float):
        """Close all remaining positions."""
        if ticker in self.positions:
            self._check_position_closes(ticker, date, price, hold_days=0)


def run_historical_backtest(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 100000
) -> Dict[str, Any]:
    """
    Run a historical backtest for a stock.

    Args:
        ticker: Stock ticker
        start_date: Start date
        end_date: End date
        initial_capital: Starting capital

    Returns:
        Backtest results
    """
    from graph.autonomous_decision_graph import get_autonomous_decision_graph

    engine = BacktestEngine(initial_capital)
    graph = get_autonomous_decision_graph()

    results = engine.run_backtest(ticker, start_date, end_date, graph)

    # Add buy-and-hold comparison
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date, end=end_date)

    if not hist.empty:
        start_price = hist.iloc[0]['Close']
        end_price = hist.iloc[-1]['Close']
        buy_hold_return = ((end_price - start_price) / start_price) * 100

        results['buy_and_hold_return'] = round(buy_hold_return, 2)
        results['vs_buy_hold'] = round(results['total_return'] - buy_hold_return, 2)

    return results
