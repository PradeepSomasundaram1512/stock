"""
Automated Market Trading Scheduler
Scans entire market and monitors automatically during market hours
Uses comprehensive market scanner instead of limited watchlist
"""

import schedule
import time
import logging
from datetime import datetime, time as dt_time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from market_scanner import MarketScanner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Market hours (US Eastern Time - adjust for your timezone)
MARKET_OPEN_TIME = dt_time(9, 30)  # 9:30 AM ET
MARKET_CLOSE_TIME = dt_time(16, 0)  # 4:00 PM ET

# Trading schedule configuration
CONFIG = {
    # Morning scan when market opens
    'morning_scan_time': "09:35",  # 5 min after market open

    # Monthly budget
    'monthly_budget': 1000,  # $1000 per month

    # Top picks to show
    'top_picks': 10,

    # End of day summary
    'eod_summary_time': "16:05",  # 5 min after market close
}


class AutomatedMarketTrader:
    """Automated trading with comprehensive market scanning"""

    def __init__(self):
        """Initialize automated trader"""
        self.scanner = MarketScanner(budget=CONFIG['monthly_budget'])
        self.last_scan_results = None
        logger.info("Automated Market Trader initialized")
        logger.info(f"Monthly Budget: ${CONFIG['monthly_budget']:,.0f}")

    def is_market_hours(self) -> bool:
        """Check if current time is during market hours"""
        now = datetime.now().time()
        return MARKET_OPEN_TIME <= now <= MARKET_CLOSE_TIME

    def is_weekday(self) -> bool:
        """Check if today is a weekday (Mon-Fri)"""
        return datetime.now().weekday() < 5  # 0=Monday, 4=Friday

    def morning_scan(self):
        """Run comprehensive market scan in the morning"""
        logger.info("\n" + "="*70)
        logger.info("MORNING MARKET SCAN")
        logger.info("="*70)

        if not self.is_weekday():
            logger.info("Market is closed (weekend)")
            return

        if not self.is_market_hours():
            logger.info("Not during market hours")
            return

        try:
            # Scan entire market
            results = self.scanner.scan_market(top_n=CONFIG['top_picks'])
            self.last_scan_results = results

            # Generate monthly investment plan
            plan = self.scanner.generate_monthly_plan(results)
            print(plan)

            # Send alerts
            self.scanner.send_alerts(results, plan)

            logger.info("✅ Morning scan complete")

        except Exception as e:
            logger.error(f"❌ Morning scan failed: {e}")
            import traceback
            traceback.print_exc()

    def eod_summary(self):
        """End of day summary"""
        logger.info("\n" + "="*70)
        logger.info("END OF DAY SUMMARY")
        logger.info("="*70)

        if not self.is_weekday():
            logger.info("Market is closed (weekend)")
            return

        if self.last_scan_results:
            logger.info(f"Today's Scan:")
            logger.info(f"  🟢 BUY Opportunities: {len(self.last_scan_results['buys'])}")
            logger.info(f"  🔴 SELL Signals: {len(self.last_scan_results['sells'])}")
            logger.info(f"  📊 Total Analyzed: {self.last_scan_results['total_analyzed']}")
        else:
            logger.info("No scan results available for today")

        logger.info("\n✅ Trading day complete. See you tomorrow!")

    def run(self):
        """Start automated trading scheduler"""
        logger.info("\n" + "="*70)
        logger.info("AUTOMATED MARKET TRADER STARTED")
        logger.info("="*70)
        logger.info(f"Monthly Budget: ${CONFIG['monthly_budget']:,.0f}")
        logger.info(f"Market Hours: {MARKET_OPEN_TIME.strftime('%I:%M %p')} - {MARKET_CLOSE_TIME.strftime('%I:%M %p')}")
        logger.info(f"Morning Scan: {CONFIG['morning_scan_time']}")
        logger.info(f"EOD Summary: {CONFIG['eod_summary_time']}")
        logger.info("="*70 + "\n")

        # Schedule morning market scan
        schedule.every().day.at(CONFIG['morning_scan_time']).do(self.morning_scan)

        # Schedule end of day summary
        schedule.every().day.at(CONFIG['eod_summary_time']).do(self.eod_summary)

        logger.info("⏰ Scheduler running. Waiting for next scheduled event...")
        logger.info("Press Ctrl+C to stop.\n")

        # Run immediately if during market hours
        if self.is_weekday() and self.is_market_hours():
            logger.info("Market is currently open. Running scan now...")
            self.morning_scan()

        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("\n\n⏹️  Automated trader stopped by user")


def main():
    """Main entry point"""
    trader = AutomatedMarketTrader()
    trader.run()


if __name__ == '__main__':
    main()
