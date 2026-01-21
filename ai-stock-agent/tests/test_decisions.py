"""
Tests for AI Stock Agent decision system.
"""

import pytest
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent
from agents.graph_feature_agent import GraphFeatureAgent
from tools.indicator_utils import (
    calculate_sma, calculate_ema, calculate_rsi,
    calculate_macd, detect_crossover
)


class TestIndicatorUtils:
    """Test technical indicator calculations."""

    def test_sma_calculation(self):
        """Test Simple Moving Average calculation."""
        data = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        sma = calculate_sma(data, period=5)

        # First 4 values should be NaN, then valid values
        assert pd.isna(sma.iloc[3])
        assert not pd.isna(sma.iloc[4])
        assert abs(sma.iloc[4] - 12.0) < 0.01  # Average of 10-14

    def test_ema_calculation(self):
        """Test Exponential Moving Average calculation."""
        data = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        ema = calculate_ema(data, period=5)

        # EMA should exist for all values
        assert not pd.isna(ema.iloc[-1])
        # EMA should be close to recent values
        assert ema.iloc[-1] > 18 and ema.iloc[-1] < 21

    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Create uptrending data
        data = pd.Series([100 + i for i in range(30)])
        rsi = calculate_rsi(data, period=14)

        # RSI should be high for uptrend
        assert rsi.iloc[-1] > 50

        # Create downtrending data
        data = pd.Series([100 - i for i in range(30)])
        rsi = calculate_rsi(data, period=14)

        # RSI should be low for downtrend
        assert rsi.iloc[-1] < 50

    def test_macd_calculation(self):
        """Test MACD calculation."""
        data = pd.Series([100 + np.sin(i/5) * 10 for i in range(50)])
        macd_line, signal_line, histogram = calculate_macd(data)

        # All should have values
        assert not pd.isna(macd_line.iloc[-1])
        assert not pd.isna(signal_line.iloc[-1])
        assert not pd.isna(histogram.iloc[-1])

        # Histogram should be difference
        expected_hist = macd_line.iloc[-1] - signal_line.iloc[-1]
        assert abs(histogram.iloc[-1] - expected_hist) < 0.01

    def test_crossover_detection(self):
        """Test crossover detection."""
        # Create bullish crossover
        series1 = pd.Series([1, 2, 3, 4, 5])
        series2 = pd.Series([3, 3, 3, 3, 3])

        result = detect_crossover(series1, series2, lookback=5)
        assert result == "bullish_cross"

        # Create bearish crossover
        series1 = pd.Series([5, 4, 3, 2, 1])
        series2 = pd.Series([3, 3, 3, 3, 3])

        result = detect_crossover(series1, series2, lookback=5)
        assert result == "bearish_cross"


class TestDataAgent:
    """Test data fetching functionality."""

    def test_data_agent_initialization(self):
        """Test that DataAgent initializes properly."""
        agent = DataAgent()
        assert agent is not None
        assert hasattr(agent, 'cache')

    def test_data_cleaning(self):
        """Test data cleaning function."""
        agent = DataAgent()

        # Create sample data with NaN
        df = pd.DataFrame({
            'Open': [100, 101, np.nan, 103],
            'High': [102, 103, 104, 105],
            'Low': [99, 100, 101, 102],
            'Close': [101, 102, 103, 104],
            'Volume': [1000, 1100, 1200, np.nan]
        })

        cleaned = agent._clean_data(df)

        # Should remove rows with NaN in critical columns
        assert len(cleaned) < len(df)
        # Should have lowercase columns
        assert 'close' in cleaned.columns


class TestGraphFeatureAgent:
    """Test feature extraction."""

    def test_feature_agent_initialization(self):
        """Test that GraphFeatureAgent initializes properly."""
        agent = GraphFeatureAgent()
        assert agent is not None

    def test_empty_dataframe_handling(self):
        """Test handling of empty DataFrame."""
        agent = GraphFeatureAgent()
        features = agent.extract_features(pd.DataFrame(), "TEST")

        assert features.get('error') is not None
        assert features.get('trend') == 'neutral'

    def test_feature_extraction_structure(self):
        """Test that extracted features have correct structure."""
        agent = GraphFeatureAgent()

        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 150, 100) + np.random.randn(100) * 2,
            'high': np.linspace(102, 152, 100) + np.random.randn(100) * 2,
            'low': np.linspace(98, 148, 100) + np.random.randn(100) * 2,
            'open': np.linspace(100, 150, 100) + np.random.randn(100) * 2,
            'volume': np.random.randint(1000000, 2000000, 100)
        }, index=dates)

        features = agent.extract_features(df, "TEST")

        # Check required fields exist
        required_fields = [
            'ticker', 'latest_price', 'trend', 'momentum',
            'rsi', 'macd_signal', 'volatility_level', 'pattern'
        ]

        for field in required_fields:
            assert field in features, f"Missing required field: {field}"

        # Check data types
        assert isinstance(features['latest_price'], float)
        assert isinstance(features['trend'], str)
        assert isinstance(features['rsi'], float)


class TestIntegration:
    """Integration tests for the complete system."""

    def test_basic_workflow(self):
        """Test basic workflow without LLM."""
        from agents.data_agent import get_data_agent
        from agents.graph_feature_agent import get_graph_feature_agent

        # Create sample data instead of fetching real data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 150, 100),
            'high': np.linspace(102, 152, 100),
            'low': np.linspace(98, 148, 100),
            'open': np.linspace(100, 150, 100),
            'volume': np.random.randint(1000000, 2000000, 100)
        }, index=dates)

        feature_agent = get_graph_feature_agent()
        features = feature_agent.extract_features(df, "TEST")

        assert features is not None
        assert 'trend' in features
        assert 'momentum' in features

    def test_confidence_bounds(self):
        """Test that confidence scores are properly bounded."""
        # This would test the reasoning agent output
        # but we'll skip LLM calls in unit tests

        # Test validation function
        from agents.reasoning_agent import ReasoningAgent
        agent = ReasoningAgent()

        test_decision = {
            "decision": "BUY",
            "confidence": 1.5,  # Invalid (too high)
            "sentiment": "bullish"
        }

        validated = agent._validate_decision(test_decision)

        assert validated['confidence'] <= 1.0
        assert validated['confidence'] >= 0.0


def test_imports():
    """Test that all modules can be imported."""
    try:
        from app.config import validate_config
        from agents.data_agent import get_data_agent
        from agents.graph_feature_agent import get_graph_feature_agent
        from agents.rag_agent import get_rag_agent
        from agents.reasoning_agent import get_reasoning_agent
        from graph.decision_graph import get_decision_graph
        from tools.finance_tools import get_finance_tools

        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
