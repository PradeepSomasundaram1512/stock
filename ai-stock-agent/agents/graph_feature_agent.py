"""
Graph Feature Agent: Extracts technical signals and patterns from stock price data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tools.indicator_utils import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
    calculate_atr, calculate_bollinger_bands, detect_support_resistance,
    calculate_volatility, detect_crossover, analyze_volume_trend
)
from app.config import (
    RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    SMA_SHORT, SMA_LONG, EMA_SHORT, EMA_LONG, ATR_PERIOD,
    RSI_OVERBOUGHT, RSI_OVERSOLD, HIGH_VOLATILITY_THRESHOLD
)

logger = logging.getLogger(__name__)


class GraphFeatureAgent:
    """Agent responsible for extracting technical features from stock data."""

    def __init__(self):
        """Initialize the Graph Feature Agent."""
        pass

    def extract_features(self, df: pd.DataFrame, ticker: str) -> Dict[str, Any]:
        """
        Extract comprehensive technical features from stock data.

        Args:
            df: DataFrame with OHLCV data (lowercase columns)
            ticker: Stock ticker symbol

        Returns:
            Dictionary containing extracted features and signals
        """
        if df is None or df.empty:
            logger.error("Cannot extract features from empty DataFrame")
            return self._get_empty_features()

        logger.info(f"Extracting features for {ticker}")

        try:
            features = {
                "ticker": ticker,
                "latest_price": float(df['close'].iloc[-1]),
                "price_change_1d": self._calculate_price_change(df, periods=1),
                "price_change_5d": self._calculate_price_change(df, periods=5),
                "price_change_20d": self._calculate_price_change(df, periods=20),
            }

            # Technical indicators
            features.update(self._extract_moving_averages(df))
            features.update(self._extract_rsi(df))
            features.update(self._extract_macd(df))
            features.update(self._extract_volatility(df))
            features.update(self._extract_volume_signals(df))
            features.update(self._extract_support_resistance(df))

            # High-level interpretations
            features.update(self._interpret_signals(features))

            logger.info(f"Successfully extracted features for {ticker}")
            return features

        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return self._get_empty_features()

    def _calculate_price_change(self, df: pd.DataFrame, periods: int) -> float:
        """Calculate percentage price change over specified periods."""
        if len(df) < periods + 1:
            return 0.0
        current = df['close'].iloc[-1]
        previous = df['close'].iloc[-periods-1]
        return float(((current - previous) / previous) * 100)

    def _extract_moving_averages(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract moving average signals."""
        close = df['close']

        sma_short = calculate_sma(close, SMA_SHORT)
        sma_long = calculate_sma(close, SMA_LONG)
        ema_short = calculate_ema(close, EMA_SHORT)
        ema_long = calculate_ema(close, EMA_LONG)

        latest_price = close.iloc[-1]

        return {
            "sma_short": float(sma_short.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) else None,
            "sma_long": float(sma_long.iloc[-1]) if not pd.isna(sma_long.iloc[-1]) else None,
            "ema_short": float(ema_short.iloc[-1]) if not pd.isna(ema_short.iloc[-1]) else None,
            "ema_long": float(ema_long.iloc[-1]) if not pd.isna(ema_long.iloc[-1]) else None,
            "price_above_sma_short": bool(latest_price > sma_short.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) else None,
            "price_above_sma_long": bool(latest_price > sma_long.iloc[-1]) if not pd.isna(sma_long.iloc[-1]) else None,
            "sma_crossover": detect_crossover(sma_short, sma_long, lookback=5),
            "ema_crossover": detect_crossover(ema_short, ema_long, lookback=5),
        }

    def _extract_rsi(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract RSI signals."""
        rsi = calculate_rsi(df['close'], RSI_PERIOD)
        latest_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

        rsi_signal = "neutral"
        if latest_rsi > RSI_OVERBOUGHT:
            rsi_signal = "overbought"
        elif latest_rsi < RSI_OVERSOLD:
            rsi_signal = "oversold"

        return {
            "rsi": latest_rsi,
            "rsi_signal": rsi_signal,
        }

    def _extract_macd(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract MACD signals."""
        macd_line, signal_line, histogram = calculate_macd(
            df['close'], MACD_FAST, MACD_SLOW, MACD_SIGNAL
        )

        latest_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0
        latest_signal = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0.0
        latest_histogram = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0

        macd_signal = "bullish" if latest_macd > latest_signal else "bearish"

        # Check for crossover
        macd_crossover = detect_crossover(macd_line, signal_line, lookback=3)

        return {
            "macd": latest_macd,
            "macd_signal_line": latest_signal,
            "macd_histogram": latest_histogram,
            "macd_signal": macd_signal,
            "macd_crossover": macd_crossover,
        }

    def _extract_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract volatility metrics."""
        returns = df['close'].pct_change()
        volatility = calculate_volatility(returns, period=20)

        atr = calculate_atr(df['high'], df['low'], df['close'], ATR_PERIOD)
        latest_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0

        # Normalize ATR by price
        normalized_atr = (latest_atr / df['close'].iloc[-1]) * 100

        volatility_level = "low"
        if volatility > HIGH_VOLATILITY_THRESHOLD * 1.5:
            volatility_level = "high"
        elif volatility > HIGH_VOLATILITY_THRESHOLD:
            volatility_level = "medium"

        return {
            "volatility": float(volatility),
            "atr": latest_atr,
            "normalized_atr": float(normalized_atr),
            "volatility_level": volatility_level,
        }

    def _extract_volume_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract volume-based signals."""
        volume = df['volume']

        avg_volume_20d = volume.tail(20).mean()
        latest_volume = volume.iloc[-1]

        volume_ratio = latest_volume / avg_volume_20d if avg_volume_20d > 0 else 1.0
        volume_confirmation = volume_ratio > 1.2  # 20% above average

        volume_trend = analyze_volume_trend(volume, lookback=10)

        return {
            "latest_volume": int(latest_volume),
            "avg_volume_20d": float(avg_volume_20d),
            "volume_ratio": float(volume_ratio),
            "volume_confirmation": bool(volume_confirmation),
            "volume_trend": volume_trend,
        }

    def _extract_support_resistance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract support and resistance levels."""
        support, resistance = detect_support_resistance(df['close'], window=20)

        latest_price = df['close'].iloc[-1]

        distance_to_support = None
        distance_to_resistance = None

        if support is not None:
            distance_to_support = float(((latest_price - support) / support) * 100)

        if resistance is not None:
            distance_to_resistance = float(((resistance - latest_price) / latest_price) * 100)

        return {
            "support_level": support,
            "resistance_level": resistance,
            "distance_to_support_pct": distance_to_support,
            "distance_to_resistance_pct": distance_to_resistance,
        }

    def _interpret_signals(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level interpretations from technical signals."""

        # Determine overall trend
        trend = "neutral"
        if features.get("price_above_sma_short") and features.get("price_above_sma_long"):
            if features.get("sma_short", 0) > features.get("sma_long", 0):
                trend = "bullish"
        elif not features.get("price_above_sma_short") and not features.get("price_above_sma_long"):
            if features.get("sma_short", 0) < features.get("sma_long", 0):
                trend = "bearish"

        # Determine momentum
        momentum = "neutral"
        if features.get("macd_signal") == "bullish" and features.get("rsi", 50) > 50:
            momentum = "increasing"
        elif features.get("macd_signal") == "bearish" and features.get("rsi", 50) < 50:
            momentum = "decreasing"

        # Detect patterns (simplified)
        pattern = "none"
        if features.get("rsi_signal") == "oversold" and features.get("macd_crossover") == "bullish_cross":
            pattern = "potential_bottom"
        elif features.get("rsi_signal") == "overbought" and features.get("macd_crossover") == "bearish_cross":
            pattern = "potential_top"

        return {
            "trend": trend,
            "momentum": momentum,
            "pattern": pattern,
        }

    def _get_empty_features(self) -> Dict[str, Any]:
        """Return empty feature dictionary for error cases."""
        return {
            "ticker": "UNKNOWN",
            "error": "Failed to extract features",
            "trend": "neutral",
            "momentum": "neutral",
            "volatility_level": "unknown",
            "pattern": "none",
            "volume_confirmation": False,
        }


# Singleton instance
_graph_feature_agent_instance = None


def get_graph_feature_agent() -> GraphFeatureAgent:
    """Get or create the GraphFeatureAgent singleton."""
    global _graph_feature_agent_instance
    if _graph_feature_agent_instance is None:
        _graph_feature_agent_instance = GraphFeatureAgent()
    return _graph_feature_agent_instance
