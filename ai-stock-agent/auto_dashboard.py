"""
Automated Daily Dashboard
Runs daily analysis automatically during market hours
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

from daily_dashboard import DailyDashboard

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Market hours
MARKET_OPEN_TIME = dt_time(9, 30)
MARKET_CLOSE_TIME = dt_time(16, 0)

# Schedule configuration
CONFIG = {
    'daily_analysis_time': "09:40",  # 10 min after market open
    'midday_check_time': "12:00",    # Midday position check
    'eod_check_time': "15:30",       # 30 min before close
    'monthly_budget': 1000
}


class AutoDashboard:
    """Automated daily dashboard"""

    def __init__(self):
        """Initialize auto dashboard"""
        self.dashboard = DailyDashboard(monthly_budget=CONFIG['monthly_budget'])
        logger.info("Auto Dashboard initialized")

    def is_weekday(self) -> bool:
        """Check if today is a weekday"""
        return datetime.now().weekday() < 5

    def is_market_hours(self) -> bool:
        """Check if currently during market hours"""
        now = datetime.now().time()
        return MARKET_OPEN_TIME <= now <= MARKET_CLOSE_TIME

    def morning_analysis(self):
        """Run morning analysis"""
        logger.info("\n" + "="*70)
        logger.info("MORNING ANALYSIS")
        logger.info("="*70)

        if not self.is_weekday():
            logger.info("Market closed (weekend)")
            return

        try:
            self.dashboard.run_daily_analysis()
        except Exception as e:
            logger.error(f"❌ Morning analysis failed: {e}")
            import traceback
            traceback.print_exc()

    def midday_check(self):
        """Quick midday position check"""
        logger.info("\n" + "="*70)
        logger.info("MIDDAY POSITION CHECK")
        logger.info("="*70)

        if not self.is_weekday() or not self.is_market_hours():
            return

        try:
            position_checks = self.dashboard.check_existing_positions()

            # Alert on any urgent actions
            for check in position_checks:
                if check['action_needed']:
                    logger.warning(f"⚠️  {check['ticker']}: {check['action']} - {check['reason']}")

        except Exception as e:
            logger.error(f"❌ Midday check failed: {e}")

    def eod_check(self):
        """End of day position check"""
        logger.info("\n" + "="*70)
        logger.info("END OF DAY CHECK")
        logger.info("="*70)

        if not self.is_weekday():
            return

        try:
            position_checks = self.dashboard.check_existing_positions()
            perf = self.dashboard.portfolio.get_performance_summary()

            logger.info(f"\n📊 Today's Summary:")
            logger.info(f"Total P/L: ${perf['total_pnl']:+,.2f} ({perf['total_pnl_pct']:+.2f}%)")
            logger.info(f"Win Rate: {perf['win_rate']:.1f}%")
            logger.info(f"Open Positions: {perf['open_positions']}/3")

        except Exception as e:
            logger.error(f"❌ EOD check failed: {e}")

    def run(self):
        """Start automated dashboard"""
        logger.info("\n" + "="*70)
        logger.info("AUTOMATED DAILY DASHBOARD STARTED")
        logger.info("="*70)
        logger.info(f"Monthly Budget: ${CONFIG['monthly_budget']:,.0f}")
        logger.info(f"Morning Analysis: {CONFIG['daily_analysis_time']}")
        logger.info(f"Midday Check: {CONFIG['midday_check_time']}")
        logger.info(f"EOD Check: {CONFIG['eod_check_time']}")
        logger.info("="*70 + "\n")

        # Schedule tasks
        schedule.every().day.at(CONFIG['daily_analysis_time']).do(self.morning_analysis)
        schedule.every().day.at(CONFIG['midday_check_time']).do(self.midday_check)
        schedule.every().day.at(CONFIG['eod_check_time']).do(self.eod_check)

        logger.info("⏰ Scheduler running...")
        logger.info("Press Ctrl+C to stop.\n")

        # Run immediately if during market hours
        if self.is_weekday() and self.is_market_hours():
            logger.info("Market is open. Running analysis now...")
            self.morning_analysis()

        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("\n\n⏹️  Auto dashboard stopped")


def main():
    """Main entry point"""
    auto = AutoDashboard()
    auto.run()


if __name__ == '__main__':
    main()
