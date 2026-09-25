"""
Institutional Analysis Agent (FREE VERSION)

AI Agent for institutional-grade stock analysis using FREE data sources:
- Yahoo Finance - Institutional holders, insider trades, short interest
- SEC EDGAR - Direct SEC filings
- Options chain data

NO API KEY REQUIRED!
"""

import logging
from typing import Dict, Any, Optional
from langchain.agents import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from tools.institutional_tool import (
    InstitutionalDataClient,
    get_institutional_analysis,
    get_institutional_score,
    format_institutional_report
)

logger = logging.getLogger(__name__)


class InstitutionalAgent:
    """Agent for analyzing institutional and smart money data using FREE sources."""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.client = InstitutionalDataClient()
        self.llm = llm

        # Analysis prompt template
        self.analysis_prompt = PromptTemplate(
            input_variables=["ticker", "institutional_data", "price_data"],
            template="""
You are an expert institutional analyst. Analyze the following institutional data for {ticker}
and provide actionable insights.

INSTITUTIONAL DATA:
{institutional_data}

CURRENT PRICE DATA:
{price_data}

Based on this institutional data, provide:

1. SMART MONEY SENTIMENT: What are institutions and insiders doing?
2. KEY OBSERVATIONS: Top 3 most important findings
3. RISK FACTORS: Any concerning signals from the data
4. RECOMMENDATION IMPACT: How should this data influence a BUY/HOLD/SELL decision?

Be specific and cite the actual numbers from the data.
"""
        )


    def analyze(self, ticker: str, price_data: Dict = None) -> Dict[str, Any]:
        """
        Perform comprehensive institutional analysis for a stock (FREE).

        Args:
            ticker: Stock symbol
            price_data: Optional current price data for context

        Returns:
            Analysis results including raw data and AI insights
        """
        logger.info(f"Institutional Agent analyzing {ticker} (FREE data)")

        # Get raw institutional data from FREE sources
        institutional_data = self.client.get_comprehensive_analysis(ticker)

        result = {
            'ticker': ticker,
            'raw_data': institutional_data,
            'formatted_report': format_institutional_report(institutional_data),
            'overall_sentiment': institutional_data.get('overall_sentiment', 'NEUTRAL'),
            'signals': institutional_data.get('signals', []),
            'bullish_count': institutional_data.get('bullish_signals', 0),
            'bearish_count': institutional_data.get('bearish_signals', 0),
            'ai_analysis': None,
            'data_source': 'FREE (Yahoo Finance, SEC EDGAR)'
        }

        # If LLM available, get AI analysis
        if self.llm:
            try:
                chain = LLMChain(llm=self.llm, prompt=self.analysis_prompt)
                ai_response = chain.run(
                    ticker=ticker,
                    institutional_data=result['formatted_report'],
                    price_data=str(price_data) if price_data else "Not provided"
                )
                result['ai_analysis'] = ai_response
            except Exception as e:
                logger.error(f"AI analysis failed: {str(e)}")
                result['ai_analysis'] = None

        return result

    def get_quick_summary(self, ticker: str) -> Dict[str, Any]:
        """Get quick institutional summary for market scanner (FREE)."""
        analysis = self.client.get_comprehensive_analysis(ticker)

        return {
            'ticker': ticker,
            'institutional_sentiment': analysis.get('overall_sentiment', 'NEUTRAL'),
            'insider_sentiment': (
                analysis.get('insider_trading', {}).get('insider_sentiment', 'NEUTRAL')
                if analysis.get('insider_trading') else 'N/A'
            ),
            'short_squeeze_potential': (
                analysis.get('short_interest', {}).get('squeeze_potential', 'LOW')
                if analysis.get('short_interest') else 'N/A'
            ),
            'options_sentiment': (
                analysis.get('options_sentiment', {}).get('options_sentiment', 'NEUTRAL')
                if analysis.get('options_sentiment') else 'N/A'
            ),
            'key_signals': analysis.get('signals', [])[:3],
            'bullish_signals': analysis.get('bullish_signals', 0),
            'bearish_signals': analysis.get('bearish_signals', 0),
            'data_source': 'FREE'
        }

    def get_institutional_score(self, ticker: str) -> int:
        """
        Calculate institutional score (-100 to +100) using FREE data.

        Positive = Bullish institutional sentiment
        Negative = Bearish institutional sentiment
        """
        # Use the free scoring function
        return get_institutional_score(ticker)


# =========================================================================
# LANGCHAIN TOOLS (FREE - No API Key Required!)
# =========================================================================

