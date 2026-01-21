"""
Market Scanner - Analyzes multiple stocks and ranks them.
Finds best Buy, Hold, and Sell opportunities.
"""

import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
import sys
from datetime import datetime
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from graph.decision_graph import get_decision_graph
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class MarketScanner:
    """Scans multiple stocks and ranks them by decision and confidence."""

    def __init__(self, max_workers: int = 5):
        """
        Initialize the Market Scanner.

        Args:
            max_workers: Maximum parallel workers for scanning
        """
        self.decision_graph = get_decision_graph()
        self.max_workers = max_workers

    def scan_stocks(
        self,
        tickers: List[str],
        period: str = "6mo",
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Scan multiple stocks in parallel.

        Args:
            tickers: List of ticker symbols
            period: Data period for analysis
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

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(self._analyze_stock, ticker, period): ticker
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
                        decision = result['decision'].get('decision', 'ERROR')
                        confidence = result['decision'].get('confidence', 0) * 100
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

    def _analyze_stock(self, ticker: str, period: str) -> Dict[str, Any]:
        """
        Analyze a single stock.

        Args:
            ticker: Stock ticker
            period: Data period

        Returns:
            Analysis result dictionary
        """
        result = self.decision_graph.run(ticker, period=period)
        return result

    def rank_stocks(
        self,
        results: List[Dict[str, Any]],
        top_n: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
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

            decision = result['decision'].get('decision', 'HOLD')
            confidence = result['decision'].get('confidence', 0)
            ticker = result.get('ticker', 'UNKNOWN')
            features = result.get('features', {})

            stock_data = {
                'ticker': ticker,
                'decision': decision,
                'confidence': confidence,
                'price': features.get('latest_price', 0),
                'change_20d': features.get('price_change_20d', 0),
                'rsi': features.get('rsi', 50),
                'trend': features.get('trend', 'neutral'),
                'volatility': features.get('volatility_level', 'unknown'),
                'explanation': result['decision'].get('explanation', '')[:200] + '...'
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

    def print_rankings(self, rankings: Dict[str, List[Dict[str, Any]]]):
        """
        Print formatted rankings.

        Args:
            rankings: Rankings dictionary from rank_stocks()
        """
        print("\n" + "="*70)
        print("📊 TOP STOCK RECOMMENDATIONS")
        print("="*70)

        # Print BUY recommendations
        print("\n🟢 TOP BUY OPPORTUNITIES")
        print("-" * 70)
        if rankings['buy']:
            print(f"{'Rank':<6} {'Ticker':<8} {'Conf':<8} {'Price':<10} {'20d Chg':<10} {'RSI':<8} {'Trend':<10}")
            print("-" * 70)
            for i, stock in enumerate(rankings['buy'], 1):
                print(
                    f"{i:<6} "
                    f"{stock['ticker']:<8} "
                    f"{stock['confidence']*100:>6.1f}% "
                    f"${stock['price']:>8.2f} "
                    f"{stock['change_20d']:>8.2f}% "
                    f"{stock['rsi']:>6.1f} "
                    f"{stock['trend']:<10}"
                )
        else:
            print("  No BUY recommendations found.")

        # Print HOLD recommendations
        print("\n🟡 TOP HOLD POSITIONS")
        print("-" * 70)
        if rankings['hold']:
            print(f"{'Rank':<6} {'Ticker':<8} {'Conf':<8} {'Price':<10} {'20d Chg':<10} {'RSI':<8} {'Trend':<10}")
            print("-" * 70)
            for i, stock in enumerate(rankings['hold'], 1):
                print(
                    f"{i:<6} "
                    f"{stock['ticker']:<8} "
                    f"{stock['confidence']*100:>6.1f}% "
                    f"${stock['price']:>8.2f} "
                    f"{stock['change_20d']:>8.2f}% "
                    f"{stock['rsi']:>6.1f} "
                    f"{stock['trend']:<10}"
                )
        else:
            print("  No HOLD recommendations found.")

        # Print SELL recommendations
        print("\n🔴 TOP SELL OPPORTUNITIES")
        print("-" * 70)
        if rankings['sell']:
            print(f"{'Rank':<6} {'Ticker':<8} {'Conf':<8} {'Price':<10} {'20d Chg':<10} {'RSI':<8} {'Trend':<10}")
            print("-" * 70)
            for i, stock in enumerate(rankings['sell'], 1):
                print(
                    f"{i:<6} "
                    f"{stock['ticker']:<8} "
                    f"{stock['confidence']*100:>6.1f}% "
                    f"${stock['price']:>8.2f} "
                    f"{stock['change_20d']:>8.2f}% "
                    f"{stock['rsi']:>6.1f} "
                    f"{stock['trend']:<10}"
                )
        else:
            print("  No SELL recommendations found.")

        print("\n" + "="*70)
        print("⚠️  DISCLAIMER: This is NOT financial advice.")
        print("Always do your own research and consult professionals.")
        print("="*70 + "\n")

    def export_to_csv(self, rankings: Dict[str, List[Dict[str, Any]]], filename: str = "stock_rankings.csv"):
        """
        Export rankings to CSV file.

        Args:
            rankings: Rankings dictionary
            filename: Output filename
        """
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


def get_sp500_tickers() -> List[str]:
    """
    Get S&P 500 ticker list.

    Returns:
        List of S&P 500 tickers
    """
    # Top 100 S&P 500 stocks by market cap (as of 2024)
    top_100 = [
        # Mega caps
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "LLY", "V",
        # Large caps
        "UNH", "XOM", "JPM", "JNJ", "WMT", "MA", "PG", "AVGO", "HD", "CVX",
        "MRK", "ABBV", "COST", "KO", "PEP", "ADBE", "NFLX", "CRM", "BAC", "TMO",
        "CSCO", "MCD", "ACN", "LIN", "ABT", "WFC", "DHR", "VZ", "ORCL", "PM",
        "TXN", "CMCSA", "INTC", "AMD", "NKE", "DIS", "INTU", "QCOM", "NEE", "PFE",
        # Mid-large caps
        "UPS", "HON", "RTX", "T", "LOW", "BMY", "UNP", "SPGI", "AMGN", "CAT",
        "BA", "GE", "DE", "SBUX", "IBM", "AXP", "BLK", "MDT", "GILD", "AMAT",
        "CVS", "SYK", "ADI", "MDLZ", "PLD", "NOW", "ISRG", "TJX", "VRTX", "ZTS",
        "REGN", "MMC", "CI", "LRCX", "C", "AMT", "BDX", "CB", "MO", "SO",
        "DUK", "SCHW", "ETN", "BSX", "PNC", "TGT", "CME", "CL", "ITW", "SLB"
    ]
    return top_100


def get_popular_stocks() -> List[str]:
    """
    Get list of popular/actively traded stocks.

    Returns:
        List of popular ticker symbols
    """
    return [
        # FAANG + Tech
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "NVDA", "TSLA",
        # Tech
        "AMD", "INTC", "CRM", "ADBE", "ORCL", "CSCO", "QCOM", "AVGO",
        # Finance
        "JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA",
        # Consumer
        "WMT", "HD", "NKE", "SBUX", "MCD", "DIS", "COST", "TGT",
        # Healthcare
        "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT",
        # Energy
        "XOM", "CVX", "COP", "SLB",
        # Industrial
        "BA", "CAT", "GE", "UPS", "RTX", "HON",
        # Other
        "KO", "PEP", "PG", "VZ", "T", "BRK.B"
    ]


# Singleton instance
_market_scanner_instance = None


def get_market_scanner() -> MarketScanner:
    """Get or create the MarketScanner singleton."""
    global _market_scanner_instance
    if _market_scanner_instance is None:
        _market_scanner_instance = MarketScanner()
    return _market_scanner_instance
