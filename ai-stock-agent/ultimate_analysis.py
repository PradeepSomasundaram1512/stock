#!/usr/bin/env python3
"""
🚀 ULTIMATE STOCK ANALYZER 🚀

The most comprehensive, advanced stock analysis tool.
Combines ALL advanced techniques in ONE simple command.

Features:
- ✅ Technical Analysis (RSI, MACD, Bollinger Bands, Volume, Support/Resistance)
- ✅ Fundamental Analysis (P/E, Market Cap, Revenue Growth, Analyst Ratings)
- ✅ News Sentiment (3 premium APIs: NewsAPI, Finnhub, Alpha Vantage)
- ✅ Market Context (VIX, S&P 500, Sector Performance)
- ✅ ML Price Prediction (LSTM + XGBoost ensemble)
- ✅ RAG Knowledge Base (Custom trading strategies)
- ✅ Multi-Agent AI Reasoning
- ✅ Risk Assessment
- ✅ Position Tracking

Usage:
    python ultimate_analysis.py AAPL
    python ultimate_analysis.py NVDA --period 1y
    python ultimate_analysis.py TSLA --ml-predict
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import all the best components
from app.config import validate_config
from rag.ingest import initialize_knowledge_base
from graph.autonomous_decision_graph import get_autonomous_decision_graph
from ml.price_predictor import get_ml_predictor
from backtesting.performance import get_performance_tracker


def print_banner():
    """Print the ultimate banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                   �� ULTIMATE STOCK ANALYZER 🚀                      ║
║                                                                      ║
║              The Most Advanced AI Stock Analysis Tool               ║
║                                                                      ║
║  ✓ Technical Analysis      ✓ Fundamental Analysis                   ║
║  ✓ News Sentiment (3 APIs) ✓ Market Context                         ║
║  ✓ ML Price Prediction     ✓ RAG Knowledge Base                     ║
║  ✓ Multi-Agent AI          ✓ Risk Assessment                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_ml_prediction(ml_result: Dict[str, Any], current_price: float):
    """Print ML price prediction beautifully."""
    print(f"\n{'='*70}")
    print("🤖 MACHINE LEARNING PRICE PREDICTION")
    print(f"{'='*70}\n")

    predicted_price = ml_result.get('predicted_price', current_price)
    change_pct = ml_result.get('predicted_change_pct', 0)
    confidence = ml_result.get('confidence', 0)
    forecast_days = ml_result.get('forecast_days', 5)
    models_used = [m for m in ml_result.get('models_used', []) if m]

    # Prediction direction
    direction = "📈 UPWARD" if change_pct > 0 else "📉 DOWNWARD" if change_pct < 0 else "➡️ FLAT"

    print(f"Forecast Period: {forecast_days} days")
    print(f"Models Used: {', '.join(models_used) if models_used else 'None trained yet'}\n")

    print(f"Current Price:    ${current_price:.2f}")
    print(f"Predicted Price:  ${predicted_price:.2f}")
    print(f"Expected Change:  {change_pct:+.2f}%")
    print(f"Direction:        {direction}")
    print(f"ML Confidence:    {confidence*100:.0f}%\n")

    if change_pct > 5:
        print("💡 Strong upside potential detected by ML models")
    elif change_pct < -5:
        print("⚠️  Strong downside risk detected by ML models")
    else:
        print("💭 ML models predict relatively stable price action")

    if models_used:
        print(f"\n📊 Individual Model Predictions:")
        if 'lstm_prediction' in ml_result and ml_result['lstm_prediction']:
            print(f"   LSTM:    ${ml_result['lstm_prediction']:.2f}")
        if 'xgb_prediction' in ml_result and ml_result['xgb_prediction']:
            print(f"   XGBoost: ${ml_result['xgb_prediction']:.2f}")
    else:
        print("\n💡 Tip: ML models improve with more data. Run analysis multiple times to train models.")


