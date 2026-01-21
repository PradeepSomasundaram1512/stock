"""
Autonomous Market Scanner - Scans multiple stocks with comprehensive analysis.
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
from scanner.market_scanner import get_sp500_tickers, get_popular_stocks
from graph.autonomous_decision_graph import get_autonomous_decision_graph
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import pandas as pd


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        AUTONOMOUS AI MARKET SCANNER                          ║
║                                                              ║
║  Comprehensive multi-stock analysis                          ║
║  Technical + Fundamental + News + Market Context             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def scan_stocks(
    tickers: List[str],
    period: str = "6mo",
    max_workers: int = 5,
    show_progress: bool = True
) -> List[Dict[str, Any]]:
    """
    Scan multiple stocks in parallel with autonomous analysis.

    Args:
        tickers: List of ticker symbols
        period: Data period for analysis
        max_workers: Maximum parallel workers
        show_progress: Whether to show progress messages

    Returns:
        List of analysis results
    """
    results = []
    total = len(tickers)

    if show_progress:
        print(f"\n{'='*70}")
        print(f"🔍 SCANNING {total} STOCKS...")
        print(f"{'='*70}\n")

    graph = get_autonomous_decision_graph()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ticker = {
            executor.submit(graph.run, ticker, period): ticker
            for ticker in tickers
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1

            try:
                result = future.result()
                results.append(result)

                if show_progress:
                    decision = result.get('decision', {}).get('decision', 'ERROR')
                    confidence = result.get('decision', {}).get('confidence', 0) * 100
                    print(f"[{completed}/{total}] ✓ {ticker:6s} - {decision:4s} ({confidence:5.1f}%)")

            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {str(e)}")
                if show_progress:
                    print(f"[{completed}/{total}] ✗ {ticker:6s} - ERROR")

    if show_progress:
        print(f"\n{'='*70}")
        print(f"✓ Scan complete: {len(results)}/{total} successful")
        print(f"{'='*70}\n")

    return results


def rank_stocks(results: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Rank stocks by decision type and confidence.

    Args:
        results: List of analysis results
        top_n: Number of top stocks to return per category

    Returns:
        Dictionary with 'buy', 'hold', 'sell' rankings
    """
    buy_stocks = []
    hold_stocks = []
    sell_stocks = []

    for result in results:
        if result.get('error'):
            continue

        decision_data = result.get('decision', {})
        decision = decision_data.get('decision', 'HOLD')
        confidence = decision_data.get('confidence', 0)
        ticker = result.get('ticker', 'UNKNOWN')
        features = result.get('features', {})
        fundamentals = result.get('fundamentals', {})

        stock_data = {
            'ticker': ticker,
            'decision': decision,
            'confidence': confidence,
            'price': features.get('latest_price', 0),
            'change_20d': features.get('price_change_20d', 0),
            'rsi': features.get('rsi', 50),
            'trend': features.get('trend', 'neutral'),
            'risk_level': decision_data.get('risk_level', 'unknown'),
            'valuation_score': fundamentals.get('valuation_score', 0.5),
            'health_score': fundamentals.get('health_score', 0.5),
            'growth_score': fundamentals.get('growth_score', 0.5),
            'reasoning': decision_data.get('reasoning', '')[:150] + '...'
        }

        if decision == 'BUY':
            buy_stocks.append(stock_data)
        elif decision == 'SELL':
            sell_stocks.append(stock_data)
        else:
            hold_stocks.append(stock_data)

    # Sort by confidence (descending)
    buy_stocks.sort(key=lambda x: x['confidence'], reverse=True)
    sell_stocks.sort(key=lambda x: x['confidence'], reverse=True)
    hold_stocks.sort(key=lambda x: x['confidence'], reverse=True)

    return {
        'buy': buy_stocks[:top_n],
        'hold': hold_stocks[:top_n],
        'sell': sell_stocks[:top_n]
    }


