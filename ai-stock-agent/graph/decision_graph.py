"""
LangGraph Decision Graph: Orchestrates the stock analysis workflow.
"""

from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents.data_agent import get_data_agent
from agents.graph_feature_agent import get_graph_feature_agent
from agents.rag_agent import get_rag_agent
from agents.reasoning_agent import get_reasoning_agent
from app.config import HIGH_VOLATILITY_THRESHOLD, EXTREME_VOLATILITY_THRESHOLD

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """State object for the decision graph."""
    ticker: str
    period: str
    interval: str
    stock_data: Any
    features: Dict[str, Any]
    context: str
    decision: Dict[str, Any]
    risk_check_passed: bool
    error: str


class StockDecisionGraph:
    """LangGraph-based decision workflow for stock analysis."""

    def __init__(self):
        """Initialize the decision graph."""
        self.data_agent = get_data_agent()
        self.feature_agent = get_graph_feature_agent()
        self.rag_agent = get_rag_agent()
        self.reasoning_agent = get_reasoning_agent()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("fetch_data", self.fetch_data_node)
        workflow.add_node("extract_features", self.extract_features_node)
        workflow.add_node("retrieve_context", self.retrieve_context_node)
        workflow.add_node("risk_check", self.risk_check_node)
        workflow.add_node("add_risk_warning", self.add_risk_warning_node)
        workflow.add_node("llm_reasoning", self.llm_reasoning_node)
        workflow.add_node("finalize_decision", self.finalize_decision_node)

        # Set entry point
        workflow.add_edge("__start__", "fetch_data")

        # Add edges
        workflow.add_edge("fetch_data", "extract_features")
        workflow.add_edge("extract_features", "retrieve_context")
        workflow.add_edge("retrieve_context", "risk_check")

        # Conditional edge from risk_check
        workflow.add_conditional_edges(
            "risk_check",
            self.should_add_risk_warning,
            {
                "add_warning": "add_risk_warning",
                "continue": "llm_reasoning"
            }
        )

        workflow.add_edge("add_risk_warning", "llm_reasoning")
        workflow.add_edge("llm_reasoning", "finalize_decision")
        workflow.add_edge("finalize_decision", END)

        return workflow.compile()

    def fetch_data_node(self, state: GraphState) -> GraphState:
        """Node: Fetch stock data from Yahoo Finance."""
        logger.info(f"Fetching data for {state['ticker']}")

        try:
            df = self.data_agent.fetch_stock_data(
                state['ticker'],
                state.get('period', '6mo'),
                state.get('interval', '1d')
            )

            if df is None or df.empty:
                state['error'] = f"Failed to fetch data for {state['ticker']}"
                logger.error(state['error'])
            else:
                state['stock_data'] = df
                logger.info(f"Successfully fetched {len(df)} records")

        except Exception as e:
            state['error'] = f"Error fetching data: {str(e)}"
            logger.error(state['error'])

        return state

    def extract_features_node(self, state: GraphState) -> GraphState:
        """Node: Extract technical features from stock data."""
        logger.info("Extracting technical features")

        if 'error' in state and state['error']:
            return state

        try:
            features = self.feature_agent.extract_features(
                state['stock_data'],
                state['ticker']
            )
            state['features'] = features
            logger.info("Features extracted successfully")

        except Exception as e:
            state['error'] = f"Error extracting features: {str(e)}"
            logger.error(state['error'])

        return state

    def retrieve_context_node(self, state: GraphState) -> GraphState:
        """Node: Retrieve relevant context using RAG."""
        logger.info("Retrieving historical context")

        if 'error' in state and state['error']:
            return state

        try:
            context = self.rag_agent.retrieve_context(state['features'])
            state['context'] = context
            logger.info("Context retrieved successfully")

        except Exception as e:
            state['error'] = f"Error retrieving context: {str(e)}"
            logger.error(state['error'])
            state['context'] = "No context available."

        return state

    def risk_check_node(self, state: GraphState) -> GraphState:
        """Node: Check for high-risk conditions."""
        logger.info("Performing risk check")

        if 'error' in state and state['error']:
            state['risk_check_passed'] = False
            return state

        features = state.get('features', {})

        # Check for high risk conditions
        high_risk = False
        risk_reasons = []

        # EXTREME volatility check (only flag truly extreme cases)
        volatility = features.get('volatility', 0)
        if volatility > EXTREME_VOLATILITY_THRESHOLD:
            high_risk = True
            risk_reasons.append(f"Extreme volatility detected: {volatility*100:.2f}%")
        elif volatility > HIGH_VOLATILITY_THRESHOLD:
            # Note volatility but don't fail risk check
            risk_reasons.append(f"Elevated volatility: {volatility*100:.2f}%")

        # VERY Extreme RSI check (only flag very extreme cases)
        rsi = features.get('rsi', 50)
        if rsi > 85 or rsi < 15:
            high_risk = True
            risk_reasons.append(f"Extreme RSI: {rsi:.2f}")

        # Conflicting signals check
        if features.get('trend') == 'bullish' and features.get('momentum') == 'decreasing':
            risk_reasons.append("Conflicting trend and momentum signals")
        elif features.get('trend') == 'bearish' and features.get('momentum') == 'increasing':
            risk_reasons.append("Conflicting trend and momentum signals")

        state['risk_check_passed'] = not high_risk
        state['risk_reasons'] = risk_reasons

        logger.info(f"Risk check: {'FAILED' if high_risk else 'PASSED'}")
        if risk_reasons:
            logger.info(f"Risk reasons: {risk_reasons}")

        return state

    def should_add_risk_warning(self, state: GraphState) -> str:
        """Conditional edge: Determine if risk warning should be added."""
        if not state.get('risk_check_passed', True):
            return "add_warning"
        return "continue"

    def add_risk_warning_node(self, state: GraphState) -> GraphState:
        """Node: Add risk warning to context."""
        logger.info("Adding risk warning to context")

        risk_warning = "\n\n=== HIGH RISK CONDITIONS DETECTED ===\n"
        risk_warning += "CAUTION: The following high-risk conditions have been identified:\n"

        for reason in state.get('risk_reasons', []):
            risk_warning += f"- {reason}\n"

        risk_warning += "\nConsider waiting for more favorable conditions or reducing position size significantly.\n"
        risk_warning += "High-risk conditions increase the probability of unexpected moves and losses.\n"

        # Append to context
        state['context'] = state.get('context', '') + risk_warning

        return state

    def llm_reasoning_node(self, state: GraphState) -> GraphState:
        """Node: LLM-based reasoning and decision."""
        logger.info("Performing LLM reasoning")

        if 'error' in state and state['error']:
            # Create error decision
            state['decision'] = {
                "decision": "HOLD",
                "confidence": 0.0,
                "sentiment": "neutral",
                "explanation": f"Analysis failed: {state['error']}",
                "key_signals": ["Error occurred"],
                "risk_factors": [state['error']],
            }
            return state

        try:
            features = state['features']
            decision = self.reasoning_agent.analyze(
                ticker=state['ticker'],
                latest_price=features.get('latest_price', 0),
                features=features,
                context=state['context'],
                fundamentals=features.get('fundamentals', {}),
                news_sentiment=features.get('news', {})
            )

            state['decision'] = decision
            logger.info(f"LLM decision: {decision.get('decision')} (confidence: {decision.get('confidence', 0):.2f})")

        except Exception as e:
            state['error'] = f"Error during LLM reasoning: {str(e)}"
            logger.error(state['error'])
            state['decision'] = {
                "decision": "HOLD",
                "confidence": 0.0,
                "sentiment": "neutral",
                "explanation": str(e),
                "key_signals": ["Error"],
                "risk_factors": ["LLM reasoning failed"],
            }

        return state

    def finalize_decision_node(self, state: GraphState) -> GraphState:
        """Node: Finalize and validate the decision."""
        logger.info("Finalizing decision")

        decision = state.get('decision', {})

        # If EXTREME risk was detected, reduce confidence moderately
        if not state.get('risk_check_passed', True):
            original_confidence = decision.get('confidence', 0.5)
            # More modest reduction: 15% instead of 30%
            decision['confidence'] = original_confidence * 0.85
            logger.info(f"Reduced confidence due to extreme risk: {original_confidence:.2f} -> {decision['confidence']:.2f}")

            # Only change to HOLD if confidence drops very low
            if decision['confidence'] < 0.4 and decision['decision'] != 'HOLD':
                logger.info(f"Changing {decision['decision']} to HOLD due to very low confidence")
                decision['decision'] = 'HOLD'
                decision['explanation'] = (
                    f"Originally {decision['decision']}, but changing to HOLD due to extreme risk conditions. "
                    + decision.get('explanation', '')
                )

        state['decision'] = decision
        logger.info("Decision finalized")

        return state

    def run(self, ticker: str, period: str = "6mo", interval: str = "1d") -> Dict[str, Any]:
        """
        Run the decision graph for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Data period
            interval: Data interval

        Returns:
            Dictionary containing final decision and all intermediate results
        """
        logger.info(f"Starting decision graph for {ticker}")

        initial_state = GraphState(
            ticker=ticker.upper(),
            period=period,
            interval=interval,
            stock_data=None,
            features={},
            context="",
            decision={},
            risk_check_passed=True,
            error=""
        )

        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("Decision graph completed successfully")
            return final_state

        except Exception as e:
            logger.error(f"Error running decision graph: {str(e)}")
            return {
                "ticker": ticker,
                "error": str(e),
                "decision": {
                    "decision": "HOLD",
                    "confidence": 0.0,
                    "explanation": f"Graph execution failed: {str(e)}"
                }
            }


# Singleton instance
_decision_graph_instance = None


def get_decision_graph() -> StockDecisionGraph:
    """Get or create the StockDecisionGraph singleton."""
    global _decision_graph_instance
    if _decision_graph_instance is None:
        _decision_graph_instance = StockDecisionGraph()
    return _decision_graph_instance
