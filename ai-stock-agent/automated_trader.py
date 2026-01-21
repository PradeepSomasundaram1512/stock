"""
Automated Trading Scheduler
Runs scans and monitors automatically during market hours
"""

import schedule
import time
import logging
from datetime import datetime, time as dt_time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from daily_trader import DailyTrader

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

    # Intraday position monitoring (every 30 minutes)
    'monitor_interval_minutes': 30,

    # End of day summary
    'eod_summary_time': "16:05",  # 5 min after market close

    # Watchlist file
    'watchlist': 'watchlist.txt',

    # Analysis period (shorter for day trading)
    'scan_period': '1mo'  # 1 month of data
}


class AutomatedTrader:
    """Automated trading bot that runs on schedule"""

    def __init__(self):
        """Initialize automated trader"""
        self.trader = DailyTrader(watchlist_file=CONFIG['watchlist'])
        self.is_market_hours = False
        self.last_scan_results = None

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now().time()
        return MARKET_OPEN_TIME <= now <= MARKET_CLOSE_TIME

    def is_weekday(self) -> bool:
        """Check if today is a weekday (Monday=0, Sunday=6)"""
        return datetime.now().weekday() < 5

    def morning_scan(self):
        """Run morning market scan"""
        if not self.is_weekday():
            logger.info("⏸️  Weekend - skipping morning scan")
            return

        logger.info("\n" + "🌅"*35)
        logger.info(" MORNING SCAN - MARKET OPEN")
        logger.info("🌅"*35 + "\n")

        try:
            # Load watchlist
            watchlist = self.trader.load_watchlist()

            # Scan market
            results = self.trader.scan_market(watchlist, period=CONFIG['scan_period'])
            self.last_scan_results = results

            # Send alerts
            self.trader.send_morning_alert(results)

            logger.info("\n✅ Morning scan completed successfully")

        except Exception as e:
            logger.error(f"❌ Morning scan failed: {e}")
            import traceback
            traceback.print_exc()

    def monitor_positions(self):
        """Monitor positions during market hours"""
        if not self.is_weekday():
            return

        if not self.is_market_open():
            logger.info("⏸️  Market closed - skipping position monitoring")
            return

        logger.info("\n" + "👀"*35)
        logger.info(" INTRADAY POSITION MONITORING")
        logger.info("👀"*35 + "\n")

        try:
            self.trader.monitor_positions()
            logger.info("\n✅ Position monitoring completed")

        except Exception as e:
            logger.error(f"❌ Position monitoring failed: {e}")
            import traceback
            traceback.print_exc()

    def end_of_day_summary(self):
        """Send end of day summary"""
        if not self.is_weekday():
            logger.info("⏸️  Weekend - skipping EOD summary")
            return

        logger.info("\n" + "🌙"*35)
        logger.info(" END OF DAY SUMMARY")
        logger.info("🌙"*35 + "\n")

        try:
            self.trader.send_daily_summary()
            logger.info("\n✅ EOD summary sent successfully")

        except Exception as e:
            logger.error(f"❌ EOD summary failed: {e}")
            import traceback
            traceback.print_exc()

    def setup_schedule(self):
        """Setup automated schedule"""
        logger.info("\n" + "="*70)
        logger.info(" AUTOMATED TRADING BOT CONFIGURATION")
        logger.info("="*70)
        logger.info(f"\n📅 Schedule:")
        logger.info(f"  🌅 Morning Scan: {CONFIG['morning_scan_time']} (Market Open)")
        logger.info(f"  👀 Position Monitoring: Every {CONFIG['monitor_interval_minutes']} minutes")
        logger.info(f"  🌙 EOD Summary: {CONFIG['eod_summary_time']} (Market Close)")
        logger.info(f"\n📊 Watchlist: {CONFIG['watchlist']}")
        logger.info(f"⏱️  Analysis Period: {CONFIG['scan_period']}")
        logger.info("\n" + "="*70 + "\n")

        # Morning scan
        schedule.every().day.at(CONFIG['morning_scan_time']).do(self.morning_scan)

        # Position monitoring every N minutes
        schedule.every(CONFIG['monitor_interval_minutes']).minutes.do(self.monitor_positions)

        # End of day summary
        schedule.every().day.at(CONFIG['eod_summary_time']).do(self.end_of_day_summary)

        logger.info("✅ Scheduler configured successfully")
        logger.info("🤖 Bot is now running... Press Ctrl+C to stop\n")

    def run(self):
        """Run the automated trading bot"""
        self.setup_schedule()

        # Run immediately on first start (optional)
        if self.is_market_open() and self.is_weekday():
            logger.info("🚀 Market is open! Running initial scan...")
            self.morning_scan()

        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

            except KeyboardInterrupt:
                logger.info("\n\n⏹️  Bot stopped by user")
                break

            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                time.sleep(60)  # Wait a minute before retrying


def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          AUTOMATED DAILY TRADING BOT                         ║
║                                                              ║
║  📱 SMS/Email alerts for BUY/SELL signals                    ║
║  🤖 Automated scanning during market hours                   ║
║  👀 Real-time position monitoring                            ║
║  📊 Daily performance summaries                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    logger.info("Starting Automated Trading Bot...")

    bot = AutomatedTrader()
    bot.run()


if __name__ == '__main__':
    main()