def print_rankings(rankings: Dict[str, List[Dict[str, Any]]]):
    """Print formatted rankings."""
    print("\n" + "="*70)
    print("📊 TOP STOCK RECOMMENDATIONS")
    print("="*70)

    # Print BUY recommendations
    print("\n🟢 TOP BUY OPPORTUNITIES")
    print("-" * 70)
    if rankings['buy']:
        print(f"{'Rank':<6} {'Ticker':<8} {'Conf':<8} {'Price':<10} {'Risk':<10} {'Val/Hlth/Grw':<15}")
        print("-" * 70)
        for i, stock in enumerate(rankings['buy'], 1):
            val = stock['valuation_score']
            hlth = stock['health_score']
            grw = stock['growth_score']
            scores = f"{val:.2f}/{hlth:.2f}/{grw:.2f}"

            print(
                f"{i:<6} "
                f"{stock['ticker']:<8} "
                f"{stock['confidence']*100:>6.1f}% "
                f"${stock['price']:>8.2f} "
                f"{stock['risk_level']:<10} "
                f"{scores:<15}"
            )
    else:
        print("  No BUY recommendations found.")

    # Print HOLD recommendations
    print("\n🟡 TOP HOLD POSITIONS")
    print("-" * 70)
    if rankings['hold']:
        print(f"{'Rank':<6} {'Ticker':<8} {'Conf':<8} {'Price':<10} {'Risk':<10} {'Val/Hlth/Grw':<15}")
        print("-" * 70)
        for i, stock in enumerate(rankings['hold'], 1):
            val = stock['valuation_score']
            hlth = stock['health_score']
            grw = stock['growth_score']
            scores = f"{val:.2f}/{hlth:.2f}/{grw:.2f}"

            print(
                f"{i:<6} "
                f"{stock['ticker']:<8} "
                f"{stock['confidence']*100:>6.1f}% "
                f"${stock['price']:>8.2f} "
                f"{stock['risk_level']:<10} "
                f"{scores:<15}"
            )
    else:
        print("  No HOLD recommendations found.")

    # Print SELL recommendations
    print("\n🔴 TOP SELL OPPORTUNITIES")
    print("-" * 70)
    if rankings['sell']:
        print(f"{'Rank':<6} {'Ticker':<8} {'Conf':<8} {'Price':<10} {'Risk':<10} {'Val/Hlth/Grw':<15}")
        print("-" * 70)
        for i, stock in enumerate(rankings['sell'], 1):
            val = stock['valuation_score']
            hlth = stock['health_score']
            grw = stock['growth_score']
            scores = f"{val:.2f}/{hlth:.2f}/{grw:.2f}"

            print(
                f"{i:<6} "
                f"{stock['ticker']:<8} "
                f"{stock['confidence']*100:>6.1f}% "
                f"${stock['price']:>8.2f} "
                f"{stock['risk_level']:<10} "
                f"{scores:<15}"
            )
    else:
        print("  No SELL recommendations found.")

    print("\n" + "="*70)
    print("⚠️  DISCLAIMER: This is NOT financial advice.")
    print("Always do your own research and consult professionals.")
    print("="*70 + "\n")


def export_to_csv(rankings: Dict[str, List[Dict[str, Any]]], filename: str):
    """Export rankings to CSV."""
    all_stocks = []

    for decision_type, stocks in rankings.items():
        for stock in stocks:
            stock_copy = stock.copy()
            stock_copy['decision'] = decision_type.upper()
            all_stocks.append(stock_copy)

    df = pd.DataFrame(all_stocks)
    df = df.sort_values(['decision', 'confidence'], ascending=[True, False])

    output_path = Path(filename)
    df.to_csv(output_path, index=False)
    print(f"✓ Rankings exported to: {output_path.absolute()}")


def main():
    """Main entry point for autonomous market scanner."""
    parser = argparse.ArgumentParser(
        description="Autonomous AI Market Scanner - Comprehensive multi-stock analysis"
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
        default=3,
        help='Number of parallel workers (default: 3, use fewer to avoid rate limits)'
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

        # Scan stocks
        results = scan_stocks(tickers, period=args.period, max_workers=args.workers)

        if not results:
            print("❌ No results obtained. Check your API key and internet connection.")
            return 1

        # Rank stocks
        rankings = rank_stocks(results, top_n=args.top)

        # Print rankings
        print_rankings(rankings)

        # Export if requested
        if args.export:
            export_to_csv(rankings, args.export)

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
