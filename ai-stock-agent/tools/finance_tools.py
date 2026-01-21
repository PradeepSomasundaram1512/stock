"""
LangChain tools for finance operations.
These tools can be used by LangChain agents.
"""

from typing import Optional
from langchain.tools import Tool
from langchain.pydantic_v1 import BaseModel, Field
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agents.data_agent import get_data_agent
from agents.graph_feature_agent import get_graph_feature_agent


class StockDataInput(BaseModel):
    """Input schema for stock data tool."""
    ticker: str = Field(description="Stock ticker symbol (e.g., AAPL, MSFT)")
    period: str = Field(default="6mo", description="Data period (e.g., 1mo, 3mo, 6mo, 1y)")
    interval: str = Field(default="1d", description="Data interval (e.g., 1d, 1wk, 1mo)")


class StockPriceInput(BaseModel):
    """Input schema for stock price tool."""
    ticker: str = Field(description="Stock ticker symbol")


class TechnicalAnalysisInput(BaseModel):
    """Input schema for technical analysis tool."""
    ticker: str = Field(description="Stock ticker symbol")
    period: str = Field(default="6mo", description="Analysis period")


def get_stock_data(ticker: str, period: str = "6mo", interval: str = "1d") -> str:
    """
    Fetch stock market data for a given ticker.

    Args:
        ticker: Stock ticker symbol
        period: Data period
        interval: Data interval

    Returns:
        String description of the data
    """
    data_agent = get_data_agent()
    df = data_agent.fetch_stock_data(ticker, period, interval)

    if df is None or df.empty:
        return f"Failed to fetch data for {ticker}"

    latest = df.iloc[-1]
    return f"""Stock data for {ticker}:
    - Period: {period}
    - Records: {len(df)}
    - Latest close: ${latest['close']:.2f}
    - Latest volume: {int(latest['volume']):,}
    - Date range: {df.index[0].date()} to {df.index[-1].date()}
    """


def get_latest_price(ticker: str) -> str:
    """
    Get the latest stock price.

    Args:
        ticker: Stock ticker symbol

    Returns:
        String with price information
    """
    data_agent = get_data_agent()
    price = data_agent.get_latest_price(ticker)

    if price is None:
        return f"Failed to fetch price for {ticker}"

    return f"Latest price for {ticker}: ${price:.2f}"


def analyze_technical_indicators(ticker: str, period: str = "6mo") -> str:
    """
    Perform technical analysis on a stock.

    Args:
        ticker: Stock ticker symbol
        period: Analysis period

    Returns:
        String with technical analysis summary
    """
    data_agent = get_data_agent()
    feature_agent = get_graph_feature_agent()

    # Fetch data
    df = data_agent.fetch_stock_data(ticker, period, "1d")
    if df is None or df.empty:
        return f"Failed to fetch data for technical analysis of {ticker}"

    # Extract features
    features = feature_agent.extract_features(df, ticker)

    # Format summary
    summary = f"""Technical Analysis for {ticker}:

Trend: {features.get('trend', 'unknown').upper()}
Momentum: {features.get('momentum', 'unknown')}
Pattern: {features.get('pattern', 'none')}

Key Indicators:
- RSI: {features.get('rsi', 0):.2f} ({features.get('rsi_signal', 'neutral')})
- MACD: {features.get('macd_signal', 'unknown')}
- Volatility: {features.get('volatility_level', 'unknown')}
- Volume Confirmation: {features.get('volume_confirmation', False)}

Price: ${features.get('latest_price', 0):.2f}
Support: ${features.get('support_level', 0):.2f}
Resistance: ${features.get('resistance_level', 0):.2f}
"""
    return summary


# Create LangChain tools
stock_data_tool = Tool(
    name="get_stock_data",
    description="Fetch historical stock market data (OHLCV) for a given ticker symbol. Use this to get price history, volume, and other market data.",
    func=lambda x: get_stock_data(**eval(x) if isinstance(x, str) and x.startswith('{') else {'ticker': x}),
)

stock_price_tool = Tool(
    name="get_latest_price",
    description="Get the current/latest stock price for a ticker symbol. Quick way to check current price.",
    func=get_latest_price,
)

technical_analysis_tool = Tool(
    name="analyze_technical_indicators",
    description="Perform comprehensive technical analysis including RSI, MACD, moving averages, support/resistance, and trend analysis. Returns a detailed technical summary.",
    func=lambda x: analyze_technical_indicators(**eval(x) if isinstance(x, str) and x.startswith('{') else {'ticker': x}),
)


def get_finance_tools():
    """
    Get all finance tools as a list.

    Returns:
        List of LangChain Tool objects
    """
    return [
        stock_data_tool,
        stock_price_tool,
        technical_analysis_tool,
    ]
