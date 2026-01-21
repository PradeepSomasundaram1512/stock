"""
Job Runner - Main entry point for background scheduler.
Runs periodic stock scans and sends notifications.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import signal

sys.path.append(str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import SCAN_INTERVAL_HOURS, validate_config, LOG_LEVEL
from rag.ingest import initialize_knowledge_base
from scheduler.stock_scanner import get_stock_scanner

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('stock_agent_scheduler.log')
    ]
)

logger = logging.getLogger(__name__)


class JobRunner:
    """Manages background scheduling of stock scans."""

    def __init__(self):
        """Initialize the Job Runner."""
        self.scheduler = BlockingScheduler()
        self.stock_scanner = get_stock_scanner()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Gracefully shutdown the scheduler."""
        logger.info("Received shutdown signal, stopping scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
        sys.exit(0)

    def scan_job(self):
        """
        Job function: Scan all stocks in watchlist.
        This is called by the scheduler.
        """
        logger.info("="*70)
        logger.info("STARTING SCHEDULED STOCK SCAN")
        logger.info("="*70)

        try:
            summary = self.stock_scanner.scan_all()

            logger.info("Scan Summary:")
            logger.info(f"  Stocks Scanned: {summary.get('scanned', 0)}")
            logger.info(f"  Buy Signals: {summary.get('buy_signals', 0)}")
            logger.info(f"  Notifications Sent: {summary.get('notifications_sent', 0)}")
            logger.info(f"  Errors: {summary.get('errors', 0)}")

            budget = summary.get('budget_status', {})
            logger.info(f"  Budget Remaining: ${budget.get('remaining', 0):.2f}")

        except Exception as e:
            logger.error(f"Error during scan job: {str(e)}", exc_info=True)

        logger.info("="*70)
        logger.info("SCAN COMPLETE")
        logger.info("="*70 + "\n")

    def initialize(self):
        """Initialize system before starting scheduler."""
        logger.info("Initializing AI Stock Agent Scheduler...")

        try:
            # Validate configuration
            logger.info("Validating configuration...")
            validate_config()
            logger.info("✓ Configuration valid")

            # Load knowledge base
            logger.info("Loading knowledge base...")
            success = initialize_knowledge_base(force_recreate=False)
            if not success:
                logger.warning("⚠ Knowledge base not found. Run with --init-kb flag first.")
                logger.info("Continuing anyway - knowledge base will be empty")

            logger.info("✓ Initialization complete")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            return False

    def start(self, run_immediately: bool = False):
        """
        Start the scheduler.

        Args:
            run_immediately: If True, run one scan immediately before scheduling
        """
        if not self.initialize():
            logger.error("Initialization failed, cannot start scheduler")
            return

        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║                                                              ║")
        logger.info("║          AI STOCK AGENT - BACKGROUND SCHEDULER               ║")
        logger.info("║                                                              ║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")

        # Add job to scheduler
        if SCAN_INTERVAL_HOURS == 24:
            # Daily scan at 9:30 AM (market open)
            trigger = CronTrigger(hour=9, minute=30)
            logger.info("Scheduled: Daily scan at 9:30 AM")
        else:
            # Interval-based scan
            self.scheduler.add_job(
                self.scan_job,
                'interval',
                hours=SCAN_INTERVAL_HOURS,
                id='stock_scan'
            )
            logger.info(f"Scheduled: Every {SCAN_INTERVAL_HOURS} hours")

        # Run immediately if requested
        if run_immediately:
            logger.info("\nRunning initial scan now...")
            self.scan_job()

        # Show next run time
        jobs = self.scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time
            logger.info(f"\nNext scan scheduled for: {next_run}")

        logger.info("\n🟢 Scheduler running. Press Ctrl+C to stop.\n")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")


def main():
    """Main entry point for scheduler."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Stock Agent - Background Scheduler"
    )
    parser.add_argument(
        '--now',
        action='store_true',
        help='Run one scan immediately before starting scheduler'
    )
    parser.add_argument(
        '--init-kb',
        action='store_true',
        help='Initialize knowledge base before starting'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Set debug level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize knowledge base if requested
    if args.init_kb:
        logger.info("Initializing knowledge base...")
        success = initialize_knowledge_base(force_recreate=True)
        if success:
            logger.info("✓ Knowledge base initialized")
        else:
            logger.error("✗ Knowledge base initialization failed")
            return 1

    # Start scheduler
    runner = JobRunner()
    runner.start(run_immediately=args.now)

    return 0


if __name__ == "__main__":
    sys.exit(main())
