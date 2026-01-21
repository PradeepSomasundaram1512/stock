"""
Data Agent: Handles fetching stock market data from Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataAgent:
    """Agent responsible for fetching and validating stock market data."""

    def __init__(self):
        """Initialize the Data Agent."""
        self.cache = {}

    def fetch_stock_data(
        self,
        ticker: str,
        period: str = "6mo",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch stock data from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        cache_key = f"{ticker}_{period}_{interval}"

        # Check cache
        if cache_key in self.cache:
            logger.info(f"Using cached data for {ticker}")
            return self.cache[cache_key]

        try:
            logger.info(f"Fetching data for {ticker} (period={period}, interval={interval})")

            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if df.empty:
                logger.error(f"No data returned for {ticker}")
                return None

            # Clean data
            df = self._clean_data(df)

            # Cache the result
            self.cache[cache_key] = df

            logger.info(f"Successfully fetched {len(df)} records for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def get_stock_info(self, ticker: str) -> Optional[dict]:
        """
        Get stock metadata and company information.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with stock info or None if fetch fails
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Extract key information
            return {
                "symbol": ticker,
                "name": info.get("longName", "Unknown"),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", 0),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", "Unknown"),
            }

        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {str(e)}")
            return None

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate stock data.

        Args:
            df: Raw DataFrame from yfinance

        Returns:
            Cleaned DataFrame
        """
        # Remove any rows with NaN values in critical columns
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])

        # Ensure proper column names (yfinance sometimes capitalizes)
        df.columns = df.columns.str.lower()

        # Sort by date
        df = df.sort_index()

        # Add basic validation
        if len(df) == 0:
            logger.warning("DataFrame is empty after cleaning")

        return df

    def get_latest_price(self, ticker: str) -> Optional[float]:
        """
        Get the latest closing price for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Latest closing price or None
        """
        df = self.fetch_stock_data(ticker, period="5d", interval="1d")
        if df is not None and not df.empty:
            return float(df['close'].iloc[-1])
        return None

    def calculate_returns(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate daily returns from price data.

        Args:
            df: DataFrame with 'close' column

        Returns:
            Series of daily returns
        """
        return df['close'].pct_change()

    def clear_cache(self):
        """Clear the data cache."""
        self.cache.clear()
        logger.info("Data cache cleared")


# Singleton instance
_data_agent_instance = None


def get_data_agent() -> DataAgent:
    """Get or create the DataAgent singleton."""
    global _data_agent_instance
    if _data_agent_instance is None:
        _data_agent_instance = DataAgent()
    return _data_agent_instance
