"""
Daily Dashboard with Full Market Scanner
Analyzes ALL US stocks (5000+) and provides daily recommendations
"""

import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from daily_dashboard import DailyDashboard
from full_market_scanner import FullMarketScanner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FullMarketDashboard(DailyDashboard):
    """Daily dashboard using full market scanner"""

    def __init__(self, monthly_budget: float = 1000):
        """Initialize with full market scanner"""
        super().__init__(monthly_budget)
        self.full_scanner = FullMarketScanner(monthly_budget)

    def find_new_opportunities(self, max_positions: int = 3) -> list:
        """
        Find opportunities by scanning ENTIRE market

        Returns:
            List of buy opportunities
        """
        status = self.portfolio.get_monthly_status()
        available_cash = status['current_cash']
        num_open_positions = status['num_positions']

        logger.info(f"\n{'='*70}")
        logger.info("SCANNING ENTIRE MARKET FOR OPPORTUNITIES")
        logger.info(f"Available Cash: ${available_cash:.2f}")
        logger.info(f"Open Positions: {num_open_positions}/{max_positions}")
        logger.info(f"{'='*70}")

        if num_open_positions >= max_positions:
            logger.info("✋ Maximum positions reached")
            return []

        if available_cash < 50:
            logger.info("✋ Insufficient cash")
            return []

        # Scan ENTIRE market
        # Filter by price we can afford
        max_affordable = available_cash * 0.4  # Use 40% of cash per position

        logger.info(f"\n⚡ Scanning ALL US stocks...")
        logger.info(f"Max affordable price: ${max_affordable:.2f}")
        logger.info("This will take 10-30 minutes on first run...")

        results = self.full_scanner.scan_full_market(
            min_price=5.0,
            max_price=max_affordable,
            min_confidence=0.75,
            top_n=10
        )

        top_buys = results['buys']

        if not top_buys:
            logger.info("No qualifying opportunities found")
            return []

        # Filter and prepare opportunities
        open_tickers = [pos['ticker'] for pos in status['open_positions']]
        open_sectors = [pos.get('sector') for pos in status['open_positions']]

        opportunities = []

        for buy in top_buys:
            ticker = buy['ticker']
            price = buy['price']
            confidence = buy['confidence']

            if ticker in open_tickers:
                continue

            # Calculate shares
            allocation = min(available_cash * 0.35, available_cash / (max_positions - num_open_positions))
            shares = int(allocation / price)

            if shares < 1:
                continue

            cost = shares * price

            sector = self._get_sector(ticker)

            # Prefer sector diversification but don't be too strict
            if sector in open_sectors and len(opportunities) >= 1:
                logger.info(f"  Skipping {ticker} for sector diversity ({sector})")
                continue

            opportunities.append({
                'ticker': ticker,
                'price': price,
                'shares': shares,
                'cost': cost,
                'confidence': confidence,
                'sector': sector,
                'target': buy.get('price_target'),
                'stop': buy.get('stop_loss'),
                'explanation': buy.get('explanation', '')
            })

            logger.info(f"  🟢 {ticker} @ ${price:.2f} x {shares} = ${cost:.2f} ({confidence*100:.0f}%)")

            if len(opportunities) >= (max_positions - num_open_positions):
                break

        return opportunities


def main():
    """Run full market daily dashboard"""
    import argparse

    parser = argparse.ArgumentParser(description="Daily dashboard with full market scan")
    parser.add_argument('--budget', type=float, default=1000, help='Monthly budget')

    args = parser.parse_args()

    logger.info("\n" + "="*70)
    logger.info("🌍 FULL MARKET DAILY DASHBOARD")
    logger.info("Analyzing ALL US stocks (5000+)")
    logger.info("="*70)

    dashboard = FullMarketDashboard(monthly_budget=args.budget)
    dashboard.run_daily_analysis()


if __name__ == '__main__':
    main()
