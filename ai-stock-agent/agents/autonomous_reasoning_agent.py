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
import time

logger = logging.getLogger(__name__)


class AutonomousReasoningAgent:
    """
    Makes autonomous stock decisions based on comprehensive analysis.
    Designed for users with no stock market expertise.
    """

    def __init__(self, model_type: str = "openai", model_name: Optional[str] = None, swing_mode: bool = False):
        """
        Initialize the Autonomous Reasoning Agent.

        Args:
            model_type: "openai" or "anthropic"
            model_name: Specific model name (optional)
            swing_mode: If True, use weekly swing trading prompt (5-10 day holds, 8-15% targets)
        """
        self.model_type = model_type
        self.swing_mode = swing_mode

        if model_type == "openai":
            self.llm = ChatOpenAI(
                model=model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.3,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        else:
            self.llm = ChatAnthropic(
                model=model_name or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                temperature=0.3,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )

        self.decision_prompt = self._create_swing_prompt() if swing_mode else self._create_decision_prompt()

    def _create_decision_prompt(self) -> PromptTemplate:
        """Create the comprehensive decision prompt template."""
        template = """You are an expert day trader helping a complete beginner make a trade for TODAY ONLY.
This position opens after 9:30 AM and closes before 4:00 PM ET the same day. Think intraday, not long-term.

## Stock Data for TODAY's Trade

**Ticker:** {ticker}
**Company:** {company_name}
**Sector:** {sector} | **Industry:** {industry}

---

### 1. INTRADAY TECHNICAL ANALYSIS (most important — this drives the day trade)
**Current Price:** ${current_price:.2f}
**Recent Change:** {price_change_20d:+.2f}% (recent bars)
**Trend (intraday):** {trend}
**RSI (14-period, hourly):** {rsi:.1f} ({rsi_signal})
  → Under 30 = oversold (potential bounce BUY), Over 70 = overbought (potential SELL)
**MACD:** {macd_signal}
**Volume:** {volume_signal}
  → High volume confirms the move; low volume = weak signal
**ATR (Average True Range, hourly):** {atr_value:.2f}
  → This is the typical hourly price swing. Stop = 1.5× ATR below entry. Target = 3× ATR above entry.
**Volatility:** {volatility_level} ({volatility:.1f}%)
**Key Levels:** {support_resistance}

**Technical Summary:**
{technical_summary}

---

### 2. FUNDAMENTAL SNAPSHOT (secondary for a day trade)
- P/E: {pe_ratio} | Health Score: {health_score}/1.0
- Analyst target: ${analyst_target_price} ({analyst_count} analysts)
- Revenue growth: {revenue_growth} | Earnings growth: {earnings_growth}

---

### 3. NEWS TODAY
**Sentiment:** {news_sentiment} ({news_sentiment_score:.1%}) | {news_count} recent articles
**Key Topics:** {news_topics}
**Summary:** {news_summary}

---

### 4. MARKET CONDITIONS RIGHT NOW
**Overall Market:** {market_trend} (Strength: {market_strength:.1%})
**VIX (Fear Index):** {market_vix}
  → VIX > 25 = high fear, be cautious. VIX < 15 = calm, good for trading.
**Indices (recent):**
{indices_performance}
**Sector Performance Today ({sector} sector):** {sector_performance}
  → If the whole sector is down, an oversold stock in that sector is even more attractive for a bounce.

---

## YOUR TASK: Make a DAY TRADE decision

**Rules:**
1. TECHNICAL momentum is the #1 factor for a day trade. Fundamentals are secondary.
2. BUY only if: RSI is not overbought (<70), price is trending up or showing reversal signs.
3. SELL/AVOID if: RSI overbought (>70), downtrend, or volume drying up.
4. HOLD = skip this stock today. Still provide price_target and stop_loss as a watch level for the next scan.
5. stop_loss MUST be 1.0–2.0 × ATR below entry (never more than 3% away).
6. price_target MUST be 2–3 × ATR above entry (at least 2:1 reward-to-risk).
7. If earnings are within 5 days, set risk_level="high" and warn in reasoning.
8. Write reasoning in plain English — pretend you're explaining to a friend with no finance knowledge.
9. time_horizon is ALWAYS "intraday (today only)".
10. Be decisive. HOLD is only acceptable when signals genuinely conflict.
11. MARKET TREND RULE — CRITICAL: If the overall market (SPY/QQQ) is UP more than +0.3% today, do NOT issue a SELL decision unless ALL of these are true: RSI > 85 AND the stock's own sector is DOWN today AND volume is below average. An overbought RSI alone is NOT enough to sell in a bull market — overbought stocks stay overbought all day when the market is rising. When in doubt on a bull day: HOLD instead of SELL.
12. Similarly, if the market is DOWN more than -0.3% today, do NOT issue a BUY unless RSI < 25 AND the sector is showing relative strength (less negative than the market).

**Confidence calibration (use these guidelines, do not always return 0.7):**
- 0.85–1.00: Very strong — RSI < 20 AND volume spike AND trend confirms the move
- 0.70–0.84: Clear signal — RSI < 30 OR RSI > 70 AND trend confirms
- 0.55–0.69: Moderate — RSI is extreme but trend is mixed or volume is low
- 0.40–0.54: Weak — conflicting indicators, safer to HOLD

**Return ONLY valid JSON:**
{{
    "decision": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "2-3 sentences in plain English explaining why, what could go wrong",
    "key_factors": ["factor1", "factor2", "factor3"],
    "risk_level": "low" | "medium" | "high",
    "time_horizon": "intraday (today only)",
    "price_target": price the stock could reach by close today (number),
    "stop_loss": exit immediately if price hits this (1-2x ATR below entry),
    "atr_value": the ATR value you used,
    "days_to_earnings": number of days until next earnings (integer, or null if unknown),
    "alternative_action": "If the trade goes against you, do this"
}}

**Your day-trade decision:**"""

        return PromptTemplate(
            template=template,
            input_variables=[
                "ticker", "company_name", "sector", "industry",
                "current_price", "price_change_20d", "trend", "rsi", "rsi_signal",
                "macd_signal", "volume_signal", "volatility_level", "volatility",
                "support_resistance", "technical_summary", "atr_value",
                "pe_ratio", "price_to_book", "price_to_sales", "valuation_score",
                "profit_margin", "return_on_equity", "current_ratio", "debt_to_equity", "health_score",
                "revenue_growth", "earnings_growth", "growth_score",
                "analyst_recommendation", "analyst_target_price", "analyst_count",
                "news_count", "news_sentiment", "news_sentiment_score", "news_topics", "news_summary",
                "market_trend", "market_strength", "market_vix", "sector_performance", "sector",
                "indices_performance"
            ]
        )

    def _create_swing_prompt(self) -> PromptTemplate:
        """Create prompt for weekly swing trading (hold 5-10 days, target 8-15% moves)."""
        template = """You are an expert swing trader helping a beginner find a trade to hold for 5-10 days.
This is NOT a day trade. The position opens today and targets an 8-15% move over the next 1-2 weeks.

## Stock Data for SWING TRADE Analysis

**Ticker:** {ticker}
**Company:** {company_name}
**Sector:** {sector} | **Industry:** {industry}

---

### 1. DAILY CHART TECHNICAL ANALYSIS (drives the swing setup)
**Current Price:** ${current_price:.2f}
**Recent 20-Day Change:** {price_change_20d:+.2f}%
**Trend (daily):** {trend}
**RSI (14-period, daily):** {rsi:.1f} ({rsi_signal})
  → Under 40 = oversold setup (swing BUY), Over 60 = overbought setup (swing SELL)
**MACD:** {macd_signal}
**Volume:** {volume_signal}
  → Rising volume on up-days confirms bullish swing. Shrinking volume on pullback = good entry.
**Daily ATR:** {atr_value:.2f}
  → Swing target = 5–8× daily ATR above entry. Stop = 2–3× daily ATR below entry.
**Volatility:** {volatility_level} ({volatility:.1f}% daily)
**Key Levels:** {support_resistance}

**Technical Summary:**
{technical_summary}

---

### 2. FUNDAMENTALS (important for swing — avoid weak companies)
- P/E: {pe_ratio} | Health Score: {health_score}/1.0
- Analyst target: ${analyst_target_price} ({analyst_count} analysts) → {analyst_recommendation}
- Revenue growth: {revenue_growth} | Earnings growth: {earnings_growth}

---

### 3. NEWS & CATALYST (can spark the multi-day move)
**Sentiment:** {news_sentiment} ({news_sentiment_score:.1%}) | {news_count} recent articles
**Key Topics:** {news_topics}
**Summary:** {news_summary}

---

### 4. MARKET CONDITIONS
**Overall Market:** {market_trend} (Strength: {market_strength:.1%})
**VIX:** {market_vix}
  → VIX > 30 = avoid swing trades. VIX 15-25 = ideal. VIX < 15 = low volatility (smaller moves).
**Indices:**
{indices_performance}
**Sector ({sector}):** {sector_performance}

---

## YOUR TASK: Make a SWING TRADE decision (5-10 day hold)

**Rules:**
1. BUY only if: Daily RSI < 50 (not overbought), stock has a clear uptrend or bounce setup, fundamentals are decent (health_score > 0.4).
2. SELL (short setup) only if: Daily RSI > 60, clear downtrend, fundamentals weakening.
3. HOLD = skip. Use when trend is unclear or both bull/bear cases are equally valid.
4. stop_loss MUST be 2–3× daily ATR below entry (typically 3-5% away). Never more than 6% below entry.
5. price_target MUST be 5–8× daily ATR above entry (typically 8-15% above entry). Minimum 2:1 reward-to-risk.
6. time_horizon is ALWAYS "swing (5-10 days)".
7. If earnings are within 7 days, set risk_level="high" — earnings can gap against the trade.
8. Consider the analyst target price — if current price is already near/above analyst target, avoid BUY.
9. Write reasoning in plain English — 2-3 sentences covering the setup, catalyst, and main risk.

**Confidence calibration:**
- 0.80–1.00: Strong setup — oversold daily RSI + uptrend resumption + positive news catalyst
- 0.65–0.79: Good setup — RSI oversold OR strong trend, clear support level
- 0.50–0.64: Marginal — mixed signals, no strong catalyst
- Below 0.50: HOLD — too many conflicting signals for a multi-day hold

**Return ONLY valid JSON:**
{{
    "decision": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "2-3 sentences: setup explanation, catalyst, main risk",
    "key_factors": ["factor1", "factor2", "factor3"],
    "risk_level": "low" | "medium" | "high",
    "time_horizon": "swing (5-10 days)",
    "price_target": price the stock could reach in 5-10 days (number, 8-15% above entry),
    "stop_loss": exit if price hits this (2-3x daily ATR below entry, max 6% away),
    "atr_value": the daily ATR value you used,
    "alternative_action": "If the trade goes against you, do this"
}}

**Your swing-trade decision:**"""

        return PromptTemplate(
            template=template,
            input_variables=[
                "ticker", "company_name", "sector", "industry",
                "current_price", "price_change_20d", "trend", "rsi", "rsi_signal",
                "macd_signal", "volume_signal", "volatility_level", "volatility",
                "support_resistance", "technical_summary", "atr_value",
                "pe_ratio", "price_to_book", "price_to_sales", "valuation_score",
                "profit_margin", "return_on_equity", "current_ratio", "debt_to_equity", "health_score",
                "revenue_growth", "earnings_growth", "growth_score",
                "analyst_recommendation", "analyst_target_price", "analyst_count",
                "news_count", "news_sentiment", "news_sentiment_score", "news_topics", "news_summary",
                "market_trend", "market_strength", "market_vix", "sector_performance", "sector",
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
            _t0 = time.time()
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            _latency = round(time.time() - _t0, 2)

            # Parse JSON response
            decision_data = self._parse_response(response.content)

            # Validate and ensure consistency
            decision_data = self._validate_decision(decision_data, inputs)
            decision_data['llm_status'] = 'ok'
            decision_data['model'] = getattr(self.llm, 'model_name', None) or getattr(self.llm, 'model', None)
            decision_data['latency_s'] = _latency

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
                'alternative_action': 'Wait for system resolution',
                # marks this as the exception fallback, NOT a model decision — production
                # once ran two months of these (exhausted OpenAI quota) with nothing to tell
                # them apart from a real HOLD
                'llm_status': 'fallback_error',
                'error': str(e)[:300],
                'model': getattr(self.llm, 'model_name', None) or getattr(self.llm, 'model', None),
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
            "atr_value": features.get('atr', 0) or 0,

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
            "sector_performance": self._format_sector_perf(sector, market.get('sector_perf', {})),
            "sector": sector,
            "indices_performance": indices_text
        }

    def _format_sector_perf(self, sector: str, sector_perf: Dict[str, float]) -> str:
        """Format sector performance for the prompt."""
        if not sector_perf:
            return "N/A"
        own = sector_perf.get(sector)
        own_str = f"{sector}: {own:+.1f}% today" if own is not None else f"{sector}: N/A"
        # Show top 2 gainers and top 2 losers for context
        sorted_s = sorted(sector_perf.items(), key=lambda x: x[1], reverse=True)
        best = [f"{s} {v:+.1f}%" for s, v in sorted_s[:2]]
        worst = [f"{s} {v:+.1f}%" for s, v in sorted_s[-2:]]
        return f"{own_str} | Best: {', '.join(best)} | Worst: {', '.join(worst)}"

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM JSON response with multiple fallback strategies."""
        import re

        cleaned = response_text.strip()

        # Strip markdown code fences
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        # Strategy 1: direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 2: extract first {...} block (handles extra prose around JSON)
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse JSON response. Raw:\n{response_text[:500]}")
        raise json.JSONDecodeError("Could not extract JSON from LLM response", response_text, 0)

    def _validate_decision(self, decision: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize decision data."""

        # Ensure decision is valid
        if decision.get('decision') not in ['BUY', 'SELL', 'HOLD']:
            decision['decision'] = 'HOLD'

        # Ensure confidence is in range
        confidence = decision.get('confidence', 0.5)
        decision['confidence'] = max(0.0, min(1.0, float(confidence)))

        # Ensure required fields exist
        decision.setdefault('reasoning', 'Decision based on technical analysis')
        decision.setdefault('key_factors', [])
        decision.setdefault('risk_level', 'medium')
        # Fill in price_target/stop_loss from ATR if LLM omitted them.
        current_price = float(inputs.get('current_price') or 0)
        atr_val = float(inputs.get('atr_value') or decision.get('atr_value') or 0)
        if self.swing_mode:
            if current_price > 0 and atr_val > 0:
                decision.setdefault('price_target', round(current_price + 6 * atr_val, 2))
                decision.setdefault('stop_loss',    round(current_price - 2.5 * atr_val, 2))
            else:
                decision.setdefault('price_target', round(current_price * 1.10, 2) if current_price else None)
                decision.setdefault('stop_loss',    round(current_price * 0.96, 2) if current_price else None)
            decision['time_horizon'] = 'swing (5-10 days)'
        else:
            if current_price > 0 and atr_val > 0:
                decision.setdefault('price_target', round(current_price + 3 * atr_val, 2))
                decision.setdefault('stop_loss',    round(current_price - 1.5 * atr_val, 2))
            else:
                decision.setdefault('price_target', round(current_price * 1.04, 2) if current_price else None)
                decision.setdefault('stop_loss',    round(current_price * 0.98, 2) if current_price else None)
            decision['time_horizon'] = 'intraday (today only)'
        decision.setdefault('atr_value', None)
        decision.setdefault('alternative_action', 'Exit position and wait for next scan')

        # Adjust confidence based on RSI signal strength so scores aren't all the same
        rsi = float(inputs.get('rsi', 50) or 50)
        conf = decision['confidence']
        if decision['decision'] == 'BUY':
            if rsi < 20:
                conf = max(conf, 0.82)   # very oversold — floor at 82%
            elif rsi < 30:
                conf = max(conf, 0.68)   # oversold — floor at 68%
            elif rsi > 50:
                conf = min(conf, 0.58)   # not even oversold — cap at 58%
        elif decision['decision'] == 'SELL':
            if rsi > 80:
                conf = max(conf, 0.82)   # very overbought — floor at 82%
            elif rsi > 70:
                conf = max(conf, 0.68)   # overbought — floor at 68%
            elif rsi < 50:
                conf = min(conf, 0.58)   # not even overbought — cap at 58%
        decision['confidence'] = round(max(0.0, min(1.0, conf)), 2)

        return decision


# Singleton instances
_autonomous_reasoning_agent_instance = None
_swing_reasoning_agent_instance = None


def get_autonomous_reasoning_agent() -> AutonomousReasoningAgent:
    """Get or create the AutonomousReasoningAgent singleton (intraday mode)."""
    global _autonomous_reasoning_agent_instance
    if _autonomous_reasoning_agent_instance is None:
        _autonomous_reasoning_agent_instance = AutonomousReasoningAgent()
    return _autonomous_reasoning_agent_instance


def get_swing_reasoning_agent() -> AutonomousReasoningAgent:
    """Get or create the AutonomousReasoningAgent singleton (swing mode)."""
    global _swing_reasoning_agent_instance
    if _swing_reasoning_agent_instance is None:
        _swing_reasoning_agent_instance = AutonomousReasoningAgent(swing_mode=True)
    return _swing_reasoning_agent_instance
