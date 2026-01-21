"""
Reasoning Agent: Uses LLM to analyze technical signals and make decisions.
"""

import json
from typing import Dict, Any
import logging
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

from app.config import (
    LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, FINANCIAL_DISCLAIMER,
    PROJECT_ROOT
)

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """Agent responsible for LLM-based reasoning and decision making."""

    def __init__(self):
        """Initialize the Reasoning Agent."""
        self.llm = self._initialize_llm()
        self.prompt_template = self._load_prompt_template()

    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        try:
            if LLM_PROVIDER == "openai":
                if not OPENAI_API_KEY:
                    raise ValueError("OPENAI_API_KEY not set")
                logger.info(f"Initializing OpenAI LLM: {LLM_MODEL}")
                return ChatOpenAI(
                    model=LLM_MODEL,
                    temperature=LLM_TEMPERATURE,
                    api_key=OPENAI_API_KEY
                )
            elif LLM_PROVIDER == "anthropic":
                if not ANTHROPIC_API_KEY:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                logger.info(f"Initializing Anthropic LLM: {LLM_MODEL}")
                return ChatAnthropic(
                    model=LLM_MODEL,
                    temperature=LLM_TEMPERATURE,
                    api_key=ANTHROPIC_API_KEY
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise

    def _load_prompt_template(self) -> str:
        """Load the reasoning prompt template."""
        # Try enhanced prompt first, fallback to basic
        prompt_path = PROJECT_ROOT / "prompts" / "reasoning_prompt_enhanced.txt"
        if not prompt_path.exists():
            prompt_path = PROJECT_ROOT / "prompts" / "reasoning_prompt.txt"

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"Loaded reasoning prompt template from {prompt_path.name}")
            return template
        except Exception as e:
            logger.error(f"Error loading prompt template: {str(e)}")
            # Return a basic template as fallback
            return self._get_fallback_template()

    def _get_fallback_template(self) -> str:
        """Get a basic fallback template if file loading fails."""
        return """Analyze the following stock data and provide a JSON response with:
        decision (BUY/HOLD/SELL), confidence (0-1), sentiment, explanation, key_signals, risk_factors.

        Ticker: {ticker}
        Price: {latest_price}
        Features: {features}
        Context: {context}
        """

    def analyze(
        self,
        ticker: str,
        latest_price: float,
        features: Dict[str, Any],
        context: str,
        fundamentals: Dict[str, Any] = None,
        news_sentiment: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Perform LLM-based analysis of technical signals.

        Args:
            ticker: Stock ticker symbol
            latest_price: Current stock price
            features: Technical features dictionary
            context: Retrieved historical context from RAG
            fundamentals: Fundamental data (P/E, revenue, etc.)
            news_sentiment: News and sentiment data

        Returns:
            Dictionary containing decision, confidence, explanation, etc.
        """
        try:
            # Format the prompt
            prompt = self.prompt_template.format(
                ticker=ticker,
                latest_price=latest_price,
                features=self._format_features(features),
                fundamentals=self._format_fundamentals(fundamentals or {}),
                news_sentiment=self._format_news(news_sentiment or {}),
                context=context
            )

            logger.info(f"Sending analysis request to LLM for {ticker}")

            # Get LLM response
            response = self.llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content

            logger.info("Received LLM response")

            # Parse JSON response
            decision_data = self._parse_llm_response(response_text)

            # Add disclaimer
            decision_data["disclaimer"] = FINANCIAL_DISCLAIMER

            # Validate decision data
            decision_data = self._validate_decision(decision_data)

            return decision_data

        except Exception as e:
            logger.error(f"Error during LLM analysis: {str(e)}")
            return self._get_error_decision(str(e))

    def _format_features(self, features: Dict[str, Any]) -> str:
        """Format features dictionary into readable string."""
        formatted_lines = []

        # Group features by category
        categories = {
            "Price Action": ["latest_price", "price_change_1d", "price_change_5d", "price_change_20d"],
            "Moving Averages": ["sma_short", "sma_long", "ema_short", "ema_long", "price_above_sma_short",
                               "price_above_sma_long", "sma_crossover", "ema_crossover"],
            "RSI": ["rsi", "rsi_signal"],
            "MACD": ["macd", "macd_signal_line", "macd_histogram", "macd_signal", "macd_crossover"],
            "Volatility": ["volatility", "atr", "normalized_atr", "volatility_level"],
            "Volume": ["latest_volume", "avg_volume_20d", "volume_ratio", "volume_confirmation", "volume_trend"],
            "Support/Resistance": ["support_level", "resistance_level", "distance_to_support_pct",
                                  "distance_to_resistance_pct"],
            "Interpretation": ["trend", "momentum", "pattern"]
        }

        for category, keys in categories.items():
            formatted_lines.append(f"\n{category}:")
            for key in keys:
                if key in features:
                    value = features[key]
                    if isinstance(value, float):
                        formatted_lines.append(f"  - {key}: {value:.2f}")
                    else:
                        formatted_lines.append(f"  - {key}: {value}")

        return "\n".join(formatted_lines)

    def _format_fundamentals(self, fundamentals: Dict[str, Any]) -> str:
        """Format fundamentals dictionary into readable string."""
        if not fundamentals:
            return "No fundamental data available"

        lines = []

        # Key fundamental metrics
        if 'pe_ratio' in fundamentals and fundamentals['pe_ratio']:
            lines.append(f"  - P/E Ratio: {fundamentals['pe_ratio']:.2f}")

        if 'market_cap' in fundamentals and fundamentals['market_cap']:
            market_cap_b = fundamentals['market_cap'] / 1e9
            lines.append(f"  - Market Cap: ${market_cap_b:.2f}B")

        if 'revenue_growth' in fundamentals:
            lines.append(f"  - Revenue Growth: {fundamentals['revenue_growth']*100:.1f}%")

        if 'profit_margin' in fundamentals:
            lines.append(f"  - Profit Margin: {fundamentals['profit_margin']*100:.1f}%")

        if 'recommendation' in fundamentals and fundamentals['recommendation']:
            lines.append(f"  - Analyst Rating: {fundamentals['recommendation']}")

        if 'target_price' in fundamentals and fundamentals['target_price']:
            lines.append(f"  - Analyst Target: ${fundamentals['target_price']:.2f}")

        return "\n".join(lines) if lines else "Limited fundamental data"

    def _format_news(self, news_sentiment: Dict[str, Any]) -> str:
        """Format news and sentiment data into readable string."""
        if not news_sentiment:
            return "No recent news data available"

        lines = []

        if 'news_count' in news_sentiment:
            lines.append(f"  - Articles Found: {news_sentiment['news_count']}")

        if 'sentiment' in news_sentiment and news_sentiment['sentiment']:
            sentiment = news_sentiment['sentiment'].upper()
            lines.append(f"  - Overall Sentiment: {sentiment}")

        if 'sentiment_score' in news_sentiment:
            score = news_sentiment['sentiment_score']
            lines.append(f"  - Sentiment Score: {score:.1%}")

        if 'summary' in news_sentiment and news_sentiment['summary']:
            summary = news_sentiment['summary'][:200]
            lines.append(f"  - Summary: {summary}...")

        return "\n".join(lines) if lines else "No news data"

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response, extracting JSON."""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}")
            # Try to extract key information manually
            return self._extract_decision_from_text(response_text)

    def _extract_decision_from_text(self, text: str) -> Dict[str, Any]:
        """Fallback method to extract decision from unstructured text."""
        decision = "HOLD"
        confidence = 0.5
        sentiment = "neutral"

        text_lower = text.lower()

        # Simple keyword extraction
        if "buy" in text_lower and "sell" not in text_lower:
            decision = "BUY"
            sentiment = "bullish"
        elif "sell" in text_lower:
            decision = "SELL"
            sentiment = "bearish"

        return {
            "decision": decision,
            "confidence": confidence,
            "sentiment": sentiment,
            "explanation": text[:500],
            "key_signals": ["Unable to parse structured response"],
            "risk_factors": ["Response parsing failed"],
            "supporting_indicators": [],
            "conflicting_indicators": [],
            "disclaimer": FINANCIAL_DISCLAIMER
        }

    def _validate_decision(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize decision data."""
        # Ensure decision is uppercase and valid
        decision = decision_data.get("decision", "HOLD").upper()
        if decision not in ["BUY", "HOLD", "SELL"]:
            logger.warning(f"Invalid decision '{decision}', defaulting to HOLD")
            decision = "HOLD"
        decision_data["decision"] = decision

        # Ensure confidence is between 0 and 1
        confidence = float(decision_data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        decision_data["confidence"] = confidence

        # Ensure sentiment is valid
        sentiment = decision_data.get("sentiment", "neutral").lower()
        if sentiment not in ["bullish", "neutral", "bearish"]:
            sentiment = "neutral"
        decision_data["sentiment"] = sentiment

        # Ensure required fields exist
        required_fields = ["explanation", "key_signals", "risk_factors"]
        for field in required_fields:
            if field not in decision_data:
                decision_data[field] = ["Not provided"]

        return decision_data

    def _get_error_decision(self, error_msg: str) -> Dict[str, Any]:
        """Return a safe error decision."""
        return {
            "decision": "HOLD",
            "confidence": 0.0,
            "sentiment": "neutral",
            "explanation": f"Unable to complete analysis due to error: {error_msg}",
            "key_signals": ["Analysis error"],
            "risk_factors": ["System error", "Unable to analyze data"],
            "supporting_indicators": [],
            "conflicting_indicators": [],
            "disclaimer": FINANCIAL_DISCLAIMER
        }


# Singleton instance
_reasoning_agent_instance = None


def get_reasoning_agent() -> ReasoningAgent:
    """Get or create the ReasoningAgent singleton."""
    global _reasoning_agent_instance
    if _reasoning_agent_instance is None:
        _reasoning_agent_instance = ReasoningAgent()
    return _reasoning_agent_instance
