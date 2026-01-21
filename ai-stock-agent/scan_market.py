"""
Market Scanner CLI - Analyze multiple stocks and find best opportunities.
"""

import sys
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

from app.config import validate_config
from rag.ingest import initialize_knowledge_base
from scanner.market_scanner import (
    get_market_scanner,
    get_sp500_tickers,
    get_popular_stocks
)


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              AI STOCK MARKET SCANNER                         ║
║                                                              ║
║  Multi-Stock Analysis & Ranking System                       ║
║  Powered by LangChain, LangGraph & AI                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Main entry point for market scanner."""
    parser = argparse.ArgumentParser(
        description="AI Stock Market Scanner - Analyze multiple stocks"
    )

    # Stock selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--tickers',
        nargs='+',
        help='Specific tickers to analyze (e.g., AAPL MSFT GOOGL)'
    )
    group.add_argument(
        '--popular',
        action='store_true',
        help='Scan 50 most popular stocks'
    )
    group.add_argument(
        '--sp500',
        action='store_true',
        help='Scan top 100 S&P 500 stocks'
    )
    group.add_argument(
        '--watchlist',
        action='store_true',
        help='Scan stocks from data/watchlist.txt'
    )

    # Analysis options
    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Number of top stocks to show per category (default: 10)'
    )
    parser.add_argument(
        '--period',
        default='6mo',
        help='Analysis period (default: 6mo)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers (default: 5)'
    )
    parser.add_argument(
        '--export',
        help='Export results to CSV file'
    )
    parser.add_argument(
        '--init-kb',
        action='store_true',
        help='Initialize knowledge base before scanning'
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()
        logger.info("✓ Configuration valid")

        # Initialize knowledge base if requested
        if args.init_kb:
            logger.info("Initializing knowledge base...")
            success = initialize_knowledge_base(force_recreate=True)
            if success:
                logger.info("✓ Knowledge base initialized")
            else:
                logger.warning("⚠ Knowledge base initialization had issues")
        else:
            # Try to load existing
            initialize_knowledge_base(force_recreate=False)

        # Determine which stocks to scan
        if args.tickers:
            tickers = [t.upper() for t in args.tickers]
            print(f"\n📋 Analyzing {len(tickers)} specified stocks...\n")
        elif args.popular:
            tickers = get_popular_stocks()
            print(f"\n📋 Analyzing {len(tickers)} popular stocks...\n")
        elif args.sp500:
            tickers = get_sp500_tickers()
            print(f"\n📋 Analyzing top {len(tickers)} S&P 500 stocks...\n")
        elif args.watchlist:
            from app.config import WATCHLIST_FILE
            if WATCHLIST_FILE.exists():
                with open(WATCHLIST_FILE, 'r') as f:
                    tickers = [
                        line.strip().upper()
                        for line in f
                        if line.strip() and not line.startswith('#')
                    ]
                print(f"\n📋 Analyzing {len(tickers)} stocks from watchlist...\n")
            else:
                print(f"❌ Watchlist file not found: {WATCHLIST_FILE}")
                return 1
        else:
            # Default: popular stocks
            tickers = get_popular_stocks()
            print(f"\n📋 Analyzing {len(tickers)} popular stocks (default)...\n")

        # Create scanner
        scanner = get_market_scanner()
        scanner.max_workers = args.workers

        # Scan stocks
        results = scanner.scan_stocks(tickers, period=args.period)

        if not results:
            print("❌ No results obtained. Check your API key and internet connection.")
            return 1

        # Rank stocks
        rankings = scanner.rank_stocks(results, top_n=args.top)

        # Print rankings
        scanner.print_rankings(rankings)

        # Export if requested
        if args.export:
            scanner.export_to_csv(rankings, args.export)

        # Summary statistics
        total_buy = len([r for r in results if r.get('decision', {}).get('decision') == 'BUY'])
        total_hold = len([r for r in results if r.get('decision', {}).get('decision') == 'HOLD'])
        total_sell = len([r for r in results if r.get('decision', {}).get('decision') == 'SELL'])

        print(f"\n📊 SUMMARY:")
        print(f"   Total Analyzed: {len(results)}")
        print(f"   🟢 BUY signals:  {total_buy}")
        print(f"   🟡 HOLD signals: {total_hold}")
        print(f"   🔴 SELL signals: {total_sell}")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Scan interrupted by user.\n")
        return 130

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
