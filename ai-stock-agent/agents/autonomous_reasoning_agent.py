"""
Autonomous Reasoning Agent - Makes fully autonomous stock decisions.
Combines technical, fundamental, news, and market context without user input.
"""

import logging
import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
import os

logger = logging.getLogger(__name__)


class AutonomousReasoningAgent:
    """
    Makes autonomous stock decisions based on comprehensive analysis.
    Designed for users with no stock market expertise.
    """

    def __init__(self, model_type: str = "openai", model_name: Optional[str] = None):
        """
        Initialize the Autonomous Reasoning Agent.

        Args:
            model_type: "openai" or "anthropic"
            model_name: Specific model name (optional)
        """
        self.model_type = model_type

        if model_type == "openai":
            self.llm = ChatOpenAI(
                model=model_name or os.getenv("OPENAI_MODEL", "gpt-4o"),
                temperature=0.3,  # Lower temperature for more consistent decisions
                api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            self.llm = ChatAnthropic(
                model=model_name or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                temperature=0.3,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )

        self.decision_prompt = self._create_decision_prompt()

    def _create_decision_prompt(self) -> PromptTemplate:
        """Create the comprehensive decision prompt template."""
        template = """You are an expert stock analyst making autonomous investment decisions.
Your goal is to provide clear, actionable recommendations for investors who may not have deep financial expertise.

## Stock Analysis Data

**Ticker:** {ticker}
**Company:** {company_name}
**Sector:** {sector} | **Industry:** {industry}

---

### 1. TECHNICAL ANALYSIS
**Price:** ${current_price:.2f}
**20-Day Change:** {price_change_20d:+.2f}%
**Trend:** {trend}
**RSI:** {rsi:.1f} ({rsi_signal})
**MACD:** {macd_signal}
**Volume:** {volume_signal}
**Volatility:** {volatility_level} ({volatility:.1f}%)
**Support/Resistance:** {support_resistance}

**Technical Summary:**
{technical_summary}

---

### 2. FUNDAMENTAL ANALYSIS
**Valuation:**
- P/E Ratio: {pe_ratio}
- Price/Book: {price_to_book}
- Price/Sales: {price_to_sales}
- **Valuation Score:** {valuation_score}/1.0

**Financial Health:**
- Profit Margin: {profit_margin}
- Return on Equity: {return_on_equity}
- Current Ratio: {current_ratio}
- Debt/Equity: {debt_to_equity}
- **Health Score:** {health_score}/1.0

**Growth:**
- Revenue Growth: {revenue_growth}
- Earnings Growth: {earnings_growth}
- **Growth Score:** {growth_score}/1.0

**Analyst Consensus:**
- Recommendation: {analyst_recommendation}
- Target Price: ${analyst_target_price}
- Number of Analysts: {analyst_count}

---

### 3. NEWS & SENTIMENT
**Recent News Count:** {news_count}
**Sentiment:** {news_sentiment} ({news_sentiment_score:.1%})
**Key Topics:** {news_topics}

**News Summary:**
{news_summary}

---

### 4. MARKET CONTEXT
**Overall Market:** {market_trend} (Strength: {market_strength:.1%})
**Market Volatility (VIX):** {market_vix}
**Sector Performance:** {sector_performance}

**Major Indices (30-day):**
{indices_performance}

---

## Your Task

Based on ALL the above data (technical, fundamental, news, market context), make an **autonomous decision**.

**Decision Criteria:**
- **BUY:** Strong bullish signals across multiple dimensions. Good value, positive momentum, favorable news.
- **SELL:** Strong bearish signals. Overvalued, negative momentum, concerning news.
- **HOLD:** Mixed signals, uncertainty, or waiting for better entry/exit point.

**Important Guidelines:**
1. Consider the WHOLE picture - don't rely on just one factor
2. Fundamentals matter for long-term value
3. Technical indicators show short-term momentum
4. News/sentiment can be early warning signals
5. Market context affects all stocks
6. Be decisive - this is for users who need clear guidance
7. High confidence (>75%) means very strong signals across board
8. Low confidence (<50%) means conflicting signals or uncertainty

**Return ONLY valid JSON in this exact format:**
{{
    "decision": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "2-3 sentence explanation in simple terms",
    "key_factors": ["factor1", "factor2", "factor3"],
    "risk_level": "low" | "medium" | "high",
    "time_horizon": "short-term (days-weeks)" | "medium-term (weeks-months)" | "long-term (months+)",
    "price_target": estimated fair value or target price,
    "stop_loss": suggested stop loss price (if BUY),
    "alternative_action": "What to do if decision doesn't work out"
}}

**Make your decision now:**"""

        return PromptTemplate(
            template=template,
            input_variables=[
                "ticker", "company_name", "sector", "industry",
                "current_price", "price_change_20d", "trend", "rsi", "rsi_signal",
                "macd_signal", "volume_signal", "volatility_level", "volatility",
                "support_resistance", "technical_summary",
                "pe_ratio", "price_to_book", "price_to_sales", "valuation_score",
                "profit_margin", "return_on_equity", "current_ratio", "debt_to_equity", "health_score",
                "revenue_growth", "earnings_growth", "growth_score",
                "analyst_recommendation", "analyst_target_price", "analyst_count",
                "news_count", "news_sentiment", "news_sentiment_score", "news_topics", "news_summary",
                "market_trend", "market_strength", "market_vix", "sector_performance",
                "indices_performance"
            ]
        )

    def analyze(
        self,
        ticker: str,
        technical_data: Dict[str, Any],
        fundamental_data: Dict[str, Any],
        news_data: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make autonomous decision based on all available data.

        Args:
            ticker: Stock ticker
            technical_data: Technical analysis results
            fundamental_data: Fundamental analysis results
            news_data: News and sentiment analysis
            market_context: Market context data

        Returns:
            Complete decision with reasoning
        """
        try:
            # Prepare all input variables
            inputs = self._prepare_inputs(
                ticker, technical_data, fundamental_data, news_data, market_context
            )

            # Format the prompt
            prompt_text = self.decision_prompt.format(**inputs)

            # Get LLM decision
            response = self.llm.invoke([HumanMessage(content=prompt_text)])

            # Parse JSON response
            decision_data = self._parse_response(response.content)

            # Validate and ensure consistency
            decision_data = self._validate_decision(decision_data, inputs)

            logger.info(f"Autonomous decision for {ticker}: {decision_data['decision']} "
                       f"({decision_data['confidence']:.1%} confidence)")

            return decision_data

        except Exception as e:
            logger.error(f"Error in autonomous analysis: {str(e)}", exc_info=True)
            return {
                'decision': 'HOLD',
                'confidence': 0.5,
                'reasoning': f'Unable to make decision due to analysis error: {str(e)}',
                'key_factors': ['error in analysis'],
                'risk_level': 'high',
                'time_horizon': 'unknown',
                'price_target': None,
                'stop_loss': None,
                'alternative_action': 'Wait for system resolution'
            }

    def _prepare_inputs(
        self,
        ticker: str,
        technical: Dict[str, Any],
        fundamental: Dict[str, Any],
        news: Dict[str, Any],
        market: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare all input variables for the prompt."""

        # Helper to format None values
        def fmt(value, format_str=".2f", default="N/A"):
            if value is None or (isinstance(value, float) and value == 0):
                return default
            if isinstance(value, float):
                return f"{value:{format_str}}"
            return str(value)

        # Technical data
        features = technical.get('features', {})

        # Fundamental data
        company_name = fundamental.get('company_name', ticker)
        sector = fundamental.get('sector', 'Unknown')
        industry = fundamental.get('industry', 'Unknown')

        # Market data
        indices = market.get('indices', {})
        indices_text = "\n".join([
            f"  - {name}: {data.get('month_change', 0):+.2f}% ({data.get('trend', 'unknown')})"
            for name, data in indices.items()
            if 'month_change' in data
        ]) or "  - No data available"

        return {
            # Basic info
            "ticker": ticker,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,

            # Technical
            "current_price": features.get('latest_price', 0),
            "price_change_20d": features.get('price_change_20d', 0),
            "trend": features.get('trend', 'neutral'),
            "rsi": features.get('rsi', 50),
            "rsi_signal": features.get('rsi_signal', 'neutral'),
            "macd_signal": features.get('macd_signal', 'neutral'),
            "volume_signal": features.get('volume_signal', 'normal'),
            "volatility_level": features.get('volatility_level', 'unknown'),
            "volatility": features.get('volatility', 0) * 100,
            "support_resistance": features.get('support_resistance', 'N/A'),
            "technical_summary": features.get('summary', 'No technical summary available'),

            # Fundamental
            "pe_ratio": fmt(fundamental.get('pe_ratio')),
            "price_to_book": fmt(fundamental.get('price_to_book')),
            "price_to_sales": fmt(fundamental.get('price_to_sales')),
            "valuation_score": fmt(fundamental.get('valuation_score', 0.5)),
            "profit_margin": fmt(fundamental.get('profit_margin'), ".1%"),
            "return_on_equity": fmt(fundamental.get('return_on_equity'), ".1%"),
            "current_ratio": fmt(fundamental.get('current_ratio')),
            "debt_to_equity": fmt(fundamental.get('debt_to_equity')),
            "health_score": fmt(fundamental.get('health_score', 0.5)),
            "revenue_growth": fmt(fundamental.get('revenue_growth'), "+.1%"),
            "earnings_growth": fmt(fundamental.get('earnings_growth'), "+.1%"),
            "growth_score": fmt(fundamental.get('growth_score', 0.5)),
            "analyst_recommendation": (fundamental.get('recommendation') or 'none').upper(),
            "analyst_target_price": fmt(fundamental.get('target_mean_price'), default="N/A"),
            "analyst_count": fundamental.get('number_of_analyst_opinions', 0),

            # News
            "news_count": news.get('news_count', 0),
            "news_sentiment": (news.get('sentiment') or 'neutral').upper(),
            "news_sentiment_score": news.get('sentiment_score', 0.5),
            "news_topics": ", ".join(news.get('key_topics', [])) or "None",
            "news_summary": news.get('summary', 'No recent news available'),

            # Market context
            "market_trend": (market.get('market_trend') or 'neutral').upper(),
            "market_strength": market.get('market_strength', 0.5),
            "market_vix": fmt(market.get('volatility_index'), default="N/A"),
            "sector_performance": "N/A",  # Will be enhanced if sector data available
            "indices_performance": indices_text
        }

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM JSON response."""
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # Parse JSON
            data = json.loads(cleaned)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
            raise

    def _validate_decision(self, decision: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize decision data."""

        # Ensure decision is valid
        if decision.get('decision') not in ['BUY', 'SELL', 'HOLD']:
            decision['decision'] = 'HOLD'

        # Ensure confidence is in range
        confidence = decision.get('confidence', 0.5)
        decision['confidence'] = max(0.0, min(1.0, float(confidence)))

        # Ensure required fields exist
        decision.setdefault('reasoning', 'Decision based on comprehensive analysis')
        decision.setdefault('key_factors', [])
        decision.setdefault('risk_level', 'medium')
        decision.setdefault('time_horizon', 'medium-term')
        decision.setdefault('price_target', None)
        decision.setdefault('stop_loss', None)
        decision.setdefault('alternative_action', 'Monitor and reassess')

        return decision


# Singleton instance
_autonomous_reasoning_agent_instance = None


def get_autonomous_reasoning_agent() -> AutonomousReasoningAgent:
    """Get or create the AutonomousReasoningAgent singleton."""
    global _autonomous_reasoning_agent_instance
    if _autonomous_reasoning_agent_instance is None:
        _autonomous_reasoning_agent_instance = AutonomousReasoningAgent()
    return _autonomous_reasoning_agent_instance
