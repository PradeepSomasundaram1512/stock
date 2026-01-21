"""
Stock Scanner - Batch analysis of multiple stocks.
"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from graph.decision_graph import get_decision_graph
from portfolio.manager import get_portfolio_manager
from portfolio.signal_filter import get_buy_signal_filter
from notifications.notifier import get_notifier
from notifications.voice_notifier import get_voice_notifier
from app.config import WATCHLIST_FILE

logger = logging.getLogger(__name__)


class StockScanner:
    """Scans multiple stocks and generates buy signal notifications."""

    def __init__(self):
        """Initialize the Stock Scanner."""
        self.decision_graph = get_decision_graph()
        self.portfolio_manager = get_portfolio_manager()
        self.signal_filter = get_buy_signal_filter()
        self.notifier = get_notifier()
        self.voice_notifier = get_voice_notifier()

    def load_watchlist(self) -> List[str]:
        """
        Load ticker symbols from watchlist file.

        Returns:
            List of ticker symbols
        """
        if not WATCHLIST_FILE.exists():
            logger.warning(f"Watchlist file not found: {WATCHLIST_FILE}")
            return []

        tickers = []
        try:
            with open(WATCHLIST_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        tickers.append(line.upper())

            logger.info(f"Loaded {len(tickers)} tickers from watchlist")
            return tickers

        except Exception as e:
            logger.error(f"Error loading watchlist: {str(e)}")
            return []

    def scan_stock(self, ticker: str) -> Dict[str, Any]:
        """
        Analyze a single stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Analysis result dictionary
        """
        logger.info(f"Scanning {ticker}...")

        try:
            # Run decision graph
            result = self.decision_graph.run(ticker)

            if result.get('error'):
                logger.error(f"Error analyzing {ticker}: {result['error']}")
                return {"ticker": ticker, "error": result['error']}

            return result

        except Exception as e:
            logger.error(f"Exception scanning {ticker}: {str(e)}")
            return {"ticker": ticker, "error": str(e)}

    def process_scan_result(self, result: Dict[str, Any]) -> bool:
        """
        Process scan result and send notification if buy signal.

        Args:
            result: Stock analysis result

        Returns:
            True if notification sent, False otherwise
        """
        if result.get('error'):
            return False

        ticker = result.get('ticker', 'UNKNOWN')
        decision = result.get('decision', {})
        features = result.get('features', {})

        # Get budget status
        budget_status = self.portfolio_manager.get_budget_status()

        # Check if should notify
        should_notify, suggested_amount, reason = self.signal_filter.should_notify(
            decision,
            features,
            budget_status['remaining']
        )

        if not should_notify:
            logger.info(f"{ticker}: {reason}")
            return False

        # Format buy signal
        buy_signal = self.signal_filter.format_buy_signal_summary(
            ticker,
            decision,
            features,
            suggested_amount,
            budget_status['remaining']
        )

        # Log notification (prevents duplicates)
        if not self.portfolio_manager.log_notification(
            ticker,
            decision.get('decision'),
            decision.get('confidence', 0.0),
            suggested_amount
        ):
            logger.info(f"{ticker}: Duplicate notification, skipping")
            return False

        # Send notifications
        self.notifier.send_buy_signal_notification(buy_signal)
        self.voice_notifier.speak_buy_signal(buy_signal)

        logger.info(f"{ticker}: Buy signal notification sent")
        return True

    def scan_all(self) -> Dict[str, Any]:
        """
        Scan all stocks in watchlist.

        Returns:
            Summary dictionary with scan results
        """
        tickers = self.load_watchlist()

        if not tickers:
            logger.warning("No tickers to scan")
            return {
                "scanned": 0,
                "buy_signals": 0,
                "notifications_sent": 0
            }

        logger.info(f"Starting scan of {len(tickers)} stocks...")

        scanned = 0
        buy_signals = 0
        notifications_sent = 0
        errors = 0

        for ticker in tickers:
            result = self.scan_stock(ticker)

            if result.get('error'):
                errors += 1
                continue

            scanned += 1

            # Check if buy signal
            decision = result.get('decision', {})
            if decision.get('decision') == 'BUY':
                buy_signals += 1

            # Process and potentially notify
            if self.process_scan_result(result):
                notifications_sent += 1

        logger.info(
            f"Scan complete: {scanned} scanned, {buy_signals} buy signals, "
            f"{notifications_sent} notifications, {errors} errors"
        )

        # Send daily summary
        budget_status = self.portfolio_manager.get_budget_status()
        self.notifier.send_daily_summary(
            scanned,
            buy_signals,
            notifications_sent,
            budget_status
        )

        return {
            "scanned": scanned,
            "buy_signals": buy_signals,
            "notifications_sent": notifications_sent,
            "errors": errors,
            "budget_status": budget_status
        }


# Singleton instance
_stock_scanner_instance = None


def get_stock_scanner() -> StockScanner:
    """Get or create the StockScanner singleton."""
    global _stock_scanner_instance
    if _stock_scanner_instance is None:
        _stock_scanner_instance = StockScanner()
    return _stock_scanner_instance
