"""
Autonomous Decision Graph: Fully autonomous stock analysis workflow.
Integrates technical, fundamental, news, and market context without user input.
"""

from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents.data_agent import get_data_agent
from agents.graph_feature_agent import get_graph_feature_agent
from agents.fundamental_agent import get_fundamental_agent
from agents.enhanced_news_agent import get_enhanced_news_agent
from agents.market_context_agent import get_market_context_agent
from agents.autonomous_reasoning_agent import get_autonomous_reasoning_agent
from agents.rag_agent import get_rag_agent

logger = logging.getLogger(__name__)


class AutonomousGraphState(TypedDict):
    """State object for the autonomous decision graph."""
    ticker: str
    period: str
    interval: str
    stock_data: Any
    features: Dict[str, Any]
    fundamentals: Dict[str, Any]
    news_analysis: Dict[str, Any]
    market_context: Dict[str, Any]
    rag_context: str
    decision: Dict[str, Any]
    error: str


class AutonomousStockDecisionGraph:
    """LangGraph-based autonomous decision workflow."""

    def __init__(self):
        """Initialize the autonomous decision graph."""
        self.data_agent = get_data_agent()
        self.feature_agent = get_graph_feature_agent()
        self.fundamental_agent = get_fundamental_agent()
        self.news_agent = get_enhanced_news_agent()  # Using enhanced news agent
        self.market_context_agent = get_market_context_agent()
        self.autonomous_reasoning_agent = get_autonomous_reasoning_agent()
        self.rag_agent = get_rag_agent()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(AutonomousGraphState)

        # Add nodes
        workflow.add_node("fetch_data", self.fetch_data_node)
        workflow.add_node("extract_features", self.extract_features_node)
        workflow.add_node("get_fundamentals", self.get_fundamentals_node)
        workflow.add_node("analyze_news", self.analyze_news_node)
        workflow.add_node("get_market_context", self.get_market_context_node)
        workflow.add_node("retrieve_rag_context", self.retrieve_rag_context_node)
        workflow.add_node("autonomous_decision", self.autonomous_decision_node)

        # Set entry point
        workflow.add_edge("__start__", "fetch_data")

        # Linear flow
        workflow.add_edge("fetch_data", "extract_features")
        workflow.add_edge("extract_features", "get_fundamentals")
        workflow.add_edge("get_fundamentals", "analyze_news")
        workflow.add_edge("analyze_news", "get_market_context")
        workflow.add_edge("get_market_context", "retrieve_rag_context")
        workflow.add_edge("retrieve_rag_context", "autonomous_decision")
        workflow.add_edge("autonomous_decision", END)

        return workflow.compile()

    def fetch_data_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Fetch stock data from Yahoo Finance."""
        logger.info(f"[1/7] Fetching data for {state['ticker']}")

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
                logger.info(f"✓ Fetched {len(df)} price records")

        except Exception as e:
            state['error'] = f"Error fetching data: {str(e)}"
            logger.error(state['error'])

        return state

    def extract_features_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Extract technical features."""
        logger.info("[2/7] Extracting technical features")

        if 'error' in state and state['error']:
            return state

        try:
            features = self.feature_agent.extract_features(
                state['stock_data'],
                state['ticker']
            )
            state['features'] = features
            logger.info("✓ Technical analysis complete")

        except Exception as e:
            state['error'] = f"Error extracting features: {str(e)}"
            logger.error(state['error'])

        return state

    def get_fundamentals_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Get fundamental financial data."""
        logger.info("[3/7] Analyzing fundamentals")

        if 'error' in state and state['error']:
            return state

        try:
            fundamentals = self.fundamental_agent.get_fundamentals(state['ticker'])
            state['fundamentals'] = fundamentals

            val_score = fundamentals.get('valuation_score', 0.5)
            health_score = fundamentals.get('health_score', 0.5)
            growth_score = fundamentals.get('growth_score', 0.5)

            logger.info(f"✓ Fundamentals: Valuation={val_score:.2f} Health={health_score:.2f} Growth={growth_score:.2f}")

        except Exception as e:
            state['error'] = f"Error getting fundamentals: {str(e)}"
            logger.error(state['error'])
            state['fundamentals'] = {}

        return state

    def analyze_news_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Analyze news sentiment."""
        logger.info("[4/7] Analyzing news & sentiment")

        if 'error' in state and state['error']:
            return state

        try:
            company_name = state.get('fundamentals', {}).get('company_name', state['ticker'])

            # Create simple LLM analyzer for news agent
            def llm_analyze(prompt: str) -> Dict[str, Any]:
                from langchain_core.messages import HumanMessage
                import json

                response = self.autonomous_reasoning_agent.llm.invoke([HumanMessage(content=prompt)])

                # Parse JSON response
                cleaned = response.content.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]

                return json.loads(cleaned.strip())

            news_analysis = self.news_agent.get_news_analysis(
                state['ticker'],
                company_name,
                llm_analyze
            )

            state['news_analysis'] = news_analysis

            sentiment = news_analysis.get('sentiment', 'neutral')
            news_count = news_analysis.get('news_count', 0)

            logger.info(f"✓ Found {news_count} news items, sentiment: {sentiment}")

        except Exception as e:
            logger.warning(f"News analysis had issues: {str(e)}")
            state['news_analysis'] = {
                'news_count': 0,
                'sentiment': 'neutral',
                'sentiment_score': 0.5,
                'summary': 'No news data available',
                'key_topics': []
            }

        return state

    def get_market_context_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Get market context."""
        logger.info("[5/7] Analyzing market context")

        if 'error' in state and state['error']:
            return state

        try:
            market_context = self.market_context_agent.get_market_context()
            state['market_context'] = market_context

            trend = market_context.get('market_trend', 'neutral')
            vix = market_context.get('volatility_index', 'N/A')

            logger.info(f"✓ Market: {trend}, VIX: {vix}")

        except Exception as e:
            logger.warning(f"Market context had issues: {str(e)}")
            state['market_context'] = {
                'market_trend': 'neutral',
                'market_strength': 0.5,
                'volatility_index': None,
                'indices': {}
            }

        return state

    def retrieve_rag_context_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Retrieve RAG context."""
        logger.info("[6/7] Retrieving pattern knowledge")

        if 'error' in state and state['error']:
            return state

        try:
            context = self.rag_agent.retrieve_context(state['features'])
            state['rag_context'] = context
            logger.info("✓ Retrieved historical patterns")

        except Exception as e:
            logger.warning(f"RAG context retrieval had issues: {str(e)}")
            state['rag_context'] = "No historical context available."

        return state

    def autonomous_decision_node(self, state: AutonomousGraphState) -> AutonomousGraphState:
        """Node: Make autonomous decision."""
        logger.info("[7/7] Making autonomous decision")

        if 'error' in state and state['error']:
            # Create error decision
            state['decision'] = {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": f"Analysis failed: {state['error']}",
                "key_factors": ["Error occurred"],
                "risk_level": "high",
                "time_horizon": "unknown",
                "price_target": None,
                "stop_loss": None,
                "alternative_action": "Wait for system resolution"
            }
            return state

        try:
            # Combine all analysis data
            decision = self.autonomous_reasoning_agent.analyze(
                ticker=state['ticker'],
                technical_data={
                    'features': state['features'],
                    'rag_context': state['rag_context']
                },
                fundamental_data=state['fundamentals'],
                news_data=state['news_analysis'],
                market_context=state['market_context']
            )

            state['decision'] = decision

            logger.info(f"✓ DECISION: {decision['decision']} at {decision['confidence']:.1%} confidence")
            logger.info(f"  Risk Level: {decision.get('risk_level', 'unknown')}")
            logger.info(f"  Time Horizon: {decision.get('time_horizon', 'unknown')}")

        except Exception as e:
            state['error'] = f"Error during autonomous decision: {str(e)}"
            logger.error(state['error'])
            state['decision'] = {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": str(e),
                "key_factors": ["Error"],
                "risk_level": "high",
                "time_horizon": "unknown",
                "price_target": None,
                "stop_loss": None,
                "alternative_action": "Wait for system resolution"
            }

        return state

    def run(self, ticker: str, period: str = "6mo", interval: str = "1d") -> Dict[str, Any]:
        """
        Run the autonomous decision graph for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Data period
            interval: Data interval

        Returns:
            Dictionary containing final decision and all intermediate results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"AUTONOMOUS ANALYSIS: {ticker}")
        logger.info(f"{'='*70}\n")

        initial_state = AutonomousGraphState(
            ticker=ticker.upper(),
            period=period,
            interval=interval,
            stock_data=None,
            features={},
            fundamentals={},
            news_analysis={},
            market_context={},
            rag_context="",
            decision={},
            error=""
        )

        try:
            final_state = self.graph.invoke(initial_state)
            logger.info(f"\n{'='*70}")
            logger.info("ANALYSIS COMPLETE")
            logger.info(f"{'='*70}\n")
            return final_state

        except Exception as e:
            logger.error(f"Error running autonomous decision graph: {str(e)}")
            return {
                "ticker": ticker,
                "error": str(e),
                "decision": {
                    "decision": "HOLD",
                    "confidence": 0.0,
                    "reasoning": f"Graph execution failed: {str(e)}",
                    "key_factors": ["System error"],
                    "risk_level": "high",
                    "time_horizon": "unknown",
                    "price_target": None,
                    "stop_loss": None,
                    "alternative_action": "Contact support"
                }
            }


# Singleton instance
_autonomous_decision_graph_instance = None


def get_autonomous_decision_graph() -> AutonomousStockDecisionGraph:
    """Get or create the AutonomousStockDecisionGraph singleton."""
    global _autonomous_decision_graph_instance
    if _autonomous_decision_graph_instance is None:
        _autonomous_decision_graph_instance = AutonomousStockDecisionGraph()
    return _autonomous_decision_graph_instance