def create_institutional_tools(llm: Optional[ChatOpenAI] = None) -> list:
    """Create LangChain tools for institutional analysis (FREE)."""

    agent = InstitutionalAgent(llm=llm)

    tools = [
        Tool(
            name="institutional_comprehensive_analysis",
            func=lambda ticker: agent.analyze(ticker),
            description=(
                "Get comprehensive institutional analysis including "
                "institutional ownership, insider trading, short interest, "
                "and options flow. FREE - no API key required. Input: stock ticker symbol."
            )
        ),
        Tool(
            name="institutional_quick_summary",
            func=lambda ticker: agent.get_quick_summary(ticker),
            description=(
                "Get quick institutional summary for a stock including sentiment signals "
                "from institutions, insiders, options flow, and short interest. "
                "FREE - no API key required. Input: stock ticker symbol."
            )
        ),
        Tool(
            name="institutional_score",
            func=lambda ticker: agent.get_institutional_score(ticker),
            description=(
                "Calculate institutional sentiment score from -100 (very bearish) to "
                "+100 (very bullish). FREE - no API key required. Input: stock ticker symbol."
            )
        ),
        Tool(
            name="insider_trading",
            func=lambda ticker: agent.client.get_insider_trades(ticker),
            description=(
                "Get recent insider trading activity including buys, "
                "sells, and insider sentiment. FREE. Input: stock ticker symbol."
            )
        ),
        Tool(
            name="short_interest",
            func=lambda ticker: agent.client.get_short_interest(ticker),
            description=(
                "Get short interest data including short % of float, days to cover, "
                "and short squeeze potential. FREE. Input: stock ticker symbol."
            )
        ),
        Tool(
            name="options_sentiment",
            func=lambda ticker: agent.client.get_options_sentiment(ticker),
            description=(
                "Get options sentiment from put/call ratio and volume. "
                "FREE. Input: stock ticker symbol."
            )
        )
    ]

    return tools


# Alias for backwards compatibility
create_fintel_tools = create_institutional_tools


# =========================================================================
# GRAPH NODE FUNCTION
# =========================================================================

def run_institutional_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for institutional analysis (FREE).

    Integrates with the autonomous decision graph.
    """
    ticker = state.get('ticker', '')

    if not ticker:
        state['institutional_analysis'] = {'error': 'No ticker provided'}
        return state

    logger.info(f"Running institutional analysis for {ticker} (FREE)")

    try:
        agent = InstitutionalAgent()
        analysis = agent.analyze(ticker)

        state['institutional_analysis'] = {
            'overall_sentiment': analysis.get('overall_sentiment', 'NEUTRAL'),
            'institutional_score': agent.get_institutional_score(ticker),
            'signals': analysis.get('signals', []),
            'bullish_count': analysis.get('bullish_count', 0),
            'bearish_count': analysis.get('bearish_count', 0),
            'raw_data': analysis.get('raw_data', {}),
            'formatted_report': analysis.get('formatted_report', ''),
            'data_source': 'FREE (Yahoo Finance, SEC EDGAR)'
        }

        # Add to features for decision making
        if 'features' not in state:
            state['features'] = {}

        state['features']['institutional_sentiment'] = analysis.get('overall_sentiment', 'NEUTRAL')
        state['features']['institutional_score'] = agent.get_institutional_score(ticker)
        state['features']['institutional_signals'] = analysis.get('signals', [])

    except Exception as e:
        logger.error(f"Institutional analysis failed: {str(e)}")
        state['institutional_analysis'] = {'error': str(e)}

    return state


# Alias for backwards compatibility
run_fintel_analysis = run_institutional_analysis


# =========================================================================
# CLI TEST
# =========================================================================

if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'

    print(f"\n🔍 Running Institutional Analysis for {ticker} (FREE - No API Key!)...\n")

    agent = InstitutionalAgent()

    # Full analysis
    analysis = agent.analyze(ticker)
    print(analysis['formatted_report'])

    # Institutional score
    score = agent.get_institutional_score(ticker)
    print(f"📊 Institutional Score: {score:+d}/100")

    if score > 30:
        print("   → Strong bullish institutional sentiment")
    elif score > 10:
        print("   → Moderately bullish institutional sentiment")
    elif score < -30:
        print("   → Strong bearish institutional sentiment")
    elif score < -10:
        print("   → Moderately bearish institutional sentiment")
    else:
        print("   → Neutral institutional sentiment")

    # Quick summary
    print("\n📋 Quick Summary:")
    summary = agent.get_quick_summary(ticker)
    for key, value in summary.items():
        if key != 'ticker':
            print(f"   {key}: {value}")

    print("\n✅ All data from FREE sources (Yahoo Finance, SEC EDGAR)")


# Alias for backwards compatibility
FintelAgent = InstitutionalAgent
