"""
Performance Tracker - Tracks live recommendations and calculates performance metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import yfinance as yf
import pandas as pd
import numpy as np
from backtesting.database import get_backtest_db

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Tracks and analyzes system performance."""

    def __init__(self):
        """Initialize the performance tracker."""
        self.db = get_backtest_db()

    def track_recommendation(
        self,
        ticker: str,
        result: Dict[str, Any]
    ) -> int:
        """
        Track a new recommendation.

        Args:
            ticker: Stock ticker
            result: Analysis result from decision graph

        Returns:
            Recommendation ID
        """
        rec_id = self.db.save_recommendation(
            ticker,
            result.get('decision', {}),
            {'features': result.get('features', {})},
            result.get('fundamentals', {}),
            result.get('news_analysis', {}),
            result.get('market_context', {})
        )

        logger.info(f"Tracking recommendation {rec_id} for {ticker}")
        return rec_id

    def update_open_positions(self):
        """
        Update all open positions with current prices.
        """
        open_recs = self.db.get_open_recommendations()

        logger.info(f"Updating {len(open_recs)} open positions...")

        for rec in open_recs:
            try:
                ticker = rec['ticker']
                rec_id = rec['id']
                entry_price = rec['entry_price']
                stop_loss = rec['stop_loss']
                price_target = rec['price_target']
                rec_date = datetime.fromisoformat(rec['recommendation_date'])

                # Get current price
                stock = yf.Ticker(ticker)
                current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')

                if not current_price:
                    logger.warning(f"Could not get current price for {ticker}")
                    continue

                # Check if we should auto-close
                should_close = False
                exit_reason = ""

                # Check stop loss
                if stop_loss and current_price <= stop_loss:
                    should_close = True
                    exit_reason = "Stop loss triggered"

                # Check price target
                if price_target and current_price >= price_target:
                    should_close = True
                    exit_reason = "Price target reached"

                # Check holding period (auto-close after 90 days)
                days_held = (datetime.now() - rec_date).days
                if days_held >= 90:
                    should_close = True
                    exit_reason = "90-day holding period expired"

                if should_close:
                    self.db.close_recommendation(rec_id, current_price, exit_reason)
                    logger.info(f"Auto-closed {ticker}: {exit_reason}")

            except Exception as e:
                logger.error(f"Error updating {ticker}: {e}")

    def get_performance_summary(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance summary for last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Performance summary
        """
        start_date = datetime.now() - timedelta(days=days)

        metrics = self.db.get_performance_metrics(start_date=start_date)

        # Add performance by decision type
        buy_metrics = self.db.get_performance_metrics(
            start_date=start_date,
            decision_type='BUY'
        )
        sell_metrics = self.db.get_performance_metrics(
            start_date=start_date,
            decision_type='SELL'
        )

        return {
            'period_days': days,
            'overall': metrics,
            'buy_signals': buy_metrics,
            'sell_signals': sell_metrics,
            'generated_at': datetime.now().isoformat()
        }

    def get_recommendation_accuracy(
        self,
        days: int = 30,
        min_confidence: float = 0.7
    ) -> Dict[str, Any]:
        """
        Calculate recommendation accuracy.

        Args:
            days: Number of days to analyze
            min_confidence: Minimum confidence threshold

        Returns:
            Accuracy metrics
        """
        start_date = datetime.now() - timedelta(days=days)

        # Get all closed recommendations
        history = self.db.get_recommendation_history(limit=1000)

        # Filter by date and confidence
        filtered = [
            rec for rec in history
            if rec['is_closed']
            and datetime.fromisoformat(rec['recommendation_date']) >= start_date
            and rec['confidence'] >= min_confidence
        ]

        if not filtered:
            return {
                'total_recommendations': 0,
                'correct_predictions': 0,
                'accuracy': 0,
                'high_confidence_total': 0,
                'high_confidence_correct': 0,
                'high_confidence_accuracy': 0
            }

        total = len(filtered)
        correct = sum(1 for rec in filtered if rec['outcome'] == 'win')

        # High confidence (>0.8) accuracy
        high_conf = [rec for rec in filtered if rec['confidence'] >= 0.8]
        high_conf_correct = sum(1 for rec in high_conf if rec['outcome'] == 'win')

        return {
            'total_recommendations': total,
            'correct_predictions': correct,
            'accuracy': round((correct / total) * 100, 2) if total > 0 else 0,
            'high_confidence_total': len(high_conf),
            'high_confidence_correct': high_conf_correct,
            'high_confidence_accuracy': round(
                (high_conf_correct / len(high_conf)) * 100, 2
            ) if high_conf else 0
        }

    def generate_performance_report(
        self,
        days: int = 30
    ) -> str:
        """
        Generate a formatted performance report.

        Args:
            days: Number of days to analyze

        Returns:
            Formatted report string
        """
        summary = self.get_performance_summary(days)
        accuracy = self.get_recommendation_accuracy(days)

        overall = summary['overall']
        buy = summary['buy_signals']
        sell = summary['sell_signals']

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║          PERFORMANCE REPORT - Last {days} Days
╚══════════════════════════════════════════════════════════════╝

📊 OVERALL PERFORMANCE
{'═'*70}
Total Trades:        {overall['total_trades']}
Wins / Losses:       {overall['wins']} / {overall['losses']}
Win Rate:            {overall['win_rate']:.2f}%
Average Return:      {overall['avg_return']:+.2f}%
Total Return:        {overall['total_return']:+.2f}%
Sharpe Ratio:        {overall['sharpe_ratio']:.2f}
Max Drawdown:        {overall['max_drawdown']:.2f}%
Profit Factor:       {overall['profit_factor']:.2f}

💰 RETURN BREAKDOWN
{'═'*70}
Average Win:         +{overall['avg_win']:.2f}%
Average Loss:        {overall['avg_loss']:.2f}%
Risk/Reward:         {abs(overall['avg_win'] / overall['avg_loss']) if overall['avg_loss'] != 0 else 0:.2f}x

🟢 BUY SIGNALS
{'═'*70}
Total Trades:        {buy['total_trades']}
Win Rate:            {buy['win_rate']:.2f}%
Average Return:      {buy['avg_return']:+.2f}%
Total Return:        {buy['total_return']:+.2f}%

🔴 SELL SIGNALS
{'═'*70}
Total Trades:        {sell['total_trades']}
Win Rate:            {sell['win_rate']:.2f}%
Average Return:      {sell['avg_return']:+.2f}%
Total Return:        {sell['total_return']:+.2f}%

🎯 ACCURACY METRICS
{'═'*70}
Total Recommendations:     {accuracy['total_recommendations']}
Correct Predictions:       {accuracy['correct_predictions']}
Overall Accuracy:          {accuracy['accuracy']:.2f}%

High Confidence (>80%):    {accuracy['high_confidence_total']}
High Conf. Correct:        {accuracy['high_confidence_correct']}
High Conf. Accuracy:       {accuracy['high_confidence_accuracy']:.2f}%

{'═'*70}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'═'*70}
"""
        return report

    def get_best_worst_trades(
        self,
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get best and worst performing trades.

        Args:
            limit: Number of trades to return

        Returns:
            Dictionary with 'best' and 'worst' trade lists
        """
        history = self.db.get_recommendation_history(limit=1000)

        closed = [rec for rec in history if rec['is_closed']]

        if not closed:
            return {'best': [], 'worst': []}

        # Sort by profit/loss percentage
        sorted_trades = sorted(closed, key=lambda x: x['profit_loss_pct'], reverse=True)

        best = sorted_trades[:limit]
        worst = sorted_trades[-limit:][::-1]  # Reverse to show worst first

        return {
            'best': best,
            'worst': worst
        }

    def get_ticker_performance(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a specific ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Ticker-specific metrics
        """
        history = self.db.get_recommendation_history(ticker=ticker, limit=100)

        closed = [rec for rec in history if rec['is_closed']]

        if not closed:
            return {
                'ticker': ticker,
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0
            }

        total = len(closed)
        wins = sum(1 for rec in closed if rec['outcome'] == 'win')
        returns = [rec['profit_loss_pct'] for rec in closed]

        return {
            'ticker': ticker,
            'total_trades': total,
            'wins': wins,
            'losses': sum(1 for rec in closed if rec['outcome'] == 'loss'),
            'win_rate': round((wins / total) * 100, 2) if total > 0 else 0,
            'avg_return': round(sum(returns) / total, 2) if total > 0 else 0,
            'total_return': round(sum(returns), 2),
            'best_trade': round(max(returns), 2) if returns else 0,
            'worst_trade': round(min(returns), 2) if returns else 0
        }


# Singleton instance
_performance_tracker_instance = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create the PerformanceTracker singleton."""
    global _performance_tracker_instance
    if _performance_tracker_instance is None:
        _performance_tracker_instance = PerformanceTracker()
    return _performance_tracker_instance
