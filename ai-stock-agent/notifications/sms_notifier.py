"""
SMS Notification System using Twilio
Sends stock alerts via SMS
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# SMS Configuration
SMS_ENABLED = os.getenv('SMS_ENABLED', 'false').lower() == 'true'
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
YOUR_PHONE_NUMBER = os.getenv('YOUR_PHONE_NUMBER', '')

class SMSNotifier:
    """Send stock alerts via SMS using Twilio"""

    def __init__(self):
        """Initialize SMS notifier"""
        self.enabled = SMS_ENABLED
        self.client = None

        if self.enabled:
            try:
                from twilio.rest import Client
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                logger.info("✓ SMS notifications enabled")
            except ImportError:
                logger.warning("Twilio not installed. Run: pip install twilio")
                self.enabled = False
            except Exception as e:
                logger.error(f"Error initializing Twilio: {e}")
                self.enabled = False
        else:
            logger.info("SMS notifications disabled (set SMS_ENABLED=true to enable)")

    def send_sms(self, message: str) -> bool:
        """
        Send SMS message

        Args:
            message: Message text to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"[SMS DISABLED] Would send: {message}")
            return False

        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=YOUR_PHONE_NUMBER
            )
            logger.info(f"✓ SMS sent successfully (SID: {message_obj.sid})")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def send_market_open_alert(self, top_buys: List[Dict], top_sells: List[Dict]) -> bool:
        """
        Send morning market alert with top opportunities

        Args:
            top_buys: List of top BUY recommendations
            top_sells: List of top SELL recommendations
        """
        message = f"🌅 MARKET OPEN ALERT - {datetime.now().strftime('%b %d, %Y')}\n\n"

        # Top BUY opportunities
        if top_buys:
            message += "🟢 TOP BUYS:\n"
            for i, stock in enumerate(top_buys[:3], 1):
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                message += f"{i}. {ticker} @ ${price:.2f} ({confidence:.0f}%)\n"
            message += "\n"

        # Top SELL opportunities
        if top_sells:
            message += "🔴 TOP SELLS:\n"
            for i, stock in enumerate(top_sells[:3], 1):
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                message += f"{i}. {ticker} @ ${price:.2f} ({confidence:.0f}%)\n"
            message += "\n"

        message += "View full report in your dashboard."

        return self.send_sms(message)

    def send_position_alert(self, ticker: str, action: str, reason: str, current_price: float,
                           entry_price: float = None, profit_pct: float = None) -> bool:
        """
        Send alert about position update

        Args:
            ticker: Stock ticker
            action: Action to take (SELL, HOLD, etc.)
            reason: Reason for alert
            current_price: Current stock price
            entry_price: Entry price (for profit calculation)
            profit_pct: Profit percentage
        """
        message = f"🚨 POSITION ALERT: {ticker}\n\n"
        message += f"Action: {action}\n"
        message += f"Price: ${current_price:.2f}\n"

        if entry_price and profit_pct is not None:
            symbol = "📈" if profit_pct > 0 else "📉"
            message += f"Entry: ${entry_price:.2f}\n"
            message += f"{symbol} P/L: {profit_pct:+.2f}%\n"

        message += f"\nReason: {reason}"

        return self.send_sms(message)

    def send_target_hit_alert(self, ticker: str, entry_price: float, target_price: float,
                             current_price: float, profit_pct: float) -> bool:
        """Send alert when price target is hit"""
        message = f"🎯 TARGET HIT: {ticker}\n\n"
        message += f"Entry: ${entry_price:.2f}\n"
        message += f"Target: ${target_price:.2f}\n"
        message += f"Current: ${current_price:.2f}\n"
        message += f"📈 Profit: +{profit_pct:.2f}%\n\n"
        message += "Consider taking profits!"

        return self.send_sms(message)

    def send_stop_loss_alert(self, ticker: str, entry_price: float, stop_loss: float,
                            current_price: float, loss_pct: float) -> bool:
        """Send alert when stop loss is hit"""
        message = f"⛔ STOP LOSS: {ticker}\n\n"
        message += f"Entry: ${entry_price:.2f}\n"
        message += f"Stop: ${stop_loss:.2f}\n"
        message += f"Current: ${current_price:.2f}\n"
        message += f"📉 Loss: {loss_pct:.2f}%\n\n"
        message += "Exit position to limit losses!"

        return self.send_sms(message)

    def send_daily_summary(self, total_positions: int, winning: int, losing: int,
                          total_pnl_pct: float, best_performer: str = None) -> bool:
        """Send end-of-day summary"""
        message = f"📊 DAILY SUMMARY - {datetime.now().strftime('%b %d')}\n\n"
        message += f"Positions: {total_positions}\n"
        message += f"Winners: {winning} | Losers: {losing}\n"

        symbol = "📈" if total_pnl_pct >= 0 else "📉"
        message += f"{symbol} Total P/L: {total_pnl_pct:+.2f}%\n"

        if best_performer:
            message += f"\n⭐ Top: {best_performer}"

        return self.send_sms(message)


# Singleton instance
_sms_notifier = None

def get_sms_notifier() -> SMSNotifier:
    """Get or create SMS notifier instance"""
    global _sms_notifier
    if _sms_notifier is None:
        _sms_notifier = SMSNotifier()
    return _sms_notifier
