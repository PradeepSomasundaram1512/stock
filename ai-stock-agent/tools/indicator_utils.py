"""
Technical indicator calculation utilities.
Provides clean, testable functions for computing common stock market indicators.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.

    Args:
        data: Price series
        period: Number of periods for SMA

    Returns:
        SMA series
    """
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Args:
        data: Price series
        period: Number of periods for EMA

    Returns:
        EMA series
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.

    Args:
        data: Price series (typically close prices)
        period: RSI period (default 14)

    Returns:
        RSI series (0-100)
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    data: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        data: Price series
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (volatility indicator).

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period

    Returns:
        ATR series
    """
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return atr


def calculate_bollinger_bands(
    data: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        data: Price series
        period: SMA period
        std_dev: Number of standard deviations

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle_band = calculate_sma(data, period)
    std = data.rolling(window=period).std()

    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return upper_band, middle_band, lower_band


def detect_support_resistance(data: pd.Series, window: int = 20) -> Tuple[Optional[float], Optional[float]]:
    """
    Detect basic support and resistance levels.

    Args:
        data: Price series
        window: Lookback window

    Returns:
        Tuple of (support_level, resistance_level)
    """
    if len(data) < window:
        return None, None

    recent_data = data.tail(window)
    support = recent_data.min()
    resistance = recent_data.max()

    return float(support), float(resistance)


def calculate_volatility(returns: pd.Series, period: int = 20) -> float:
    """
    Calculate annualized volatility from returns.

    Args:
        returns: Return series
        period: Rolling window period

    Returns:
        Volatility as decimal (e.g., 0.25 = 25%)
    """
    if len(returns) < period:
        return 0.0

    # Annualized volatility
    volatility = returns.tail(period).std() * np.sqrt(252)
    return float(volatility)


def detect_crossover(series1: pd.Series, series2: pd.Series, lookback: int = 5) -> str:
    """
    Detect if two series have crossed over recently.

    Args:
        series1: First series (e.g., fast MA)
        series2: Second series (e.g., slow MA)
        lookback: Number of periods to check

    Returns:
        "bullish_cross" if series1 crossed above series2
        "bearish_cross" if series1 crossed below series2
        "none" if no crossover
    """
    if len(series1) < lookback or len(series2) < lookback:
        return "none"

    recent1 = series1.tail(lookback)
    recent2 = series2.tail(lookback)

    # Check for bullish crossover (series1 crosses above series2)
    for i in range(1, len(recent1)):
        if recent1.iloc[i-1] <= recent2.iloc[i-1] and recent1.iloc[i] > recent2.iloc[i]:
            return "bullish_cross"
        if recent1.iloc[i-1] >= recent2.iloc[i-1] and recent1.iloc[i] < recent2.iloc[i]:
            return "bearish_cross"

    return "none"


def analyze_volume_trend(volume: pd.Series, lookback: int = 10) -> str:
    """
    Analyze volume trend.

    Args:
        volume: Volume series
        lookback: Number of periods to analyze

    Returns:
        "increasing", "decreasing", or "stable"
    """
    if len(volume) < lookback:
        return "stable"

    recent_volume = volume.tail(lookback)
    avg_first_half = recent_volume.iloc[:lookback//2].mean()
    avg_second_half = recent_volume.iloc[lookback//2:].mean()

    change = (avg_second_half - avg_first_half) / avg_first_half

    if change > 0.2:
        return "increasing"
    elif change < -0.2:
        return "decreasing"
    else:
        return "stable"