def print_comprehensive_report(result: Dict[str, Any], ml_result: Optional[Dict[str, Any]] = None):
    """Print the ultimate comprehensive report."""

    if result.get('error'):
        print(f"\n❌ Error: {result['error']}\n")
        return

    ticker = result.get('ticker', 'UNKNOWN')
    decision_data = result.get('decision', {})
    features = result.get('features', {})
    fundamentals = result.get('fundamentals', {})
    news = result.get('news_analysis', {})
    market = result.get('market_context', {})

    # ========== HEADER ==========
    print(f"\n{'='*70}")
    print(f"📊 ULTIMATE ANALYSIS REPORT: {ticker}")
    print(f"{'='*70}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ========== COMPANY INFO ==========
    company = fundamentals.get('company_name', ticker)
    sector = fundamentals.get('sector', 'Unknown')
    industry = fundamentals.get('industry', 'Unknown')

    print(f"🏢 {company}")
    print(f"   Sector: {sector} | Industry: {industry}\n")

    # ========== CURRENT PRICE ==========
    price = features.get('latest_price', 0)
    change_1d = features.get('price_change_1d', 0)
    change_5d = features.get('price_change_5d', 0)
    change_20d = features.get('price_change_20d', 0)

    symbol_1d = '📈' if change_1d >= 0 else '📉'
    symbol_5d = '📈' if change_5d >= 0 else '📉'
    symbol_20d = '📈' if change_20d >= 0 else '📉'

    print(f"💰 Current Price: ${price:.2f}")
    print(f"   {symbol_1d} 1-Day:   {change_1d:+.2f}%")
    print(f"   {symbol_5d} 5-Day:   {change_5d:+.2f}%")
    print(f"   {symbol_20d} 20-Day:  {change_20d:+.2f}%\n")

    # ========== THE ULTIMATE DECISION ==========
    print(f"{'='*70}")
    print(f"🎯 AI RECOMMENDATION")
    print(f"{'='*70}\n")

    decision = decision_data.get('decision', 'HOLD')
    confidence = decision_data.get('confidence', 0) * 100
    risk_level = decision_data.get('risk_level', 'MEDIUM').upper()
    time_horizon = decision_data.get('time_horizon', 'medium-term')

    # Decision emoji
    decision_emoji = {
        'BUY': '🟢',
        'HOLD': '🟡',
        'SELL': '🔴'
    }.get(decision, '🟡')

    print(f"{decision_emoji} {decision}")
    print(f"   Confidence: {confidence:.0f}%")
    print(f"   Risk Level: {risk_level}")
    print(f"   Time Horizon: {time_horizon}\n")

    # Explanation
    explanation = decision_data.get('explanation', 'No explanation provided')
    print(f"📝 Why This Decision?")
    print(f"   {explanation}\n")

    # Key factors
    key_factors = decision_data.get('key_factors', [])
    if key_factors:
        print(f"🔑 Key Factors:")
        for factor in key_factors[:5]:
            print(f"   • {factor}")
        print()

    # Price target
    price_target = decision_data.get('price_target')
    if price_target and price_target > 0:
        potential = ((price_target - price) / price) * 100
        target_symbol = '📈' if potential >= 0 else '📉'
        print(f"🎯 Price Target: ${price_target:.2f}")
        print(f"   Potential: {target_symbol} {potential:+.1f}%\n")

    # Alternative plan
    alternative = decision_data.get('alternative_plan', '')
    if alternative:
        print(f"🔄 If This Doesn't Work Out:")
        print(f"   {alternative}\n")

    # ========== ML PREDICTION (if available) ==========
    if ml_result and ml_result.get('models_used'):
        print_ml_prediction(ml_result, price)

    # ========== TECHNICAL ANALYSIS ==========
    print(f"\n{'='*70}")
    print("📈 TECHNICAL ANALYSIS")
    print(f"{'='*70}\n")

    trend = features.get('trend', 'NEUTRAL')
    momentum = features.get('momentum', 'neutral')
    volatility = features.get('volatility_level', 'UNKNOWN')
    rsi = features.get('rsi', 0)
    rsi_signal = features.get('rsi_signal', 'NEUTRAL')
    macd_signal = features.get('macd_signal', 'UNKNOWN')
    volume_conf = '✓' if features.get('volume_confirmation') else '✗'
    support = features.get('support_level', 0)
    resistance = features.get('resistance_level', 0)

    print(f"Trend:               {trend}")
    print(f"Momentum:            {momentum}")
    print(f"Volatility:          {volatility}")
    print(f"RSI:                 {rsi:.1f} ({rsi_signal})")
    print(f"MACD Signal:         {macd_signal}")
    print(f"Volume Confirmation: {volume_conf}")
    print(f"Support Level:       ${support:.2f}")
    print(f"Resistance Level:    ${resistance:.2f}")

    # ========== FUNDAMENTAL ANALYSIS ==========
    print(f"\n{'='*70}")
    print("💼 FUNDAMENTAL ANALYSIS")
    print(f"{'='*70}\n")

    pe_ratio = fundamentals.get('pe_ratio', 0)
    market_cap = fundamentals.get('market_cap', 0)
    revenue_growth = fundamentals.get('revenue_growth', 0)
    profit_margin = fundamentals.get('profit_margin', 0)
    analyst_rec = fundamentals.get('recommendation', 'N/A')

    # Calculate scores
    valuation_score = fundamentals.get('valuation_score', 0)
    health_score = fundamentals.get('health_score', 0)
    growth_score = fundamentals.get('growth_score', 0)

    print(f"P/E Ratio:           {pe_ratio:.2f}" if pe_ratio else "P/E Ratio:           N/A")
    print(f"Market Cap:          ${market_cap/1e9:.2f}B" if market_cap else "Market Cap:          N/A")
    print(f"Revenue Growth:      {revenue_growth*100:.1f}%" if revenue_growth else "Revenue Growth:      N/A")
    print(f"Profit Margin:       {profit_margin*100:.1f}%" if profit_margin else "Profit Margin:       N/A")
    print(f"Analyst Consensus:   {analyst_rec}")

    if valuation_score or health_score or growth_score:
        print(f"\nFundamental Scores (0-1):")
        if valuation_score: print(f"   Valuation: {valuation_score:.2f}/1.0")
        if health_score: print(f"   Health:    {health_score:.2f}/1.0")
        if growth_score: print(f"   Growth:    {growth_score:.2f}/1.0")

    # ========== NEWS SENTIMENT ==========
    print(f"\n{'='*70}")
    print("📰 NEWS & SENTIMENT ANALYSIS")
    print(f"{'='*70}\n")

    news_count = news.get('news_count', 0)
    sentiment = news.get('sentiment', 'NEUTRAL')
    sentiment_score = news.get('sentiment_score', 0.5) * 100
    news_summary = news.get('summary', 'No recent news available')
    data_sources = news.get('data_sources', [])

    sentiment_emoji = {
        'bullish': '📈',
        'neutral': '➡️',
        'bearish': '📉'
    }.get(sentiment.lower(), '➡️')

    print(f"Articles Analyzed:   {news_count}")
    print(f"Sentiment:           {sentiment_emoji} {sentiment.upper()}")
    print(f"Sentiment Score:     {sentiment_score:.1f}%")
    print(f"Data Sources:        {', '.join(data_sources) if data_sources else 'Web Scraping'}")
    print(f"\nSummary:")
    print(f"   {news_summary[:200]}{'...' if len(news_summary) > 200 else ''}")

    # ========== MARKET CONTEXT ==========
    print(f"\n{'='*70}")
    print("🌍 MARKET CONTEXT")
    print(f"{'='*70}\n")

    market_sentiment = market.get('overall_market', 'NEUTRAL')
    vix = market.get('vix', 0)
    vix_level = market.get('vix_level', 'MODERATE')
    spy_trend = market.get('spy_trend', 'NEUTRAL')
    sector_perf = market.get('sector_performance', 'N/A')

    print(f"Overall Market:      {market_sentiment}")
    print(f"VIX (Fear Index):    {vix:.1f} ({vix_level})")
    print(f"S&P 500 Trend:       {spy_trend}")
    print(f"Sector Performance:  {sector_perf}")

    # ========== RISK ASSESSMENT ==========
    print(f"\n{'='*70}")
    print("⚠️  RISK FACTORS")
    print(f"{'='*70}\n")

    risk_factors = decision_data.get('risk_factors', [])
    if risk_factors:
        for risk in risk_factors[:5]:
            print(f"   • {risk}")
    else:
        print("   No significant risks identified")

    # ========== FOOTER ==========
    print(f"\n{'='*70}")
    print("⚠️  IMPORTANT DISCLAIMER")
    print(f"{'='*70}\n")
    print("This is NOT financial advice. This analysis is for educational")
    print("purposes only. Always do your own research and consult with a")
    print("licensed financial advisor before making investment decisions.")
    print("Past performance does not guarantee future results.\n")
    print(f"{'='*70}\n")


def run_ml_prediction(ticker: str, stock_data, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run ML price prediction if requested."""
    try:
        logger.info("Running ML price prediction...")

        predictor = get_ml_predictor(ticker)

        # Train models if not already trained
        if not predictor.lstm_model and not predictor.xgb_model:
            logger.info("Training ML models (first-time setup)...")
            predictor.train_lstm(stock_data, features, forecast_days=5)
            predictor.train_xgboost(stock_data, features, forecast_days=5)
            predictor.save_models(ticker)

        # Make prediction
        ml_result = predictor.predict(stock_data, features, forecast_days=5)

        logger.info("✓ ML prediction completed")
        return ml_result

    except Exception as e:
        logger.warning(f"ML prediction failed: {str(e)}")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='🚀 Ultimate Stock Analyzer - The most comprehensive analysis tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ultimate_analysis.py AAPL
  python ultimate_analysis.py NVDA --period 1y
  python ultimate_analysis.py TSLA --ml-predict
  python ultimate_analysis.py MSFT --period 6mo --ml-predict

For help: python ultimate_analysis.py --help
        """
    )

    parser.add_argument('ticker', help='Stock ticker symbol (e.g., AAPL, NVDA, TSLA)')
    parser.add_argument('--period', default='6mo', help='Time period (1mo, 3mo, 6mo, 1y, 2y, 5y)')
    parser.add_argument('--ml-predict', action='store_true', help='Include ML price prediction')
    parser.add_argument('--init-kb', action='store_true', help='Re-initialize knowledge base')
    parser.add_argument('--no-track', action='store_true', help='Don\'t save to database')

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Validate configuration
    logger.info("Validating configuration...")
    if not validate_config():
        logger.error("Configuration validation failed")
        return 1
    logger.info("✓ Configuration valid")

    # Initialize knowledge base
    if args.init_kb:
        logger.info("Initializing knowledge base...")
        initialize_knowledge_base()
    else:
        logger.info("Loading existing knowledge base...")
        initialize_knowledge_base()

    # Run the ultimate analysis
    ticker = args.ticker.upper()
    logger.info(f"Starting ultimate analysis for {ticker}...")

    print(f"\n🔄 Analyzing {ticker}...")
    print("   This may take 30-60 seconds for complete analysis...\n")

    try:
        # Get autonomous decision graph
        decision_graph = get_autonomous_decision_graph()

        # Run analysis
        result = decision_graph.graph.invoke({
            'ticker': ticker,
            'period': args.period,
            'interval': '1d'
        })

        # Run ML prediction if requested
        ml_result = None
        if args.ml_predict and result.get('stock_data') is not None:
            ml_result = run_ml_prediction(
                ticker,
                result.get('stock_data'),
                result.get('features', {})
            )

        # Print comprehensive report
        print_comprehensive_report(result, ml_result)

        # Track recommendation in database
        if not args.no_track and result.get('decision'):
            try:
                tracker = get_performance_tracker()
                recommendation_id = tracker.save_recommendation(
                    ticker=ticker,
                    decision=result['decision']['decision'],
                    confidence=result['decision']['confidence'],
                    entry_price=result['features']['latest_price'],
                    reasoning=result['decision'].get('explanation', ''),
                    metadata={
                        'period': args.period,
                        'ml_prediction': ml_result if ml_result else None
                    }
                )

                print("✅ Recommendation tracked (ID: {})".format(recommendation_id))
                print("   View positions: python backtest_cli.py positions")
                print("   View performance: python backtest_cli.py performance\n")

            except Exception as e:
                logger.warning(f"Failed to track recommendation: {str(e)}")

        logger.info("✓ Ultimate analysis completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        print(f"\n❌ Analysis failed: {str(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
