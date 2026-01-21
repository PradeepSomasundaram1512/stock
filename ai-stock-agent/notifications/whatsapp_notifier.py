"""
WhatsApp Notification System using Twilio
Sends stock alerts via WhatsApp (FREE alternative to SMS!)
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# WhatsApp Configuration
WHATSAPP_ENABLED = os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true'
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Twilio sandbox
YOUR_WHATSAPP_NUMBER = os.getenv('YOUR_WHATSAPP_NUMBER', '')  # Format: whatsapp:+1234567890

class WhatsAppNotifier:
    """Send stock alerts via WhatsApp using Twilio"""

    def __init__(self):
        """Initialize WhatsApp notifier"""
        self.enabled = WHATSAPP_ENABLED
        self.client = None

        if self.enabled:
            try:
                from twilio.rest import Client
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                logger.info("✓ WhatsApp notifications enabled")
            except ImportError:
                logger.warning("Twilio not installed. Run: pip install twilio")
                self.enabled = False
            except Exception as e:
                logger.error(f"Error initializing Twilio for WhatsApp: {e}")
                self.enabled = False
        else:
            logger.info("WhatsApp notifications disabled (set WHATSAPP_ENABLED=true to enable)")

    def send_whatsapp(self, message: str) -> bool:
        """
        Send WhatsApp message

        Args:
            message: Message text to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"[WHATSAPP DISABLED] Would send: {message[:100]}...")
            return False

        if not YOUR_WHATSAPP_NUMBER:
            logger.error("YOUR_WHATSAPP_NUMBER not configured in .env")
            return False

        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=YOUR_WHATSAPP_NUMBER
            )
            logger.info(f"✓ WhatsApp sent successfully (SID: {message_obj.sid})")
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp: {e}")
            return False

    def send_market_open_alert(self, top_buys: List[Dict], top_sells: List[Dict]) -> bool:
        """
        Send morning market alert with top opportunities

        Args:
            top_buys: List of top BUY recommendations
            top_sells: List of top SELL recommendations
        """
        message = f"🌅 *MARKET OPEN ALERT*\n"
        message += f"_{datetime.now().strftime('%b %d, %Y')}_\n\n"

        # Top BUY opportunities
        if top_buys:
            message += "🟢 *TOP BUYS:*\n"
            for i, stock in enumerate(top_buys[:3], 1):
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                target = stock.get('price_target')
                stop = stock.get('stop_loss')

                message += f"{i}. *{ticker}* @ ${price:.2f}\n"
                message += f"   Confidence: {confidence:.0f}%\n"
                if target:
                    gain_pct = ((target / price) - 1) * 100
                    message += f"   🎯 Target: ${target:.2f} (+{gain_pct:.1f}%)\n"
                if stop:
                    loss_pct = ((stop / price) - 1) * 100
                    message += f"   ⛔ Stop: ${stop:.2f} ({loss_pct:.1f}%)\n"
                message += "\n"

        # Top SELL opportunities
        if top_sells:
            message += "🔴 *TOP SELLS:*\n"
            for i, stock in enumerate(top_sells[:3], 1):
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                message += f"{i}. *{ticker}* @ ${price:.2f} ({confidence:.0f}%)\n"
            message += "\n"

        message += "_View full analysis in dashboard_"

        return self.send_whatsapp(message)

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
        message = f"🚨 *POSITION ALERT: {ticker}*\n\n"
        message += f"*Action:* {action}\n"
        message += f"*Price:* ${current_price:.2f}\n"

        if entry_price and profit_pct is not None:
            symbol = "📈" if profit_pct > 0 else "📉"
            message += f"*Entry:* ${entry_price:.2f}\n"
            message += f"{symbol} *P/L:* {profit_pct:+.2f}%\n"

        message += f"\n*Reason:* {reason}"

        return self.send_whatsapp(message)

    def send_target_hit_alert(self, ticker: str, entry_price: float, target_price: float,
                             current_price: float, profit_pct: float) -> bool:
        """Send alert when price target is hit"""
        message = f"🎯 *TARGET HIT: {ticker}*\n\n"
        message += f"Entry: ${entry_price:.2f}\n"
        message += f"Target: ${target_price:.2f}\n"
        message += f"Current: ${current_price:.2f}\n"
        message += f"📈 *Profit: +{profit_pct:.2f}%*\n\n"
        message += "💰 *Consider taking profits!*"

        return self.send_whatsapp(message)

    def send_stop_loss_alert(self, ticker: str, entry_price: float, stop_loss: float,
                            current_price: float, loss_pct: float) -> bool:
        """Send alert when stop loss is hit"""
        message = f"⛔ *STOP LOSS: {ticker}*\n\n"
        message += f"Entry: ${entry_price:.2f}\n"
        message += f"Stop: ${stop_loss:.2f}\n"
        message += f"Current: ${current_price:.2f}\n"
        message += f"📉 *Loss: {loss_pct:.2f}%*\n\n"
        message += "⚠️ *Exit position to limit losses!*"

        return self.send_whatsapp(message)

    def send_daily_summary(self, total_positions: int, winning: int, losing: int,
                          total_pnl_pct: float, best_performer: str = None) -> bool:
        """Send end-of-day summary"""
        message = f"📊 *DAILY SUMMARY*\n"
        message += f"_{datetime.now().strftime('%b %d')}_\n\n"
        message += f"Positions: {total_positions}\n"
        message += f"Winners: {winning} | Losers: {losing}\n"

        symbol = "📈" if total_pnl_pct >= 0 else "📉"
        message += f"{symbol} *Total P/L: {total_pnl_pct:+.2f}%*\n"

        if best_performer:
            message += f"\n⭐ *Top:* {best_performer}"

        return self.send_whatsapp(message)

    def send_mtf_alert(self, ticker: str, signal: str, confidence: float, alignment: int) -> bool:
        """Send multi-timeframe analysis alert"""
        symbol = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"

        message = f"{symbol} *MULTI-TIMEFRAME ALERT*\n\n"
        message += f"*{ticker}*\n"
        message += f"Signal: *{signal}*\n"
        message += f"Confidence: {confidence*100:.0f}%\n"
        message += f"Alignment: {alignment}/3 timeframes\n\n"

        if confidence >= 0.90:
            message += "🔥 *HIGH CONVICTION SIGNAL!*"
        elif confidence >= 0.75:
            message += "💪 Strong signal across timeframes"
        else:
            message += "⚠️ Mixed signals - trade carefully"

        return self.send_whatsapp(message)


# Singleton instance
_whatsapp_notifier = None

def get_whatsapp_notifier() -> WhatsAppNotifier:
    """Get or create WhatsApp notifier instance"""
    global _whatsapp_notifier
    if _whatsapp_notifier is None:
        _whatsapp_notifier = WhatsAppNotifier()
    return _whatsapp_notifier
