"""
Discord Webhook Notification System
Sends stock alerts via Discord webhooks (100% FREE!)
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
import requests

logger = logging.getLogger(__name__)

# Discord Configuration
DISCORD_ENABLED = os.getenv('DISCORD_ENABLED', 'false').lower() == 'true'
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

class DiscordNotifier:
    """Send stock alerts via Discord webhooks"""

    def __init__(self):
        """Initialize Discord notifier"""
        self.enabled = DISCORD_ENABLED
        self.webhook_url = DISCORD_WEBHOOK_URL

        if self.enabled:
            if not self.webhook_url:
                logger.warning("Discord enabled but DISCORD_WEBHOOK_URL not set in .env")
                self.enabled = False
            else:
                logger.info("✓ Discord notifications enabled")
        else:
            logger.info("Discord notifications disabled (set DISCORD_ENABLED=true to enable)")

    def send_discord(self, content: str = None, embed: Dict[str, Any] = None) -> bool:
        """
        Send Discord message

        Args:
            content: Plain text message (optional if embed provided)
            embed: Rich embed object (optional if content provided)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"[DISCORD DISABLED] Would send: {content or 'embedded message'}")
            return False

        try:
            payload = {}
            if content:
                payload['content'] = content
            if embed:
                payload['embeds'] = [embed]

            response = requests.post(self.webhook_url, json=payload)

            if response.status_code == 204:
                logger.info("✓ Discord message sent successfully")
                return True
            else:
                logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False

    def send_market_open_alert(self, top_buys: List[Dict], top_sells: List[Dict]) -> bool:
        """
        Send morning market alert with top opportunities

        Args:
            top_buys: List of top BUY recommendations
            top_sells: List of top SELL recommendations
        """
        embed = {
            "title": "🌅 MARKET OPEN ALERT",
            "description": f"_{datetime.now().strftime('%b %d, %Y')}_",
            "color": 0x00FF00,  # Green
            "fields": [],
            "footer": {
                "text": "AI Stock Decision Agent"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        # Top BUY opportunities
        if top_buys:
            buy_text = ""
            for i, stock in enumerate(top_buys[:3], 1):
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                target = stock.get('price_target')
                stop = stock.get('stop_loss')

                buy_text += f"**{i}. {ticker}** @ ${price:.2f}\n"
                buy_text += f"   Confidence: {confidence:.0f}%\n"

                if target:
                    gain_pct = ((target / price) - 1) * 100
                    buy_text += f"   🎯 Target: ${target:.2f} (+{gain_pct:.1f}%)\n"
                if stop:
                    loss_pct = ((stop / price) - 1) * 100
                    buy_text += f"   ⛔ Stop: ${stop:.2f} ({loss_pct:.1f}%)\n"
                buy_text += "\n"

            embed["fields"].append({
                "name": "🟢 TOP BUYS",
                "value": buy_text.strip(),
                "inline": False
            })

        # Top SELL opportunities
        if top_sells:
            sell_text = ""
            for i, stock in enumerate(top_sells[:3], 1):
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                sell_text += f"**{i}. {ticker}** @ ${price:.2f} ({confidence:.0f}%)\n"

            embed["fields"].append({
                "name": "🔴 TOP SELLS",
                "value": sell_text.strip(),
                "inline": False
            })

        return self.send_discord(embed=embed)

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
        color = 0xFF0000 if action == "SELL" else 0xFFFF00 if action == "HOLD" else 0x00FF00

        embed = {
            "title": f"🚨 POSITION ALERT: {ticker}",
            "color": color,
            "fields": [
                {
                    "name": "Action",
                    "value": action,
                    "inline": True
                },
                {
                    "name": "Current Price",
                    "value": f"${current_price:.2f}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "AI Stock Decision Agent"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        if entry_price and profit_pct is not None:
            symbol = "📈" if profit_pct > 0 else "📉"
            embed["fields"].extend([
                {
                    "name": "Entry Price",
                    "value": f"${entry_price:.2f}",
                    "inline": True
                },
                {
                    "name": f"{symbol} P/L",
                    "value": f"{profit_pct:+.2f}%",
                    "inline": True
                }
            ])

        embed["fields"].append({
            "name": "Reason",
            "value": reason,
            "inline": False
        })

        return self.send_discord(embed=embed)

    def send_target_hit_alert(self, ticker: str, entry_price: float, target_price: float,
                             current_price: float, profit_pct: float) -> bool:
        """Send alert when price target is hit"""
        embed = {
            "title": f"🎯 TARGET HIT: {ticker}",
            "description": "💰 **Consider taking profits!**",
            "color": 0x00FF00,  # Green
            "fields": [
                {
                    "name": "Entry",
                    "value": f"${entry_price:.2f}",
                    "inline": True
                },
                {
                    "name": "Target",
                    "value": f"${target_price:.2f}",
                    "inline": True
                },
                {
                    "name": "Current",
                    "value": f"${current_price:.2f}",
                    "inline": True
                },
                {
                    "name": "📈 Profit",
                    "value": f"+{profit_pct:.2f}%",
                    "inline": False
                }
            ],
            "footer": {
                "text": "AI Stock Decision Agent"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        return self.send_discord(embed=embed)

    def send_stop_loss_alert(self, ticker: str, entry_price: float, stop_loss: float,
                            current_price: float, loss_pct: float) -> bool:
        """Send alert when stop loss is hit"""
        embed = {
            "title": f"⛔ STOP LOSS: {ticker}",
            "description": "⚠️ **Exit position to limit losses!**",
            "color": 0xFF0000,  # Red
            "fields": [
                {
                    "name": "Entry",
                    "value": f"${entry_price:.2f}",
                    "inline": True
                },
                {
                    "name": "Stop",
                    "value": f"${stop_loss:.2f}",
                    "inline": True
                },
                {
                    "name": "Current",
                    "value": f"${current_price:.2f}",
                    "inline": True
                },
                {
                    "name": "📉 Loss",
                    "value": f"{loss_pct:.2f}%",
                    "inline": False
                }
            ],
            "footer": {
                "text": "AI Stock Decision Agent"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        return self.send_discord(embed=embed)

    def send_daily_summary(self, total_positions: int, winning: int, losing: int,
                          total_pnl_pct: float, best_performer: str = None) -> bool:
        """Send end-of-day summary"""
        color = 0x00FF00 if total_pnl_pct >= 0 else 0xFF0000
        symbol = "📈" if total_pnl_pct >= 0 else "📉"

        embed = {
            "title": "📊 DAILY SUMMARY",
            "description": f"_{datetime.now().strftime('%b %d')}_",
            "color": color,
            "fields": [
                {
                    "name": "Positions",
                    "value": str(total_positions),
                    "inline": True
                },
                {
                    "name": "Winners",
                    "value": str(winning),
                    "inline": True
                },
                {
                    "name": "Losers",
                    "value": str(losing),
                    "inline": True
                },
                {
                    "name": f"{symbol} Total P/L",
                    "value": f"{total_pnl_pct:+.2f}%",
                    "inline": False
                }
            ],
            "footer": {
                "text": "AI Stock Decision Agent"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        if best_performer:
            embed["fields"].append({
                "name": "⭐ Top Performer",
                "value": best_performer,
                "inline": False
            })

        return self.send_discord(embed=embed)

    def send_mtf_alert(self, ticker: str, signal: str, confidence: float, alignment: int) -> bool:
        """Send multi-timeframe analysis alert"""
        if signal == 'BUY':
            color = 0x00FF00
            symbol = "🟢"
        elif signal == 'SELL':
            color = 0xFF0000
            symbol = "🔴"
        else:
            color = 0xFFFF00
            symbol = "🟡"

        description = ""
        if confidence >= 0.90:
            description = "🔥 **HIGH CONVICTION SIGNAL!**"
        elif confidence >= 0.75:
            description = "💪 Strong signal across timeframes"
        else:
            description = "⚠️ Mixed signals - trade carefully"

        embed = {
            "title": f"{symbol} MULTI-TIMEFRAME ALERT",
            "description": description,
            "color": color,
            "fields": [
                {
                    "name": "Ticker",
                    "value": f"**{ticker}**",
                    "inline": True
                },
                {
                    "name": "Signal",
                    "value": f"**{signal}**",
                    "inline": True
                },
                {
                    "name": "Confidence",
                    "value": f"{confidence*100:.0f}%",
                    "inline": True
                },
                {
                    "name": "Alignment",
                    "value": f"{alignment}/3 timeframes",
                    "inline": True
                }
            ],
            "footer": {
                "text": "AI Stock Decision Agent"
            },
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        return self.send_discord(embed=embed)


# Singleton instance
_discord_notifier = None

def get_discord_notifier() -> DiscordNotifier:
    """Get or create Discord notifier instance"""
    global _discord_notifier
    if _discord_notifier is None:
        _discord_notifier = DiscordNotifier()
    return _discord_notifier
