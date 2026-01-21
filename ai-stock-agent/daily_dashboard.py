"""
Daily Trading Dashboard
Analyzes market, manages portfolio, provides daily BUY/SELL/HOLD recommendations
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import yfinance as yf

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from portfolio_manager import get_portfolio_manager
from market_scanner import MarketScanner, MARKET_UNIVERSE
from enhancements.multi_timeframe import get_mtf_analyzer
from notifications.discord_notifier import get_discord_notifier
from notifications.email_notifier import get_email_notifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyDashboard:
    """Daily trading dashboard with portfolio management"""

    def __init__(self, monthly_budget: float = 1000):
        """Initialize dashboard"""
        self.portfolio = get_portfolio_manager(monthly_budget)
        self.scanner = MarketScanner(monthly_budget)
        self.mtf = get_mtf_analyzer()
        self.discord = get_discord_notifier()
        self.email = get_email_notifier()

    def check_existing_positions(self) -> List[Dict[str, Any]]:
        """
        Check all open positions and provide recommendations

        Returns:
            List of position recommendations
        """
        status = self.portfolio.get_monthly_status()
        positions = status.get('open_positions', [])

        if not positions:
            logger.info("No open positions to check")
            return []

        recommendations = []

        logger.info(f"\n{'='*70}")
        logger.info("CHECKING EXISTING POSITIONS")
        logger.info(f"{'='*70}")

        for pos in positions:
            ticker = pos['ticker']
            entry_price = pos['entry_price']
            shares = pos['shares']
            target = pos.get('target_price', 0)
            stop = pos.get('stop_loss', 0)

            try:
                # Get current price
                stock = yf.Ticker(ticker)
                current_price = float(stock.info.get('currentPrice', stock.info.get('regularMarketPrice', 0)))

                if current_price == 0:
                    logger.warning(f"  Could not get price for {ticker}")
                    continue

                # Calculate P/L
                profit_loss = (current_price - entry_price) * shares
                profit_loss_pct = ((current_price / entry_price) - 1) * 100

                logger.info(f"\n{ticker}:")
                logger.info(f"  Entry: ${entry_price:.2f} | Current: ${current_price:.2f}")
                logger.info(f"  P/L: ${profit_loss:+.2f} ({profit_loss_pct:+.2f}%)")

                # Determine recommendation
                recommendation = "HOLD"
                reason = "Position within normal range"
                action_needed = False

                # Check target hit
                if target and current_price >= target:
                    recommendation = "SELL"
                    reason = f"🎯 Target hit! (${target:.2f})"
                    action_needed = True

                # Check stop loss
                elif stop and current_price <= stop:
                    recommendation = "SELL"
                    reason = f"⛔ Stop loss triggered! (${stop:.2f})"
                    action_needed = True

                # Check for large profit (>5%)
                elif profit_loss_pct >= 5:
                    recommendation = "CONSIDER SELL"
                    reason = f"📈 Up {profit_loss_pct:.1f}% - consider taking profits"

                # Check for large loss (>3%)
                elif profit_loss_pct <= -3:
                    recommendation = "CONSIDER SELL"
                    reason = f"📉 Down {profit_loss_pct:.1f}% - consider cutting losses"

                # Re-analyze with multi-timeframe
                else:
                    mtf_result = self.mtf.analyze(ticker)
                    if not mtf_result.get('error'):
                        signal = mtf_result['overall_signal']
                        confidence = mtf_result['confidence']

                        if signal == 'SELL' and confidence >= 0.75:
                            recommendation = "CONSIDER SELL"
                            reason = f"Multi-timeframe turned bearish ({confidence*100:.0f}% confidence)"
                        elif signal == 'BUY' and confidence >= 0.85:
                            recommendation = "HOLD STRONG"
                            reason = f"Still bullish ({confidence*100:.0f}% confidence)"

                logger.info(f"  💡 {recommendation}: {reason}")

                recommendations.append({
                    'ticker': ticker,
                    'action': recommendation,
                    'reason': reason,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'profit_loss': profit_loss,
                    'profit_loss_pct': profit_loss_pct,
                    'action_needed': action_needed,
                    'shares': shares
                })

            except Exception as e:
                logger.error(f"  Error checking {ticker}: {e}")
                continue

        return recommendations

    def find_new_opportunities(self, max_positions: int = 3) -> List[Dict[str, Any]]:
        """
        Find new buying opportunities

        Args:
            max_positions: Maximum number of positions to suggest

        Returns:
            List of buy opportunities
        """
        status = self.portfolio.get_monthly_status()
        available_cash = status['current_cash']
        num_open_positions = status['num_positions']

        logger.info(f"\n{'='*70}")
        logger.info("SCANNING FOR NEW OPPORTUNITIES")
        logger.info(f"Available Cash: ${available_cash:.2f}")
        logger.info(f"Open Positions: {num_open_positions}/{max_positions}")
        logger.info(f"{'='*70}")

        if num_open_positions >= max_positions:
            logger.info("✋ Maximum positions reached. Close a position before opening new ones.")
            return []

        if available_cash < 50:  # Need at least $50 to open position
            logger.info("✋ Insufficient cash for new positions")
            return []

        # Scan market for opportunities
        results = self.scanner.scan_market(top_n=10)
        top_buys = results['buys']

        if not top_buys:
            logger.info("No strong BUY signals found today")
            return []

        # Filter for positions we can afford and diversify sectors
        open_tickers = [pos['ticker'] for pos in status['open_positions']]
        open_sectors = [pos.get('sector') for pos in status['open_positions']]

        opportunities = []

        for buy in top_buys:
            ticker = buy['ticker']
            price = buy['price']
            confidence = buy['confidence']

            # Skip if already have position
            if ticker in open_tickers:
                continue

            # Calculate how many shares we can buy (use 30-40% of available cash per position)
            allocation = min(available_cash * 0.35, available_cash / (max_positions - num_open_positions))
            shares = int(allocation / price)

            if shares < 1:
                continue

            cost = shares * price

            # Check sector diversification
            sector = self._get_sector(ticker)
            if sector in open_sectors and len(opportunities) > 0:
                logger.info(f"  Skipping {ticker} - already have {sector} exposure")
                continue

            opportunities.append({
                'ticker': ticker,
                'price': price,
                'shares': shares,
                'cost': cost,
                'confidence': confidence,
                'sector': sector,
                'target': buy.get('price_target'),
                'stop': buy.get('stop_loss'),
                'explanation': buy.get('explanation', '')
            })

            logger.info(f"  🟢 BUY: {ticker} @ ${price:.2f} x {shares} shares = ${cost:.2f}")
            logger.info(f"     Confidence: {confidence*100:.0f}% | Sector: {sector}")

            # Limit to spaces available
            if len(opportunities) >= (max_positions - num_open_positions):
                break

        return opportunities

    def _get_sector(self, ticker: str) -> str:
        """Get stock sector"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('sector', 'Unknown')
        except:
            return 'Unknown'

    def generate_daily_report(self, position_checks: List[Dict], new_opportunities: List[Dict]) -> str:
        """Generate daily trading report"""
        status = self.portfolio.get_monthly_status()
        perf = self.portfolio.get_performance_summary()

        report = f"\n{'='*70}\n"
        report += f"📊 DAILY TRADING DASHBOARD\n"
        report += f"{'='*70}\n\n"
        report += f"Date: {datetime.now().strftime('%B %d, %Y - %A')}\n"
        report += f"Month: {perf['month']}\n\n"

        # Portfolio Status
        report += f"{'='*70}\n"
        report += f"💰 PORTFOLIO STATUS\n"
        report += f"{'='*70}\n"
        report += f"Starting Capital: ${perf['starting_capital']:,.2f}\n"
        report += f"Current Value: ${perf['current_value']:,.2f}\n"
        report += f"Available Cash: ${perf['cash']:,.2f}\n"
        report += f"Deployed Capital: ${perf['deployed']:,.2f}\n"
        report += f"Total P/L: ${perf['total_pnl']:+,.2f} ({perf['total_pnl_pct']:+.2f}%)\n\n"

        report += f"Trades This Month: {perf['trades']}\n"
        report += f"Winners: {perf['winners']} | Losers: {perf['losers']}\n"
        if perf['trades'] > 0:
            report += f"Win Rate: {perf['win_rate']:.1f}%\n"
        report += f"Open Positions: {perf['open_positions']}/3\n\n"

        # Position Checks
        if position_checks:
            report += f"{'='*70}\n"
            report += f"📋 POSITION UPDATES\n"
            report += f"{'='*70}\n"

            for check in position_checks:
                report += f"\n{check['ticker']}:\n"
                report += f"  Current: ${check['current_price']:.2f} (Entry: ${check['entry_price']:.2f})\n"
                report += f"  P/L: ${check['profit_loss']:+.2f} ({check['profit_loss_pct']:+.2f}%)\n"
                report += f"  💡 {check['action']}: {check['reason']}\n"

        # New Opportunities
        if new_opportunities:
            report += f"\n{'='*70}\n"
            report += f"🎯 NEW OPPORTUNITIES\n"
            report += f"{'='*70}\n"

            for opp in new_opportunities:
                report += f"\n{opp['ticker']} - {opp['sector']}\n"
                report += f"  Price: ${opp['price']:.2f}\n"
                report += f"  Suggested: Buy {opp['shares']} shares (${opp['cost']:.2f})\n"
                report += f"  Confidence: {opp['confidence']*100:.0f}%\n"
                if opp['target']:
                    gain = ((opp['target'] / opp['price']) - 1) * 100
                    report += f"  🎯 Target: ${opp['target']:.2f} (+{gain:.1f}%)\n"
                if opp['stop']:
                    loss = ((opp['stop'] / opp['price']) - 1) * 100
                    report += f"  ⛔ Stop: ${opp['stop']:.2f} ({loss:.1f}%)\n"
                report += f"  {opp['explanation']}\n"
        else:
            if status['num_positions'] < 3:
                report += f"\n{'='*70}\n"
                report += f"No strong BUY signals today. Keep cash for better opportunities.\n"

        report += f"\n{'='*70}\n"
        report += "⚠️  REMEMBER:\n"
        report += "- Act on SELL signals promptly\n"
        report += "- Set stop losses on new positions\n"
        report += "- Don't exceed 3 positions\n"
        report += "- Monthly budget limit: $1,000\n"
        report += f"{'='*70}\n"

        return report

    def run_daily_analysis(self) -> str:
        """Run complete daily analysis"""
        logger.info("\n" + "="*70)
        logger.info("STARTING DAILY ANALYSIS")
        logger.info("="*70)

        # Initialize month if needed
        self.portfolio.initialize_month()

        # Check existing positions
        position_checks = self.check_existing_positions()

        # Find new opportunities
        new_opportunities = self.find_new_opportunities()

        # Generate report
        report = self.generate_daily_report(position_checks, new_opportunities)

        print(report)

        # Send notifications
        self._send_notifications(report, position_checks, new_opportunities)

        logger.info("\n✅ Daily analysis complete!")

        return report

    def _send_notifications(self, report: str, position_checks: List[Dict],
                          new_opportunities: List[Dict]):
        """Send notifications via Discord and Email"""

        # Send to Discord
        if self.discord.enabled:
            # Send position alerts
            for check in position_checks:
                if check['action_needed']:
                    self.discord.send_position_alert(
                        ticker=check['ticker'],
                        action=check['action'],
                        reason=check['reason'],
                        current_price=check['current_price'],
                        entry_price=check['entry_price'],
                        profit_pct=check['profit_loss_pct']
                    )

            # Send new opportunities
            if new_opportunities:
                buys = [{
                    'ticker': opp['ticker'],
                    'price': opp['price'],
                    'confidence': opp['confidence'],
                    'price_target': opp.get('target'),
                    'stop_loss': opp.get('stop')
                } for opp in new_opportunities]

                self.discord.send_market_open_alert(buys, [])

        # Send email report
        if self.email.enabled:
            subject = f"Daily Trading Report - {datetime.now().strftime('%b %d')}"
            self.email.send_email(subject, report)


def main():
    """Run daily dashboard"""
    import argparse

    parser = argparse.ArgumentParser(description="Daily trading dashboard")
    parser.add_argument('--budget', type=float, default=1000,
                       help='Monthly budget (default: 1000)')

    args = parser.parse_args()

    dashboard = DailyDashboard(monthly_budget=args.budget)
    dashboard.run_daily_analysis()


if __name__ == '__main__':
    main()
