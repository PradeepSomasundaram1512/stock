"""
Main entry point for AI Stock Agent.
"""

import sys
import logging
from pathlib import Path
import argparse

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import validate_config, FINANCIAL_DISCLAIMER, DEFAULT_TICKER, DEFAULT_PERIOD
from rag.ingest import initialize_knowledge_base
from graph.decision_graph import get_decision_graph


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              AI STOCK DECISION AGENT                         ║
║                                                              ║
║  Agentic AI System for Stock Analysis                        ║
║  Using LangChain, LangGraph, RAG & Technical Analysis        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_decision_summary(result: dict):
    """
    Print formatted decision summary.

    Args:
        result: Decision graph result dictionary
    """
    decision = result.get('decision', {})
    features = result.get('features', {})
    ticker = result.get('ticker', 'UNKNOWN')

    print("\n" + "="*70)
    print(f"STOCK ANALYSIS REPORT: {ticker}")
    print("="*70)

    # Stock Information
    print(f"\n📊 STOCK INFORMATION")
    print(f"   Ticker: {ticker}")
    print(f"   Current Price: ${features.get('latest_price', 0):.2f}")
    print(f"   1-Day Change: {features.get('price_change_1d', 0):+.2f}%")
    print(f"   5-Day Change: {features.get('price_change_5d', 0):+.2f}%")
    print(f"   20-Day Change: {features.get('price_change_20d', 0):+.2f}%")

    # Technical Overview
    print(f"\n📈 TECHNICAL OVERVIEW")
    print(f"   Trend: {features.get('trend', 'unknown').upper()}")
    print(f"   Momentum: {features.get('momentum', 'unknown').title()}")
    print(f"   Pattern: {features.get('pattern', 'none').replace('_', ' ').title()}")
    print(f"   Volatility: {features.get('volatility_level', 'unknown').upper()}")

    # Key Indicators
    print(f"\n🔍 KEY INDICATORS")
    print(f"   RSI: {features.get('rsi', 0):.2f} ({features.get('rsi_signal', 'neutral').upper()})")
    print(f"   MACD Signal: {features.get('macd_signal', 'unknown').upper()}")
    print(f"   Volume Confirmation: {'✓' if features.get('volume_confirmation') else '✗'}")
    print(f"   Support Level: ${features.get('support_level', 0):.2f}")
    print(f"   Resistance Level: ${features.get('resistance_level', 0):.2f}")

    # Decision
    decision_text = decision.get('decision', 'HOLD')
    confidence = decision.get('confidence', 0.0)
    sentiment = decision.get('sentiment', 'neutral')

    decision_emoji = {
        'BUY': '🟢',
        'HOLD': '🟡',
        'SELL': '🔴'
    }.get(decision_text, '⚪')

    print(f"\n{decision_emoji} AI DECISION: {decision_text}")
    print(f"   Confidence: {confidence:.1%}")
    print(f"   Sentiment: {sentiment.upper()}")

    # Explanation
    print(f"\n💡 EXPLANATION")
    explanation = decision.get('explanation', 'No explanation provided.')
    # Word wrap the explanation
    words = explanation.split()
    line = "   "
    for word in words:
        if len(line) + len(word) + 1 > 70:
            print(line)
            line = "   " + word
        else:
            line += " " + word if line != "   " else word
    if line.strip():
        print(line)

    # Key Signals
    key_signals = decision.get('key_signals', [])
    if key_signals:
        print(f"\n✅ KEY SUPPORTING SIGNALS")
        for signal in key_signals[:5]:
            print(f"   • {signal}")

    # Risk Factors
    risk_factors = decision.get('risk_factors', [])
    if risk_factors:
        print(f"\n⚠️  RISK FACTORS")
        for risk in risk_factors[:5]:
            print(f"   • {risk}")

    # Supporting/Conflicting Indicators
    supporting = decision.get('supporting_indicators', [])
    if supporting:
        print(f"\n📊 SUPPORTING INDICATORS")
        for ind in supporting[:3]:
            print(f"   • {ind}")

    conflicting = decision.get('conflicting_indicators', [])
    if conflicting:
        print(f"\n⚡ CONFLICTING INDICATORS")
        for ind in conflicting[:3]:
            print(f"   • {ind}")

    # Disclaimer
    print("\n" + "="*70)
    print(FINANCIAL_DISCLAIMER)
    print("="*70 + "\n")


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="AI Stock Decision Agent - Analyze stocks using AI and technical analysis"
    )
    parser.add_argument(
        'ticker',
        nargs='?',
        default=DEFAULT_TICKER,
        help=f'Stock ticker symbol (default: {DEFAULT_TICKER})'
    )
    parser.add_argument(
        '--period',
        default=DEFAULT_PERIOD,
        help='Data period: 1mo, 3mo, 6mo, 1y, 2y (default: 6mo)'
    )
    parser.add_argument(
        '--interval',
        default='1d',
        help='Data interval: 1d, 1wk, 1mo (default: 1d)'
    )
    parser.add_argument(
        '--init-kb',
        action='store_true',
        help='Initialize/recreate knowledge base before analysis'
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
                logger.warning("⚠ Knowledge base initialization had issues, continuing anyway...")
        else:
            # Try to load existing knowledge base
            logger.info("Loading existing knowledge base...")
            success = initialize_knowledge_base(force_recreate=False)
            if not success:
                logger.warning("⚠ Knowledge base not found. Run with --init-kb to create it.")

        # Run analysis
        logger.info(f"Analyzing {args.ticker}...")
        print(f"\n🔄 Analyzing {args.ticker}...\n")

        decision_graph = get_decision_graph()
        result = decision_graph.run(
            ticker=args.ticker,
            period=args.period,
            interval=args.interval
        )

        # Check for errors
        if result.get('error'):
            print(f"\n❌ Error: {result['error']}\n")
            return 1

        # Print results
        print_decision_summary(result)

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
