"""
Autonomous Stock Analysis - No expertise required.
Analyzes all available data and makes clear recommendations.
"""

import sys
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

from app.config import validate_config
from rag.ingest import initialize_knowledge_base
from graph.autonomous_decision_graph import get_autonomous_decision_graph


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          AUTONOMOUS AI STOCK ANALYZER                        ║
║                                                              ║
║  Comprehensive analysis for users with no expertise          ║
║  Combines: Technical + Fundamental + News + Market           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_decision_summary(result: dict):
    """Print comprehensive decision summary."""

    if result.get('error'):
        print(f"\n❌ Error: {result['error']}\n")
        return

    ticker = result.get('ticker', 'UNKNOWN')
    decision_data = result.get('decision', {})
    features = result.get('features', {})
    fundamentals = result.get('fundamentals', {})
    news = result.get('news_analysis', {})
    market = result.get('market_context', {})

    # Header
    print(f"\n{'='*70}")
    print(f"ANALYSIS REPORT: {ticker}")
    print(f"{'='*70}\n")

    # Company info
    company = fundamentals.get('company_name', ticker)
    sector = fundamentals.get('sector', 'Unknown')
    industry = fundamentals.get('industry', 'Unknown')

    print(f"📊 {company}")
    print(f"   Sector: {sector} | Industry: {industry}\n")

    # Current price
    price = features.get('latest_price', 0)
    change_20d = features.get('price_change_20d', 0)
    change_symbol = '+' if change_20d >= 0 else ''

    print(f"💰 Current Price: ${price:.2f}")
    print(f"   20-Day Change: {change_symbol}{change_20d:.2f}%\n")

    # THE DECISION (MOST IMPORTANT)
    print(f"{'='*70}")
    print(f"🎯 RECOMMENDATION")
    print(f"{'='*70}\n")

    decision = decision_data.get('decision', 'HOLD')
    confidence = decision_data.get('confidence', 0)

    # Colorful decision display
    if decision == 'BUY':
        symbol = '🟢'
        action_text = 'STRONG BUY' if confidence > 0.8 else 'BUY' if confidence > 0.6 else 'WEAK BUY'
    elif decision == 'SELL':
        symbol = '🔴'
        action_text = 'STRONG SELL' if confidence > 0.8 else 'SELL' if confidence > 0.6 else 'WEAK SELL'
    else:
        symbol = '🟡'
        action_text = 'HOLD'

    print(f"{symbol} {action_text}")
    print(f"   Confidence: {confidence:.1%}")
    risk_level = decision_data.get('risk_level') or 'unknown'
    print(f"   Risk Level: {risk_level.upper()}")
    print(f"   Time Horizon: {decision_data.get('time_horizon', 'unknown')}\n")

    # Reasoning
    print(f"📝 Why This Decision?")
    print(f"   {decision_data.get('reasoning', 'No reasoning provided')}\n")

    # Key factors
    key_factors = decision_data.get('key_factors', [])
    if key_factors:
        print(f"🔑 Key Factors:")
        for factor in key_factors:
            print(f"   • {factor}")
        print()

    # Price targets
    target = decision_data.get('price_target')
    stop_loss = decision_data.get('stop_loss')

    if target:
        print(f"🎯 Price Target: ${target:.2f}")
        if price > 0:
            upside = ((target - price) / price) * 100
            print(f"   Potential: {upside:+.1f}%")

    if stop_loss:
        print(f"🛑 Suggested Stop Loss: ${stop_loss:.2f}")
        if price > 0:
            risk = ((stop_loss - price) / price) * 100
            print(f"   Risk: {risk:+.1f}%")

    if target or stop_loss:
        print()

    # Alternative action
    alt_action = decision_data.get('alternative_action')
    if alt_action:
        print(f"🔄 If This Doesn't Work Out:")
        print(f"   {alt_action}\n")

    # Quick stats
    print(f"{'='*70}")
    print(f"📈 QUICK STATS")
    print(f"{'='*70}\n")

    # Technical
    print(f"Technical Analysis:")
    print(f"   Trend: {features.get('trend', 'unknown').capitalize()}")
    print(f"   RSI: {features.get('rsi', 50):.1f} ({features.get('rsi_signal', 'neutral')})")
    print(f"   MACD: {features.get('macd_signal', 'neutral').capitalize()}")
    print(f"   Volatility: {features.get('volatility_level', 'unknown').capitalize()}\n")

    # Fundamental
    print(f"Fundamental Analysis:")
    print(f"   Valuation Score: {fundamentals.get('valuation_score', 0.5):.2f}/1.0")
    print(f"   Health Score: {fundamentals.get('health_score', 0.5):.2f}/1.0")
    print(f"   Growth Score: {fundamentals.get('growth_score', 0.5):.2f}/1.0")

    pe = fundamentals.get('pe_ratio')
    if pe:
        print(f"   P/E Ratio: {pe:.2f}")

    analyst_rec = fundamentals.get('recommendation', 'none')
    if analyst_rec and analyst_rec != 'none':
        print(f"   Analyst Consensus: {analyst_rec.upper()}")
    print()

    # News
    print(f"News & Sentiment:")
    print(f"   Articles Found: {news.get('news_count', 0)}")
    print(f"   Sentiment: {news.get('sentiment', 'neutral').upper()}")
    sentiment_score = news.get('sentiment_score', 0.5)
    print(f"   Sentiment Score: {sentiment_score:.1%}")

    news_summary = news.get('summary', '')
    if news_summary and news_summary != 'No recent news available':
        print(f"   Summary: {news_summary[:100]}...")
    print()

    # Market
    print(f"Market Context:")
    print(f"   Overall Market: {market.get('market_trend', 'neutral').upper()}")
    vix = market.get('volatility_index')
    if vix:
        vix_level = 'HIGH' if vix > 25 else 'LOW' if vix < 15 else 'MODERATE'
        print(f"   Market Volatility (VIX): {vix:.1f} ({vix_level})")
    print()

    # Disclaimer
    print(f"{'='*70}")
    print(f"⚠️  IMPORTANT DISCLAIMER")
    print(f"{'='*70}\n")
    print(f"This is NOT financial advice. This analysis is for educational")
    print(f"purposes only. Always do your own research and consult with a")
    print(f"licensed financial advisor before making investment decisions.")
    print(f"Past performance does not guarantee future results.\n")
    print(f"{'='*70}\n")


