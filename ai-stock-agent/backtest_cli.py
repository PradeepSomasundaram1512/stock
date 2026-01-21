"""
Backtesting CLI - Test system performance on historical data.
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

from backtesting.performance import get_performance_tracker
from backtesting.engine import run_historical_backtest
from backtesting.database import get_backtest_db


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          BACKTESTING & PERFORMANCE TRACKER                   ║
║                                                              ║
║  Prove your system works with historical validation          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def cmd_performance(args):
    """Show performance report."""
    tracker = get_performance_tracker()

    print(f"\n{'='*70}")
    print(f"PERFORMANCE ANALYSIS")
    print(f"{'='*70}\n")

    # Generate report
    report = tracker.generate_performance_report(days=args.days)
    print(report)

    # Show best/worst trades
    if args.show_trades:
        trades = tracker.get_best_worst_trades(limit=5)

        print(f"\n🏆 TOP 5 BEST TRADES")
        print(f"{'='*70}")
        for i, trade in enumerate(trades['best'], 1):
            print(
                f"{i}. {trade['ticker']:6s} {trade['decision']:4s} "
                f"@ ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} "
                f"({trade['profit_loss_pct']:+.2f}%) "
                f"[{trade['exit_reason']}]"
            )

        print(f"\n💔 TOP 5 WORST TRADES")
        print(f"{'='*70}")
        for i, trade in enumerate(trades['worst'], 1):
            print(
                f"{i}. {trade['ticker']:6s} {trade['decision']:4s} "
                f"@ ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} "
                f"({trade['profit_loss_pct']:+.2f}%) "
                f"[{trade['exit_reason']}]"
            )

    print()


def cmd_backtest(args):
    """Run historical backtest."""
    print(f"\n{'='*70}")
    print(f"HISTORICAL BACKTEST: {args.ticker}")
    print(f"{'='*70}\n")

    # Parse dates
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=365)  # 1 year ago

    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Initial Capital: ${args.capital:,.2f}\n")

    print("Running backtest (this may take a few minutes)...\n")

    # Run backtest
    results = run_historical_backtest(
        args.ticker,
        start_date,
        end_date,
        args.capital
    )

    if results.get('error'):
        print(f"❌ Error: {results['error']}\n")
        return

    # Print results
    print(f"{'='*70}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*70}\n")

    print(f"Initial Capital:        ${results['initial_capital']:,.2f}")
    print(f"Final Capital:          ${results['final_capital']:,.2f}")
    print(f"Total Return:           {results['total_return']:+.2f}%")
    print(f"Number of Trades:       {results['num_trades']}")

    if 'buy_and_hold_return' in results:
        print(f"\nBuy & Hold Return:      {results['buy_and_hold_return']:+.2f}%")
        print(f"Vs. Buy & Hold:         {results['vs_buy_hold']:+.2f}%")

        if results['vs_buy_hold'] > 0:
            print(f"✅ Strategy OUTPERFORMED buy-and-hold by {results['vs_buy_hold']:.2f}%")
        else:
            print(f"❌ Strategy underperformed buy-and-hold by {abs(results['vs_buy_hold']):.2f}%")

    print(f"\n{'='*70}\n")


def cmd_update(args):
    """Update open positions."""
    print("\nUpdating open positions with current prices...\n")

    tracker = get_performance_tracker()
    tracker.update_open_positions()

    print("\n✓ Update complete\n")


def cmd_positions(args):
    """Show open positions."""
    db = get_backtest_db()
    positions = db.get_open_recommendations()

    if not positions:
        print("\nNo open positions.\n")
        return

    print(f"\n{'='*70}")
    print(f"OPEN POSITIONS ({len(positions)})")
    print(f"{'='*70}\n")

    print(f"{'Ticker':<8} {'Decision':<8} {'Entry':<10} {'Target':<10} {'Stop':<10} {'Conf':<8} {'Days'}")
    print(f"{'─'*70}")

    for pos in positions:
        rec_date = datetime.fromisoformat(pos['recommendation_date'])
        days_open = (datetime.now() - rec_date).days

        print(
            f"{pos['ticker']:<8} "
            f"{pos['decision']:<8} "
            f"${pos['entry_price']:<9.2f} "
            f"${pos.get('price_target') or 0:<9.2f} "
            f"${pos.get('stop_loss') or 0:<9.2f} "
            f"{pos['confidence']*100:<7.1f}% "
            f"{days_open}"
        )

    print()


def cmd_ticker_stats(args):
    """Show statistics for a specific ticker."""
    tracker = get_performance_tracker()
    stats = tracker.get_ticker_performance(args.ticker)

    print(f"\n{'='*70}")
    print(f"TICKER PERFORMANCE: {args.ticker}")
    print(f"{'='*70}\n")

    print(f"Total Trades:        {stats['total_trades']}")
    print(f"Wins / Losses:       {stats.get('wins', 0)} / {stats.get('losses', 0)}")
    print(f"Win Rate:            {stats['win_rate']:.2f}%")
    print(f"Average Return:      {stats['avg_return']:+.2f}%")
    print(f"Total Return:        {stats['total_return']:+.2f}%")
    print(f"Best Trade:          {stats.get('best_trade', 0):+.2f}%")
    print(f"Worst Trade:         {stats.get('worst_trade', 0):+.2f}%")

    print()


def cmd_history(args):
    """Show recommendation history."""
    db = get_backtest_db()

    if args.ticker:
        history = db.get_recommendation_history(ticker=args.ticker, limit=args.limit)
        print(f"\n{'='*70}")
        print(f"RECOMMENDATION HISTORY: {args.ticker} (Last {args.limit})")
        print(f"{'='*70}\n")
    else:
        history = db.get_recommendation_history(limit=args.limit)
        print(f"\n{'='*70}")
        print(f"RECOMMENDATION HISTORY (Last {args.limit})")
        print(f"{'='*70}\n")

    if not history:
        print("No recommendations found.\n")
        return

    for rec in history:
        rec_date = datetime.fromisoformat(rec['recommendation_date'])
        status = "OPEN" if not rec['is_closed'] else "CLOSED"

        print(f"\n[{rec['id']}] {rec['ticker']} - {rec['decision']} ({rec['confidence']*100:.1f}%)")
        print(f"  Date: {rec_date.strftime('%Y-%m-%d')} | Status: {status}")
        print(f"  Entry: ${rec['entry_price']:.2f}")

        if rec['is_closed']:
            exit_date = datetime.fromisoformat(rec['exit_date'])
            print(f"  Exit: ${rec['exit_price']:.2f} on {exit_date.strftime('%Y-%m-%d')}")
            print(f"  P&L: {rec['profit_loss_pct']:+.2f}% ({rec['outcome'].upper()})")
            print(f"  Reason: {rec['exit_reason']}")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backtesting and Performance Tracking Tool"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Performance command
    perf_parser = subparsers.add_parser('performance', help='Show performance report')
    perf_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    perf_parser.add_argument(
        '--show-trades',
        action='store_true',
        help='Show best/worst trades'
    )

    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run historical backtest')
    backtest_parser.add_argument(
        'ticker',
        help='Stock ticker to backtest'
    )
    backtest_parser.add_argument(
        '--start-date',
        help='Start date (YYYY-MM-DD). Default: 1 year ago'
    )
    backtest_parser.add_argument(
        '--end-date',
        help='End date (YYYY-MM-DD). Default: today'
    )
    backtest_parser.add_argument(
        '--capital',
        type=float,
        default=100000,
        help='Initial capital (default: 100000)'
    )

    # Update command
    update_parser = subparsers.add_parser('update', help='Update open positions')

    # Positions command
    positions_parser = subparsers.add_parser('positions', help='Show open positions')

    # Ticker stats command
    ticker_parser = subparsers.add_parser('ticker', help='Show ticker performance')
    ticker_parser.add_argument(
        'ticker',
        help='Stock ticker'
    )

    # History command
    history_parser = subparsers.add_parser('history', help='Show recommendation history')
    history_parser.add_argument(
        '--ticker',
        help='Filter by ticker'
    )
    history_parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Number of recommendations to show (default: 20)'
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    if not args.command:
        parser.print_help()
        return 0

    # Execute command
    try:
        if args.command == 'performance':
            cmd_performance(args)
        elif args.command == 'backtest':
            cmd_backtest(args)
        elif args.command == 'update':
            cmd_update(args)
        elif args.command == 'positions':
            cmd_positions(args)
        elif args.command == 'ticker':
            cmd_ticker_stats(args)
        elif args.command == 'history':
            cmd_history(args)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user.\n")
        return 130

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
