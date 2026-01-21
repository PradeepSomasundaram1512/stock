"""
Daily Trading System - Automated Stock Scanner with Alerts
Perfect for day trading with SMS/Email notifications
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, time
from typing import List, Dict, Any
import argparse

sys.path.append(str(Path(__file__).parent))

from graph.autonomous_decision_graph import get_autonomous_decision_graph
from backtesting.performance import get_performance_tracker
from notifications.sms_notifier import get_sms_notifier
from notifications.email_notifier import get_email_notifier
from notifications.discord_notifier import get_discord_notifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyTrader:
    """Automated daily trading system with alerts"""

    def __init__(self, watchlist_file: str = None):
        """
        Initialize daily trader

        Args:
            watchlist_file: Path to file containing stock tickers (one per line)
        """
        self.graph = get_autonomous_decision_graph()
        self.tracker = get_performance_tracker()
        self.sms = get_sms_notifier()
        self.email = get_email_notifier()
        self.discord = get_discord_notifier()
        self.watchlist_file = watchlist_file or "watchlist.txt"

    def load_watchlist(self) -> List[str]:
        """Load watchlist from file"""
        watchlist_path = Path(self.watchlist_file)

        if not watchlist_path.exists():
            logger.warning(f"Watchlist file not found: {self.watchlist_file}")
            logger.info("Creating default watchlist with popular stocks...")

            # Default watchlist - popular day trading stocks
            default_watchlist = [
                # Tech Giants
                "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
                # Popular Day Trading Stocks
                "AMD", "NFLX", "DIS", "PYPL", "SQ", "SNAP", "UBER",
                # ETFs
                "SPY", "QQQ", "IWM", "DIA",
                # High Volume
                "BAC", "F", "AAL", "CCL", "NIO"
            ]

            with open(watchlist_path, 'w') as f:
                f.write('\n'.join(default_watchlist))

            logger.info(f"✓ Created {self.watchlist_file} with {len(default_watchlist)} stocks")
            return default_watchlist

        # Load from file
        with open(watchlist_path, 'r') as f:
            tickers = [
                line.strip().upper()
                for line in f
                if line.strip() and not line.startswith('#')
            ]

        logger.info(f"✓ Loaded {len(tickers)} stocks from {self.watchlist_file}")
        return tickers

    def scan_market(self, tickers: List[str], period: str = "1mo") -> Dict[str, List[Dict]]:
        """
        Scan market and categorize opportunities

        Args:
            tickers: List of stock tickers to analyze
            period: Analysis period (1mo for day trading)

        Returns:
            Dictionary with 'buys', 'sells', 'holds' lists
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"MARKET SCAN STARTED - {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        logger.info(f"Analyzing {len(tickers)} stocks...")
        logger.info(f"{'='*70}\n")

        results = {
            'buys': [],
            'sells': [],
            'holds': []
        }

        for i, ticker in enumerate(tickers, 1):
            try:
                logger.info(f"[{i}/{len(tickers)}] Analyzing {ticker}...")

                # Run analysis with short period for day trading
                result = self.graph.run(ticker, period=period)

                if result.get('error'):
                    logger.warning(f"  ⚠️  {ticker}: {result['error']}")
                    continue

                # Extract decision
                decision_data = result.get('decision', {})
                decision = decision_data.get('decision', 'HOLD')
                confidence = decision_data.get('confidence', 0.5)
                price = result.get('features', {}).get('latest_price', 0)

                stock_info = {
                    'ticker': ticker,
                    'decision': decision,
                    'confidence': confidence,
                    'price': price,
                    'reason': decision_data.get('reasoning', '')[:100],
                    'entry_price': decision_data.get('entry_price'),
                    'stop_loss': decision_data.get('stop_loss'),
                    'price_target': decision_data.get('price_target')
                }

                # Categorize by decision
                if decision == 'BUY' and confidence >= 0.65:
                    results['buys'].append(stock_info)
                    logger.info(f"  🟢 BUY: {ticker} @ ${price:.2f} ({confidence*100:.0f}%)")

                elif decision == 'SELL' and confidence >= 0.65:
                    results['sells'].append(stock_info)
                    logger.info(f"  🔴 SELL: {ticker} @ ${price:.2f} ({confidence*100:.0f}%)")

                else:
                    results['holds'].append(stock_info)
                    logger.info(f"  🟡 HOLD: {ticker} @ ${price:.2f} ({confidence*100:.0f}%)")

                # Track recommendation
                self.tracker.track_recommendation(ticker, result)

            except Exception as e:
                logger.error(f"  ❌ Error analyzing {ticker}: {e}")
                continue

        # Sort by confidence
        results['buys'].sort(key=lambda x: x['confidence'], reverse=True)
        results['sells'].sort(key=lambda x: x['confidence'], reverse=True)

        return results

    def generate_investment_plan(self, buys: List[Dict], budget: float = 1000) -> str:
        """
        Generate specific investment plan for given budget

        Args:
            buys: List of BUY recommendations
            budget: Investment budget in dollars

        Returns:
            Formatted investment plan string
        """
        if not buys:
            return "No BUY opportunities found today."

        plan = f"\n{'='*70}\n"
        plan += f"💰 INVESTMENT PLAN FOR ${budget:,.0f}\n"
        plan += f"{'='*70}\n\n"

        # Take top 3-5 stocks based on confidence
        top_picks = buys[:min(5, len(buys))]
        num_stocks = min(3, len(top_picks))  # Diversify across 3 stocks max

        # Calculate allocation (weighted by confidence)
        total_confidence = sum(s['confidence'] for s in top_picks[:num_stocks])

        plan += f"STRATEGY: Diversify across {num_stocks} high-confidence picks\n\n"

        remaining_budget = budget
        for i, stock in enumerate(top_picks[:num_stocks], 1):
            # Allocate budget proportional to confidence
            weight = stock['confidence'] / total_confidence
            allocation = budget * weight
            shares = int(allocation / stock['price'])
            actual_cost = shares * stock['price']
            remaining_budget -= actual_cost

            plan += f"[{i}] {stock['ticker']}\n"
            plan += f"    Price: ${stock['price']:.2f}\n"
            plan += f"    Confidence: {stock['confidence']*100:.0f}%\n"
            plan += f"    Allocation: ${allocation:.0f} → Buy {shares} shares (${actual_cost:.2f})\n"

            if stock.get('price_target'):
                target_gain = ((stock['price_target'] / stock['price']) - 1) * 100
                plan += f"    🎯 Target: ${stock['price_target']:.2f} (+{target_gain:.1f}% profit)\n"

            if stock.get('stop_loss'):
                stop_loss_pct = ((stock['stop_loss'] / stock['price']) - 1) * 100
                plan += f"    ⛔ Stop Loss: ${stock['stop_loss']:.2f} ({stop_loss_pct:.1f}%)\n"

            plan += f"    📝 Reason: {stock['reason'][:80]}...\n\n"

        plan += f"Remaining Cash: ${remaining_budget:.2f}\n"
        plan += f"\n{'='*70}\n"
        plan += "WHEN TO SELL:\n"
        plan += "  • Hit price target → Take profits (set alerts!)\n"
        plan += "  • Hit stop loss → Exit to limit losses\n"
        plan += "  • Hold for 5-30 days or until targets hit\n"
        plan += f"{'='*70}\n"

        return plan

    def send_morning_alert(self, results: Dict[str, List[Dict]]):
        """Send morning market alert with top opportunities"""
        logger.info("\n" + "="*70)
        logger.info("SENDING MORNING ALERTS")
        logger.info("="*70)

        buys = results['buys']
        sells = results['sells']

        logger.info(f"\n📊 SCAN RESULTS:")
        logger.info(f"  🟢 BUY Signals: {len(buys)}")
        logger.info(f"  🔴 SELL Signals: {len(sells)}")
        logger.info(f"  🟡 HOLD Signals: {len(results['holds'])}")

        if buys:
            logger.info(f"\n🟢 TOP 5 BUY OPPORTUNITIES:")
            for i, stock in enumerate(buys[:5], 1):
                logger.info(f"  {i}. {stock['ticker']} @ ${stock['price']:.2f} ({stock['confidence']*100:.0f}% confidence)")

            # Generate and display investment plan
            investment_plan = self.generate_investment_plan(buys, budget=1000)
            logger.info(investment_plan)

        if sells:
            logger.info(f"\n🔴 TOP 5 SELL SIGNALS:")
            for i, stock in enumerate(sells[:5], 1):
                logger.info(f"  {i}. {stock['ticker']} @ ${stock['price']:.2f} ({stock['confidence']*100:.0f}% confidence)")

        # Send SMS
        if self.sms.enabled:
            self.sms.send_market_open_alert(buys, sells)
            logger.info("\n✓ SMS alert sent")

        # Send Email
        if self.email.enabled:
            self.email.send_market_open_alert(buys, sells)
            logger.info("✓ Email alert sent")

        # Send Discord
        if self.discord.enabled:
            self.discord.send_market_open_alert(buys, sells)
            logger.info("✓ Discord alert sent")

        if not self.sms.enabled and not self.email.enabled and not self.discord.enabled:
            logger.warning("\n⚠️  No notifications enabled. Enable SMS, Email, or Discord in .env")

    def monitor_positions(self):
        """
        Monitor open positions and send alerts for targets/stops

        Call this periodically during market hours
        """
        logger.info("\n" + "="*70)
        logger.info("MONITORING OPEN POSITIONS")
        logger.info("="*70 + "\n")

        # Get open positions
        open_positions = self.tracker.get_open_positions()

        if not open_positions:
            logger.info("No open positions to monitor")
            return

        logger.info(f"Monitoring {len(open_positions)} positions...")

        for pos in open_positions:
            ticker = pos['ticker']
            entry_price = pos['entry_price']
            current_price = pos['current_price']
            stop_loss = pos['stop_loss']
            price_target = pos['price_target']
            profit_pct = pos['profit_loss_pct']

            logger.info(f"\n{ticker}:")
            logger.info(f"  Entry: ${entry_price:.2f}")
            logger.info(f"  Current: ${current_price:.2f}")
            logger.info(f"  P/L: {profit_pct:+.2f}%")

            # Check if target hit (within 1% of target)
            if price_target and current_price >= price_target * 0.99:
                logger.info(f"  🎯 TARGET HIT! Sending alert...")
                self.sms.send_target_hit_alert(ticker, entry_price, price_target, current_price, profit_pct)
                self.email.send_target_hit_alert(ticker, entry_price, price_target, current_price, profit_pct)

            # Check if stop loss hit (within 1% of stop)
            elif stop_loss and current_price <= stop_loss * 1.01:
                logger.info(f"  ⛔ STOP LOSS HIT! Sending alert...")
                self.sms.send_stop_loss_alert(ticker, entry_price, stop_loss, current_price, profit_pct)
                self.email.send_stop_loss_alert(ticker, entry_price, stop_loss, current_price, profit_pct)

            # Alert for significant price movements
            elif abs(profit_pct) >= 5:  # 5% movement
                logger.info(f"  🚨 Significant move: {profit_pct:+.2f}%")
                reason = f"Price moved {profit_pct:+.2f}% from entry"
                action = "TAKE PROFITS" if profit_pct > 0 else "REVIEW POSITION"
                self.sms.send_position_alert(ticker, action, reason, current_price, entry_price, profit_pct)
                self.email.send_position_alert(ticker, action, reason, current_price, entry_price, profit_pct)

    def send_daily_summary(self):
        """Send end-of-day summary"""
        logger.info("\n" + "="*70)
        logger.info("GENERATING DAILY SUMMARY")
        logger.info("="*70 + "\n")

        # Update all positions
        self.tracker.update_open_positions()

        # Get performance metrics
        performance = self.tracker.get_performance_metrics()

        total_positions = performance.get('total_trades', 0)
        winning = performance.get('wins', 0)
        losing = performance.get('losses', 0)

        # Calculate today's P/L (simplified - you can enhance this)
        open_positions = self.tracker.get_open_positions()
        total_pnl = sum(pos['profit_loss_pct'] for pos in open_positions) / max(len(open_positions), 1)

        # Find best/worst performers
        if open_positions:
            best = max(open_positions, key=lambda x: x['profit_loss_pct'])
            worst = min(open_positions, key=lambda x: x['profit_loss_pct'])
            best_performer = f"{best['ticker']} ({best['profit_loss_pct']:+.2f}%)"
            worst_performer = f"{worst['ticker']} ({worst['profit_loss_pct']:+.2f}%)"
        else:
            best_performer = None
            worst_performer = None

        logger.info(f"Positions: {total_positions}")
        logger.info(f"Winners: {winning} | Losers: {losing}")
        logger.info(f"Total P/L: {total_pnl:+.2f}%")

        # Send notifications
        self.sms.send_daily_summary(total_positions, winning, losing, total_pnl, best_performer)
        self.email.send_daily_summary(total_positions, winning, losing, total_pnl, best_performer, worst_performer)

        logger.info("\n✓ Daily summary sent")


def main():
    parser = argparse.ArgumentParser(description="Daily Trading System with Automated Alerts")
    parser.add_argument('command', choices=['scan', 'monitor', 'summary'],
                       help='Command to run: scan (morning), monitor (intraday), summary (end of day)')
    parser.add_argument('--watchlist', type=str, default='watchlist.txt',
                       help='Path to watchlist file (default: watchlist.txt)')
    parser.add_argument('--period', type=str, default='1mo',
                       help='Analysis period for scanning (default: 1mo for day trading)')

    args = parser.parse_args()

    trader = DailyTrader(watchlist_file=args.watchlist)

    if args.command == 'scan':
        # Morning scan - find opportunities
        watchlist = trader.load_watchlist()
        results = trader.scan_market(watchlist, period=args.period)
        trader.send_morning_alert(results)

    elif args.command == 'monitor':
        # Intraday monitoring - check positions
        trader.monitor_positions()

    elif args.command == 'summary':
        # End of day summary
        trader.send_daily_summary()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