def main():
    """Main entry point for autonomous analysis."""
    parser = argparse.ArgumentParser(
        description="Autonomous AI Stock Analyzer - Comprehensive analysis without expertise"
    )

    parser.add_argument(
        'ticker',
        help='Stock ticker to analyze (e.g., AAPL, MSFT, GOOGL)'
    )
    parser.add_argument(
        '--period',
        default='6mo',
        help='Analysis period (default: 6mo). Options: 1mo, 3mo, 6mo, 1y, 2y'
    )
    parser.add_argument(
        '--init-kb',
        action='store_true',
        help='Initialize knowledge base before analysis'
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()
        logger.info("✓ Configuration valid\n")

        # Initialize knowledge base if requested
        if args.init_kb:
            logger.info("Initializing knowledge base...")
            initialize_knowledge_base(force_recreate=True)
            logger.info("✓ Knowledge base initialized\n")
        else:
            # Try to load existing
            initialize_knowledge_base(force_recreate=False)

        # Get decision graph
        graph = get_autonomous_decision_graph()

        # Run analysis
        result = graph.run(args.ticker, period=args.period)

        # Print comprehensive summary
        print_decision_summary(result)

        # Auto-track recommendation in database
        try:
            if isinstance(result, dict) and not result.get('error') and result.get('decision'):
                from backtesting.performance import get_performance_tracker
                tracker = get_performance_tracker()
                rec_id = tracker.track_recommendation(args.ticker, result)
                print(f"\n✅ Recommendation tracked (ID: {rec_id})")
                print(f"   Check status: python backtest_cli.py positions")
                print(f"   View performance: python backtest_cli.py performance\n")
            else:
                # Debug: show what we got
                print(f"\n⚠️  Tracking skipped")
                print(f"   Result type: {type(result)}")
                if isinstance(result, dict):
                    print(f"   Has 'decision' key: {'decision' in result}")
                    print(f"   Keys: {list(result.keys())[:5]}")
        except Exception as e:
            logger.error(f"Could not track recommendation: {e}")
            import traceback
            print(f"\n❌ Tracking error: {e}")
            print(traceback.format_exc())

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Analysis interrupted by user.\n")
        return 130

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
