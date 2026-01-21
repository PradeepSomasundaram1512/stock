"""
Full Market Scanner
Scans ALL stocks on major exchanges (NYSE, NASDAQ, AMEX)
Finds best opportunities from 5000+ stocks
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from portfolio_manager import get_portfolio_manager
from enhancements.multi_timeframe import get_mtf_analyzer
from notifications.discord_notifier import get_discord_notifier
from notifications.email_notifier import get_email_notifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_tickers() -> List[str]:
    """
    Get ALL stock tickers from major US exchanges

    Returns:
        List of all stock tickers (5000+ stocks)
    """
    logger.info("Fetching complete list of stocks from US exchanges...")

    all_tickers = []

    try:
        # Method 1: Use pandas-datareader to get stock lists
        import pandas_datareader as pdr

        # Get NYSE stocks
        try:
            nyse = pdr.get_nasdaq_symbols()
            nyse_tickers = nyse.index.tolist()
            all_tickers.extend(nyse_tickers)
            logger.info(f"Found {len(nyse_tickers)} NYSE/NASDAQ stocks")
        except Exception as e:
            logger.warning(f"Could not fetch from pandas-datareader: {e}")
    except ImportError:
        logger.warning("pandas-datareader not installed")

    # Method 2: Use FTP from NASDAQ
    if not all_tickers:
        try:
            import io
            import requests

            # NASDAQ traded symbols
            logger.info("Fetching from NASDAQ FTP...")

            # Get NASDAQ listed
            nasdaq_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
            response = requests.get(nasdaq_url.replace('ftp://', 'http://'))
            nasdaq_df = pd.read_csv(io.StringIO(response.text), sep='|')
            nasdaq_tickers = nasdaq_df['Symbol'].dropna().tolist()
            all_tickers.extend(nasdaq_tickers)
            logger.info(f"Found {len(nasdaq_tickers)} NASDAQ stocks")

            # Get other exchanges (NYSE, AMEX, etc.)
            other_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
            response = requests.get(other_url.replace('ftp://', 'http://'))
            other_df = pd.read_csv(io.StringIO(response.text), sep='|')
            other_tickers = other_df['ACT Symbol'].dropna().tolist()
            all_tickers.extend(other_tickers)
            logger.info(f"Found {len(other_tickers)} NYSE/AMEX stocks")

        except Exception as e:
            logger.error(f"Could not fetch from NASDAQ FTP: {e}")

    # Method 3: Fallback - use a comprehensive predefined list
    if not all_tickers:
        logger.info("Using comprehensive predefined stock list...")
        all_tickers = get_comprehensive_ticker_list()

    # Clean tickers
    all_tickers = [t.strip().upper() for t in all_tickers if t and len(t) <= 5]

    # Remove test symbols and special characters
    all_tickers = [t for t in all_tickers if not any(x in t for x in ['$', '^', '=', 'TEST'])]

    # Remove duplicates
    all_tickers = list(set(all_tickers))

    # Sort
    all_tickers.sort()

    logger.info(f"✅ Total stocks to scan: {len(all_tickers)}")

    return all_tickers


def get_comprehensive_ticker_list() -> List[str]:
    """
    Comprehensive list of major US stocks across all sectors
    This is a fallback if API fetching fails
    """
    # This list contains ~1000 most liquid stocks
    # In production, the API methods above will get 5000+
    return [
        # Large Cap Tech
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC',
        'CRM', 'ORCL', 'ADBE', 'NFLX', 'CSCO', 'AVGO', 'QCOM', 'TXN', 'AMAT', 'NOW',
        'INTU', 'IBM', 'DELL', 'HPQ', 'HPE', 'NTAP', 'STX', 'WDC',

        # Cloud & SaaS
        'SNOW', 'PLTR', 'DDOG', 'NET', 'MDB', 'CRWD', 'ZS', 'OKTA', 'PANW', 'FTNT',
        'WDAY', 'VEEV', 'TEAM', 'ZM', 'DOCU', 'TWLO', 'SPLK', 'DOMO',

        # Semiconductors
        'TSM', 'ASML', 'MU', 'LRCX', 'KLAC', 'MRVL', 'NXPI', 'ADI', 'MCHP', 'ON',
        'SWKS', 'QRVO', 'MPWR', 'WOLF', 'RMBS', 'CRUS', 'SIMO', 'ALGM',

        # E-commerce & Payments
        'SHOP', 'SQ', 'PYPL', 'COIN', 'HOOD', 'SOFI', 'UBER', 'LYFT', 'ABNB', 'DASH',
        'EBAY', 'ETSY', 'W', 'CHWY', 'PINS', 'SNAP', 'RBLX', 'U',

        # Financials
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA',
        'BX', 'KKR', 'APO', 'ARES', 'COF', 'USB', 'PNC', 'TFC', 'BK', 'STT',
        'ALLY', 'SYF', 'DFS', 'FITB', 'RF', 'CFG', 'KEY', 'HBAN', 'CMA', 'ZION',

        # Healthcare & Pharma
        'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'ABT', 'DHR', 'LLY', 'BMY',
        'AMGN', 'GILD', 'VRTX', 'REGN', 'BIIB', 'MRNA', 'BNTX', 'ISRG', 'SYK',
        'BSX', 'MDT', 'EW', 'HOLX', 'BAX', 'BDX', 'ZBH', 'ALGN', 'DXCM', 'PODD',

        # Consumer Discretionary
        'WMT', 'HD', 'TGT', 'LOW', 'NKE', 'SBUX', 'MCD', 'BABA', 'JD', 'PDD',
        'LULU', 'RH', 'ROST', 'TJX', 'ULTA', 'DG', 'DLTR', 'FIVE', 'BBY', 'BURL',
        'GM', 'F', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'TSLA',

        # Consumer Staples
        'PG', 'KO', 'PEP', 'COST', 'MDLZ', 'CL', 'KMB', 'GIS', 'K', 'CPB',
        'CAG', 'SJM', 'HSY', 'MKC', 'CHD', 'CLX', 'TAP', 'TSN', 'HRL',

        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'OXY', 'HAL', 'DVN',
        'PXD', 'VLO', 'HES', 'APA', 'MRO', 'FANG', 'CTRA', 'OVV',

        # Industrials
        'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'FDX',
        'EMR', 'ETN', 'ITW', 'PH', 'CMI', 'GD', 'NOC', 'LHX', 'TXT', 'ROK',

        # Communications
        'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR', 'FOXA', 'FOX', 'NWSA', 'NWS',
        'SPOT', 'WBD', 'PARA', 'OMC', 'IPG',

        # Real Estate
        'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'O', 'SPG', 'WELL', 'DLR', 'AVB',
        'EQR', 'VTR', 'ARE', 'MAA', 'INVH', 'ESS', 'UDR', 'CPT', 'HST', 'SLG',

        # Materials
        'LIN', 'APD', 'NEM', 'FCX', 'GOLD', 'NUE', 'DD', 'DOW', 'ECL', 'SHW',
        'PPG', 'CTVA', 'ALB', 'VMC', 'MLM', 'PKG', 'IP', 'WRK',

        # Utilities
        'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'PEG',
        'WEC', 'ES', 'FE', 'EIX', 'ETR', 'AWK', 'DTE', 'PPL', 'AEE', 'CMS',

        # Crypto-Related
        'MSTR', 'COIN', 'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF', 'BTBT',

        # Meme & High Volatility
        'GME', 'AMC', 'BBBY', 'BB', 'NOK', 'CLOV', 'WISH', 'WKHS', 'RIDE',

        # REITs
        'VNQ', 'IYR', 'XLRE',

        # Major ETFs
        'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'IVV', 'VEA', 'IEFA', 'VWO',
        'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE',
        'ARKK', 'ARKG', 'ARKW', 'ARKQ', 'ARKF',
    ]


class FullMarketScanner:
    """Scan entire market - ALL stocks"""

    def __init__(self, monthly_budget: float = 1000):
        """Initialize full market scanner"""
        self.budget = monthly_budget
        self.mtf = get_mtf_analyzer()
        self.portfolio = get_portfolio_manager(monthly_budget)
        self.discord = get_discord_notifier()
        self.email = get_email_notifier()

    def scan_full_market(self,
                        min_price: float = 5.0,
                        max_price: float = 1000.0,
                        min_confidence: float = 0.75,
                        top_n: int = 10) -> Dict[str, List[Dict]]:
        """
        Scan entire market for opportunities

        Args:
            min_price: Minimum stock price (filter penny stocks)
            max_price: Maximum stock price (filter if too expensive)
            min_confidence: Minimum confidence threshold
            top_n: Number of top picks to return

        Returns:
            Scan results with top opportunities
        """
        logger.info("\n" + "="*70)
        logger.info("FULL MARKET SCAN - ALL US STOCKS")
        logger.info(f"Budget: ${self.budget:,.0f}")
        logger.info(f"Filters: ${min_price:.2f} - ${max_price:.2f}, Confidence ≥ {min_confidence*100:.0f}%")
        logger.info("="*70)

        # Get all tickers
        all_tickers = get_all_tickers()
        total_tickers = len(all_tickers)

        logger.info(f"\nScanning {total_tickers} stocks...")
        logger.info("This may take 10-30 minutes depending on market data availability.\n")

        all_buys = []
        all_sells = []
        analyzed_count = 0
        skipped_count = 0

        for i, ticker in enumerate(all_tickers, 1):
            # Progress indicator every 100 stocks
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{total_tickers} ({i/total_tickers*100:.1f}%) - "
                          f"Found {len(all_buys)} BUY signals so far")

            try:
                # Analyze with multi-timeframe
                result = self.mtf.analyze(ticker)

                if result.get('error'):
                    skipped_count += 1
                    continue

                signal = result['overall_signal']
                confidence = result['confidence']

                # Get price from timeframes
                price = 0
                for tf_data in result['timeframes'].values():
                    if tf_data.get('price', 0) > 0:
                        price = tf_data['price']
                        break

                if price == 0:
                    skipped_count += 1
                    continue

                # Apply filters
                if price < min_price or price > max_price:
                    skipped_count += 1
                    continue

                if confidence < min_confidence:
                    skipped_count += 1
                    continue

                analyzed_count += 1

                stock_data = {
                    'ticker': ticker,
                    'signal': signal,
                    'confidence': confidence,
                    'price': price,
                    'alignment': result['alignment'],
                    'explanation': result['explanation']
                }

                # Calculate targets/stops
                if signal == 'BUY':
                    stock_data['price_target'] = price * 1.03
                    stock_data['stop_loss'] = price * 0.98
                    all_buys.append(stock_data)

                    # Log high confidence finds immediately
                    if confidence >= 0.90:
                        logger.info(f"  🔥 HIGH CONFIDENCE: {ticker} @ ${price:.2f} ({confidence*100:.0f}%)")

                elif signal == 'SELL':
                    all_sells.append(stock_data)

            except KeyboardInterrupt:
                logger.warning("\n⚠️  Scan interrupted by user")
                break
            except Exception as e:
                skipped_count += 1
                continue

        # Sort by confidence
        all_buys.sort(key=lambda x: x['confidence'], reverse=True)
        all_sells.sort(key=lambda x: x['confidence'], reverse=True)

        # Get top picks
        top_buys = all_buys[:top_n]

        logger.info("\n" + "="*70)
        logger.info("FULL MARKET SCAN COMPLETE")
        logger.info(f"Total Tickers: {total_tickers}")
        logger.info(f"Analyzed Successfully: {analyzed_count}")
        logger.info(f"Skipped (no data/filters): {skipped_count}")
        logger.info(f"🟢 BUY Signals: {len(all_buys)} (showing top {len(top_buys)})")
        logger.info(f"🔴 SELL Signals: {len(all_sells)}")
        logger.info("="*70)

        return {
            'buys': top_buys,
            'sells': all_sells[:top_n],
            'all_buys': all_buys,
            'scan_time': datetime.now().isoformat(),
            'total_scanned': total_tickers,
            'analyzed': analyzed_count,
            'skipped': skipped_count
        }

    def generate_report(self, results: Dict) -> str:
        """Generate investment report"""
        buys = results['buys']

        report = f"\n{'='*70}\n"
        report += f"💰 FULL MARKET SCAN - INVESTMENT PLAN\n"
        report += f"{'='*70}\n\n"
        report += f"Scan Time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
        report += f"Total Stocks Scanned: {results['total_scanned']:,}\n"
        report += f"Successfully Analyzed: {results['analyzed']}\n"
        report += f"BUY Opportunities Found: {len(results['all_buys'])}\n"
        report += f"Monthly Budget: ${self.budget:,.0f}\n\n"

        if not buys:
            report += "No qualifying opportunities found.\n"
            return report

        report += f"{'='*70}\n"
        report += f"🏆 TOP {len(buys)} OPPORTUNITIES\n"
        report += f"{'='*70}\n\n"

        for i, stock in enumerate(buys, 1):
            report += f"[{i}] {stock['ticker']}\n"
            report += f"    Price: ${stock['price']:.2f}\n"
            report += f"    Confidence: {stock['confidence']*100:.0f}%\n"
            report += f"    Alignment: {stock['alignment']}/3 timeframes\n"
            report += f"    {stock['explanation']}\n"
            report += f"    🎯 Target: ${stock['price_target']:.2f} (+{((stock['price_target']/stock['price'])-1)*100:.1f}%)\n"
            report += f"    ⛔ Stop: ${stock['stop_loss']:.2f} ({((stock['stop_loss']/stock['price'])-1)*100:.1f}%)\n\n"

        return report


def main():
    """Run full market scan"""
    import argparse

    parser = argparse.ArgumentParser(description="Scan entire US stock market")
    parser.add_argument('--budget', type=float, default=1000, help='Monthly budget')
    parser.add_argument('--min-price', type=float, default=5.0, help='Min stock price')
    parser.add_argument('--max-price', type=float, default=1000.0, help='Max stock price')
    parser.add_argument('--min-confidence', type=float, default=0.75, help='Min confidence (0-1)')
    parser.add_argument('--top', type=int, default=10, help='Number of top picks')

    args = parser.parse_args()

    scanner = FullMarketScanner(monthly_budget=args.budget)

    # Scan
    results = scanner.scan_full_market(
        min_price=args.min_price,
        max_price=args.max_price,
        min_confidence=args.min_confidence,
        top_n=args.top
    )

    # Generate report
    report = scanner.generate_report(results)
    print(report)

    # Send notifications
    if results['buys'] and scanner.discord.enabled:
        scanner.discord.send_market_open_alert(results['buys'][:5], [])

    if results['buys'] and scanner.email.enabled:
        subject = f"Full Market Scan - {len(results['all_buys'])} Opportunities Found"
        scanner.email.send_email(subject, report)

    logger.info("\n✅ Full market scan complete!")


if __name__ == '__main__':
    main()
