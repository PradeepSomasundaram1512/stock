"""
Comprehensive Market Scanner
Scans entire market to find best trading opportunities
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from graph.autonomous_decision_graph import get_autonomous_decision_graph
from notifications.discord_notifier import get_discord_notifier
from notifications.email_notifier import get_email_notifier
from enhancements.multi_timeframe import get_mtf_analyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Comprehensive market universe - top liquid stocks across sectors
MARKET_UNIVERSE = [
    # Mega Cap Tech
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'CRM',
    'ORCL', 'ADBE', 'NFLX', 'CSCO', 'AVGO', 'QCOM', 'TXN', 'AMAT', 'NOW', 'INTU',

    # Cloud & AI
    'SNOW', 'PLTR', 'DDOG', 'NET', 'MDB', 'CRWD', 'ZS', 'OKTA', 'PANW', 'FTNT',

    # Semiconductors
    'TSM', 'ASML', 'MU', 'LRCX', 'KLAC', 'MRVL', 'NXPI', 'ADI', 'MCHP',

    # E-commerce & Fintech
    'SHOP', 'SQ', 'COIN', 'HOOD', 'SOFI', 'PYPL', 'UBER', 'LYFT', 'ABNB', 'DASH',

    # Financial Services
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'V', 'MA', 'BX', 'KKR',

    # Healthcare & Biotech
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'ABT', 'DHR', 'LLY', 'BMY', 'AMGN',
    'GILD', 'VRTX', 'REGN', 'BIIB', 'MRNA', 'BNTX',

    # Consumer Discretionary
    'WMT', 'HD', 'TGT', 'LOW', 'NKE', 'SBUX', 'MCD', 'BABA', 'JD', 'PDD',
    'LULU', 'RH', 'ETSY', 'W',

    # Consumer Staples
    'PG', 'KO', 'PEP', 'COST', 'MDLZ', 'CL', 'KMB', 'GIS',

    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'OXY', 'HAL', 'DVN',

    # Industrial & Manufacturing
    'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'FDX', 'EMR',

    # Communication & Media
    'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'NFLX', 'SPOT', 'RBLX',

    # Electric Vehicles
    'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'F', 'GM',

    # Real Estate & REITs
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'O',

    # Materials
    'LIN', 'APD', 'NEM', 'FCX', 'GOLD',

    # Crypto-Related
    'MSTR', 'MARA', 'RIOT', 'CLSK',

    # Meme Stocks (high volatility - trade carefully!)
    'GME', 'AMC', 'BBBY',

    # ETFs (for market context)
    'SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLY', 'XLP',
    'VTI', 'VOO', 'ARKK', 'ARKG', 'ARKW'
]


class MarketScanner:
    """Scan entire market for best opportunities"""

    def __init__(self, budget: float = 1000):
        """
        Initialize market scanner

        Args:
            budget: Monthly budget in dollars
        """
        self.budget = budget
        self.graph = get_autonomous_decision_graph()
        self.mtf_analyzer = get_mtf_analyzer()
        self.discord = get_discord_notifier()
        self.email = get_email_notifier()

    def scan_market(self, top_n: int = 10) -> Dict[str, List[Dict]]:
        """
        Scan entire market and find top opportunities

        Args:
            top_n: Number of top picks to return

        Returns:
            Dictionary with top BUY and SELL opportunities
        """
        logger.info("\n" + "="*70)
        logger.info("COMPREHENSIVE MARKET SCAN")
        logger.info(f"Budget: ${self.budget:,.0f}")
        logger.info(f"Analyzing {len(MARKET_UNIVERSE)} stocks...")
        logger.info("="*70)

        all_buys = []
        all_sells = []
        all_holds = []

        for i, ticker in enumerate(MARKET_UNIVERSE, 1):
            try:
                logger.info(f"\n[{i}/{len(MARKET_UNIVERSE)}] Analyzing {ticker}...")

                # Multi-timeframe analysis
                mtf_result = self.mtf_analyzer.analyze(ticker)

                if mtf_result.get('error'):
                    logger.warning(f"  Skipping {ticker}: {mtf_result['error']}")
                    continue

                signal = mtf_result['overall_signal']
                confidence = mtf_result['confidence']

                # Get current price
                price = 0
                for tf in mtf_result['timeframes'].values():
                    if tf.get('price', 0) > 0:
                        price = tf['price']
                        break

                if price == 0:
                    logger.warning(f"  Skipping {ticker}: No price data")
                    continue

                stock_data = {
                    'ticker': ticker,
                    'signal': signal,
                    'confidence': confidence,
                    'price': price,
                    'alignment': mtf_result['alignment'],
                    'explanation': mtf_result['explanation']
                }

                # Calculate targets and stops (simple 3% target, 2% stop)
                if signal == 'BUY':
                    stock_data['price_target'] = price * 1.03
                    stock_data['stop_loss'] = price * 0.98
                    all_buys.append(stock_data)
                    logger.info(f"  🟢 BUY: {ticker} @ ${price:.2f} ({confidence*100:.0f}%)")

                elif signal == 'SELL':
                    all_sells.append(stock_data)
                    logger.info(f"  🔴 SELL: {ticker} @ ${price:.2f} ({confidence*100:.0f}%)")

                else:
                    all_holds.append(stock_data)
                    logger.info(f"  🟡 HOLD: {ticker} @ ${price:.2f}")

            except Exception as e:
                logger.error(f"  ❌ Error analyzing {ticker}: {e}")
                continue

        # Sort by confidence
        all_buys.sort(key=lambda x: x['confidence'], reverse=True)
        all_sells.sort(key=lambda x: x['confidence'], reverse=True)

        # Get top picks
        top_buys = all_buys[:top_n]
        top_sells = all_sells[:top_n]

        logger.info("\n" + "="*70)
        logger.info("SCAN COMPLETE")
        logger.info(f"🟢 BUY Signals: {len(all_buys)}")
        logger.info(f"🔴 SELL Signals: {len(all_sells)}")
        logger.info(f"🟡 HOLD Signals: {len(all_holds)}")
        logger.info("="*70)

        return {
            'buys': top_buys,
            'sells': top_sells,
            'holds': all_holds,
            'scan_time': datetime.now().isoformat(),
            'total_analyzed': len(MARKET_UNIVERSE)
        }

    def generate_monthly_plan(self, results: Dict) -> str:
        """
        Generate investment plan for monthly budget

        Args:
            results: Scan results from scan_market()

        Returns:
            Formatted investment plan
        """
        buys = results['buys']

        if not buys:
            return "\nNo BUY opportunities found in market scan."

        plan = f"\n{'='*70}\n"
        plan += f"💰 MONTHLY INVESTMENT PLAN - ${self.budget:,.0f} BUDGET\n"
        plan += f"{'='*70}\n\n"
        plan += f"Scan Time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
        plan += f"Stocks Analyzed: {results['total_analyzed']}\n"
        plan += f"BUY Opportunities Found: {len(buys)}\n\n"

        # Select top 3-5 stocks based on confidence
        num_positions = min(3, len(buys))  # Max 3 positions for $1000 budget
        top_picks = buys[:num_positions]

        plan += f"STRATEGY: Diversify across {num_positions} high-confidence picks\n\n"

        # Calculate allocation (weighted by confidence)
        total_confidence = sum(s['confidence'] for s in top_picks)

        remaining_budget = self.budget
        positions = []

        for i, stock in enumerate(top_picks, 1):
            # Allocate budget proportional to confidence
            weight = stock['confidence'] / total_confidence
            allocation = self.budget * weight
            shares = int(allocation / stock['price'])
            actual_cost = shares * stock['price']
            remaining_budget -= actual_cost

            plan += f"[{i}] {stock['ticker']}\n"
            plan += f"    Signal: {stock['signal']}\n"
            plan += f"    Price: ${stock['price']:.2f}\n"
            plan += f"    Confidence: {stock['confidence']*100:.0f}%\n"
            plan += f"    Alignment: {stock['alignment']}/3 timeframes\n"
            plan += f"    {stock['explanation']}\n"
            plan += f"    📊 Allocation: ${allocation:.0f} → Buy {shares} shares (${actual_cost:.2f})\n"

            if 'price_target' in stock:
                gain = ((stock['price_target'] / stock['price']) - 1) * 100
                profit = (stock['price_target'] - stock['price']) * shares
                plan += f"    🎯 Target: ${stock['price_target']:.2f} (+{gain:.1f}%) = ${profit:.2f} profit\n"

            if 'stop_loss' in stock:
                loss = ((stock['stop_loss'] / stock['price']) - 1) * 100
                loss_amount = (stock['price'] - stock['stop_loss']) * shares
                plan += f"    ⛔ Stop: ${stock['stop_loss']:.2f} ({loss:.1f}%) = ${loss_amount:.2f} max loss\n"

            plan += "\n"

            positions.append({
                'ticker': stock['ticker'],
                'shares': shares,
                'cost': actual_cost,
                'target': stock.get('price_target', 0),
                'stop': stock.get('stop_loss', 0)
            })

        # Summary
        plan += f"{'='*70}\n"
        plan += f"MONTHLY BUDGET: ${self.budget:,.0f}\n"
        plan += f"ALLOCATED: ${self.budget - remaining_budget:.2f}\n"
        plan += f"REMAINING: ${remaining_budget:.2f}\n"
        plan += f"{'='*70}\n\n"

        # Expected returns
        total_target_profit = sum((p['target'] - buys[i]['price']) * p['shares']
                                  for i, p in enumerate(positions) if p['target'] > 0)
        total_max_loss = sum((buys[i]['price'] - p['stop']) * p['shares']
                            for i, p in enumerate(positions) if p['stop'] > 0)

        if total_target_profit > 0:
            roi = (total_target_profit / (self.budget - remaining_budget)) * 100
            plan += f"📈 EXPECTED PROFIT (if all targets hit): ${total_target_profit:.2f} (+{roi:.1f}% ROI)\n"

        if total_max_loss > 0:
            risk = (total_max_loss / (self.budget - remaining_budget)) * 100
            plan += f"📉 MAX RISK (if all stops hit): ${total_max_loss:.2f} (-{risk:.1f}%)\n"

        plan += f"\n{'='*70}\n"
        plan += "⚠️  IMPORTANT REMINDERS:\n"
        plan += "- Set stop losses immediately after buying\n"
        plan += "- Monitor positions daily\n"
        plan += "- Take profits at targets\n"
        plan += "- Never risk more than you can afford to lose\n"
        plan += f"{'='*70}\n"

        return plan

    def send_alerts(self, results: Dict, plan: str):
        """Send scan results via Discord and Email"""

        buys = results['buys']

        # Send to Discord
        if self.discord.enabled and buys:
            logger.info("\nSending Discord alert...")
            self.discord.send_market_open_alert(buys[:5], [])

        # Send to Email
        if self.email.enabled:
            logger.info("Sending Email alert...")
            subject = f"Market Scan Results - {len(buys)} BUY Opportunities"
            body = plan
            self.email.send_email(subject, body)


def main():
    """Run comprehensive market scan"""
    import argparse

    parser = argparse.ArgumentParser(description="Scan entire market for best opportunities")
    parser.add_argument('--budget', type=float, default=1000,
                       help='Monthly budget in dollars (default: 1000)')
    parser.add_argument('--top', type=int, default=10,
                       help='Number of top picks to show (default: 10)')
    args = parser.parse_args()

    scanner = MarketScanner(budget=args.budget)

    # Scan market
    results = scanner.scan_market(top_n=args.top)

    # Generate monthly plan
    plan = scanner.generate_monthly_plan(results)
    print(plan)

    # Send alerts
    scanner.send_alerts(results, plan)

    logger.info("\n✅ Market scan complete!")


if __name__ == '__main__':
    main()
