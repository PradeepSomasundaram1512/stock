"""
Notification System.
Handles console, desktop, and email notifications for buy signals.
"""

import logging
from typing import Dict, Any
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.config import (
    ENABLE_DESKTOP_NOTIFICATIONS,
    FINANCIAL_DISCLAIMER
)

logger = logging.getLogger(__name__)


class Notifier:
    """Manages notifications for buy signals."""

    def __init__(self):
        """Initialize the Notifier."""
        self.desktop_available = False
        self._init_desktop_notifications()

    def _init_desktop_notifications(self):
        """Initialize desktop notification capability."""
        if not ENABLE_DESKTOP_NOTIFICATIONS:
            logger.info("Desktop notifications disabled")
            return

        try:
            from plyer import notification
            self.plyer_notification = notification
            self.desktop_available = True
            logger.info("Desktop notifications enabled")
        except ImportError:
            logger.warning("plyer not available - desktop notifications disabled")
            self.desktop_available = False

    def send_buy_signal_notification(
        self,
        buy_signal: Dict[str, Any]
    ):
        """
        Send notification for a buy signal.

        Args:
            buy_signal: Formatted buy signal dictionary
        """
        # Always send console notification
        self._send_console_notification(buy_signal)

        # Send desktop notification if available
        if self.desktop_available:
            self._send_desktop_notification(buy_signal)

    def _send_console_notification(self, buy_signal: Dict[str, Any]):
        """
        Send console notification (print formatted message).

        Args:
            buy_signal: Buy signal dictionary
        """
        ticker = buy_signal.get('ticker', 'UNKNOWN')
        confidence = buy_signal.get('confidence', 0.0)
        suggested_amount = buy_signal.get('suggested_amount', 0.0)
        remaining_budget = buy_signal.get('remaining_budget', 0.0)
        latest_price = buy_signal.get('latest_price', 0.0)
        explanation = buy_signal.get('explanation', '')

        message = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                 🟢 BUY SIGNAL DETECTED 🟢                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

📈 STOCK: {ticker}
💰 Current Price: ${latest_price:.2f}
🎯 Confidence: {confidence:.1%}
💵 Suggested Investment: ${suggested_amount:.2f}
📊 Remaining Budget: ${remaining_budget:.2f}

REASONING:
{self._format_explanation(explanation)}

KEY SIGNALS:
"""

        for signal in buy_signal.get('key_signals', [])[:5]:
            message += f"  ✓ {signal}\n"

        message += "\n⚠️  RISK FACTORS:\n"
        for risk in buy_signal.get('risk_factors', [])[:3]:
            message += f"  ⚠ {risk}\n"

        message += f"\n{FINANCIAL_DISCLAIMER}\n"
        message += "="*66 + "\n"

        print(message)
        logger.info(f"Console notification sent for {ticker}")

    def _send_desktop_notification(self, buy_signal: Dict[str, Any]):
        """
        Send desktop notification.

        Args:
            buy_signal: Buy signal dictionary
        """
        if not self.desktop_available:
            return

        try:
            ticker = buy_signal.get('ticker', 'UNKNOWN')
            confidence = buy_signal.get('confidence', 0.0)
            suggested_amount = buy_signal.get('suggested_amount', 0.0)

            title = f"🟢 BUY Signal: {ticker}"
            message = (
                f"Confidence: {confidence:.1%}\n"
                f"Suggested: ${suggested_amount:.2f}\n"
                f"Not financial advice"
            )

            self.plyer_notification.notify(
                title=title,
                message=message,
                app_name="AI Stock Agent",
                timeout=10
            )

            logger.info(f"Desktop notification sent for {ticker}")

        except Exception as e:
            logger.error(f"Error sending desktop notification: {str(e)}")

    def _format_explanation(self, explanation: str, max_length: int = 300) -> str:
        """
        Format explanation text for display.

        Args:
            explanation: Full explanation text
            max_length: Maximum length

        Returns:
            Formatted explanation
        """
        if len(explanation) <= max_length:
            return explanation

        # Truncate and add ellipsis
        return explanation[:max_length] + "..."

    def send_error_notification(self, ticker: str, error_message: str):
        """
        Send error notification.

        Args:
            ticker: Stock ticker
            error_message: Error description
        """
        message = f"""
╔══════════════════════════════════════════════════════════════╗
║                    ❌ ANALYSIS ERROR ❌                       ║
╚══════════════════════════════════════════════════════════════╝

Stock: {ticker}
Error: {error_message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The analysis could not be completed. Please check logs for details.
"""
        print(message)
        logger.error(f"Error notification sent for {ticker}: {error_message}")

    def send_daily_summary(
        self,
        scanned_count: int,
        buy_signals: int,
        notifications_sent: int,
        budget_status: Dict[str, float]
    ):
        """
        Send daily summary notification.

        Args:
            scanned_count: Number of stocks scanned
            buy_signals: Number of buy signals detected
            notifications_sent: Number of notifications sent
            budget_status: Current budget status
        """
        message = f"""
╔══════════════════════════════════════════════════════════════╗
║                    📊 DAILY SUMMARY 📊                        ║
╚══════════════════════════════════════════════════════════════╝

Date: {datetime.now().strftime('%Y-%m-%d')}

SCAN RESULTS:
  • Stocks Scanned: {scanned_count}
  • Buy Signals Found: {buy_signals}
  • Notifications Sent: {notifications_sent}

BUDGET STATUS:
  • Total Budget: ${budget_status.get('total', 0):.2f}
  • Spent This Month: ${budget_status.get('spent', 0):.2f}
  • Remaining: ${budget_status.get('remaining', 0):.2f}

"""
        print(message)
        logger.info("Daily summary notification sent")


# Singleton instance
_notifier_instance = None


def get_notifier() -> Notifier:
    """Get or create the Notifier singleton."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = Notifier()
    return _notifier_instance
