"""
Email Notification System
Sends stock alerts via email (alternative to SMS)
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Email Configuration
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')  # Gmail by default
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')  # App password for Gmail
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', EMAIL_ADDRESS)

class EmailNotifier:
    """Send stock alerts via email"""

    def __init__(self):
        """Initialize email notifier"""
        self.enabled = EMAIL_ENABLED
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.email = EMAIL_ADDRESS
        self.password = EMAIL_PASSWORD
        self.recipient = RECIPIENT_EMAIL

        if self.enabled:
            if not self.email or not self.password:
                logger.warning("Email credentials not set. Email notifications disabled.")
                self.enabled = False
            else:
                logger.info("✓ Email notifications enabled")
        else:
            logger.info("Email notifications disabled (set EMAIL_ENABLED=true to enable)")

    def send_email(self, subject: str, body: str, html: bool = False) -> bool:
        """
        Send email

        Args:
            subject: Email subject
            body: Email body (text or HTML)
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.info(f"[EMAIL DISABLED] Would send: {subject}")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email
            msg['To'] = self.recipient

            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)

            logger.info(f"✓ Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_market_open_alert(self, top_buys: List[Dict], top_sells: List[Dict]) -> bool:
        """Send morning market alert with top opportunities"""
        subject = f"🌅 Market Open Alert - {datetime.now().strftime('%b %d, %Y')}"

        body = self._format_market_open_html(top_buys, top_sells)
        return self.send_email(subject, body, html=True)

    def _format_market_open_html(self, top_buys: List[Dict], top_sells: List[Dict]) -> str:
        """Format market open alert as HTML"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">🌅 Market Open Alert</h2>
            <p style="color: #7f8c8d;">{datetime.now().strftime('%B %d, %Y - %I:%M %p')}</p>
        """

        # Top BUY opportunities
        if top_buys:
            html += """
            <h3 style="color: #27ae60;">🟢 TOP BUY OPPORTUNITIES</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #ecf0f1;">
                    <th style="padding: 10px; text-align: left;">Ticker</th>
                    <th style="padding: 10px; text-align: right;">Price</th>
                    <th style="padding: 10px; text-align: right;">Confidence</th>
                    <th style="padding: 10px; text-align: left;">Reason</th>
                </tr>
            """
            for stock in top_buys[:5]:
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                reason = stock.get('reason', 'Strong signals')[:40]
                html += f"""
                <tr style="border-bottom: 1px solid #ecf0f1;">
                    <td style="padding: 10px; font-weight: bold;">{ticker}</td>
                    <td style="padding: 10px; text-align: right;">${price:.2f}</td>
                    <td style="padding: 10px; text-align: right; color: #27ae60;">{confidence:.0f}%</td>
                    <td style="padding: 10px; font-size: 0.9em;">{reason}</td>
                </tr>
                """
            html += "</table>"

        # Top SELL opportunities
        if top_sells:
            html += """
            <h3 style="color: #e74c3c;">🔴 TOP SELL SIGNALS</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #ecf0f1;">
                    <th style="padding: 10px; text-align: left;">Ticker</th>
                    <th style="padding: 10px; text-align: right;">Price</th>
                    <th style="padding: 10px; text-align: right;">Confidence</th>
                    <th style="padding: 10px; text-align: left;">Reason</th>
                </tr>
            """
            for stock in top_sells[:5]:
                ticker = stock['ticker']
                price = stock.get('price', 0)
                confidence = stock.get('confidence', 0) * 100
                reason = stock.get('reason', 'Bearish signals')[:40]
                html += f"""
                <tr style="border-bottom: 1px solid #ecf0f1;">
                    <td style="padding: 10px; font-weight: bold;">{ticker}</td>
                    <td style="padding: 10px; text-align: right;">${price:.2f}</td>
                    <td style="padding: 10px; text-align: right; color: #e74c3c;">{confidence:.0f}%</td>
                    <td style="padding: 10px; font-size: 0.9em;">{reason}</td>
                </tr>
                """
            html += "</table>"

        html += """
            <p style="margin-top: 30px; font-size: 0.9em; color: #7f8c8d;">
                <em>This is an automated alert from your AI Stock Analyzer.</em>
            </p>
        </body>
        </html>
        """
        return html

    def send_position_alert(self, ticker: str, action: str, reason: str, current_price: float,
                           entry_price: float = None, profit_pct: float = None) -> bool:
        """Send alert about position update"""
        subject = f"🚨 Position Alert: {ticker} - {action}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>🚨 Position Alert: {ticker}</h2>
            <p><strong>Action:</strong> <span style="color: #e74c3c; font-size: 1.2em;">{action}</span></p>
            <p><strong>Current Price:</strong> ${current_price:.2f}</p>
        """

        if entry_price and profit_pct is not None:
            color = "#27ae60" if profit_pct > 0 else "#e74c3c"
            symbol = "📈" if profit_pct > 0 else "📉"
            body += f"""
            <p><strong>Entry Price:</strong> ${entry_price:.2f}</p>
            <p><strong>{symbol} Profit/Loss:</strong> <span style="color: {color}; font-weight: bold;">{profit_pct:+.2f}%</span></p>
            """

        body += f"""
            <p><strong>Reason:</strong> {reason}</p>
            <p style="margin-top: 30px; font-size: 0.9em; color: #7f8c8d;">
                <em>Act quickly - market conditions may change!</em>
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)

    def send_target_hit_alert(self, ticker: str, entry_price: float, target_price: float,
                             current_price: float, profit_pct: float) -> bool:
        """Send alert when price target is hit"""
        subject = f"🎯 Target Hit: {ticker} (+{profit_pct:.1f}%)"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #27ae60;">🎯 Price Target Hit: {ticker}</h2>
            <table style="margin: 20px 0;">
                <tr><td><strong>Entry Price:</strong></td><td style="padding-left: 20px;">${entry_price:.2f}</td></tr>
                <tr><td><strong>Target Price:</strong></td><td style="padding-left: 20px;">${target_price:.2f}</td></tr>
                <tr><td><strong>Current Price:</strong></td><td style="padding-left: 20px;">${current_price:.2f}</td></tr>
                <tr><td><strong>📈 Profit:</strong></td><td style="padding-left: 20px; color: #27ae60; font-weight: bold;">+{profit_pct:.2f}%</td></tr>
            </table>
            <p style="background-color: #d4edda; padding: 15px; border-left: 4px solid #27ae60;">
                <strong>💰 Consider taking profits!</strong> Your target has been reached.
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)

    def send_stop_loss_alert(self, ticker: str, entry_price: float, stop_loss: float,
                            current_price: float, loss_pct: float) -> bool:
        """Send alert when stop loss is hit"""
        subject = f"⛔ Stop Loss: {ticker} ({loss_pct:.1f}%)"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #e74c3c;">⛔ Stop Loss Hit: {ticker}</h2>
            <table style="margin: 20px 0;">
                <tr><td><strong>Entry Price:</strong></td><td style="padding-left: 20px;">${entry_price:.2f}</td></tr>
                <tr><td><strong>Stop Loss:</strong></td><td style="padding-left: 20px;">${stop_loss:.2f}</td></tr>
                <tr><td><strong>Current Price:</strong></td><td style="padding-left: 20px;">${current_price:.2f}</td></tr>
                <tr><td><strong>📉 Loss:</strong></td><td style="padding-left: 20px; color: #e74c3c; font-weight: bold;">{loss_pct:.2f}%</td></tr>
            </table>
            <p style="background-color: #f8d7da; padding: 15px; border-left: 4px solid #e74c3c;">
                <strong>⚠️ Exit position immediately!</strong> Stop loss triggered to limit further losses.
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)

    def send_daily_summary(self, total_positions: int, winning: int, losing: int,
                          total_pnl_pct: float, best_performer: str = None, worst_performer: str = None) -> bool:
        """Send end-of-day summary"""
        subject = f"📊 Daily Summary - {datetime.now().strftime('%b %d')} ({total_pnl_pct:+.2f}%)"

        color = "#27ae60" if total_pnl_pct >= 0 else "#e74c3c"
        symbol = "📈" if total_pnl_pct >= 0 else "📉"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>📊 Daily Trading Summary</h2>
            <p style="color: #7f8c8d;">{datetime.now().strftime('%B %d, %Y')}</p>

            <table style="width: 100%; margin: 20px 0; border-collapse: collapse;">
                <tr style="background-color: #ecf0f1;">
                    <td style="padding: 10px;"><strong>Total Positions</strong></td>
                    <td style="padding: 10px; text-align: right;">{total_positions}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>Winners</strong></td>
                    <td style="padding: 10px; text-align: right; color: #27ae60;">{winning}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>Losers</strong></td>
                    <td style="padding: 10px; text-align: right; color: #e74c3c;">{losing}</td>
                </tr>
                <tr style="background-color: #ecf0f1; font-size: 1.2em;">
                    <td style="padding: 15px;"><strong>{symbol} Total P/L</strong></td>
                    <td style="padding: 15px; text-align: right; color: {color}; font-weight: bold;">{total_pnl_pct:+.2f}%</td>
                </tr>
            </table>
        """

        if best_performer:
            body += f"<p><strong>⭐ Best Performer:</strong> {best_performer}</p>"
        if worst_performer:
            body += f"<p><strong>📉 Worst Performer:</strong> {worst_performer}</p>"

        body += """
            <p style="margin-top: 30px; font-size: 0.9em; color: #7f8c8d;">
                <em>Rest well. Tomorrow is a new trading day!</em>
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)


# Singleton instance
_email_notifier = None

def get_email_notifier() -> EmailNotifier:
    """Get or create email notifier instance"""
    global _email_notifier
    if _email_notifier is None:
        _email_notifier = EmailNotifier()
    return _email_notifier
