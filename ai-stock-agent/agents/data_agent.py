"""
Data Agent: Handles fetching stock market data from Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataAgent:
    """Agent responsible for fetching and validating stock market data."""

    def __init__(self, cache_ttl_minutes: int = 15):
        """
        Initialize the Data Agent.

        Args:
            cache_ttl_minutes: Cache time-to-live in minutes (default: 15 minutes)
        """
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        logger.info(f"DataAgent initialized with {cache_ttl_minutes} minute cache TTL")

    def fetch_stock_data(
        self,
        ticker: str,
        period: str = "6mo",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch stock data from Yahoo Finance with TTL caching.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        cache_key = f"{ticker}_{period}_{interval}"
        now = datetime.now()

        # Check cache and TTL
        if cache_key in self.cache:
            cache_age = now - self.cache_timestamps[cache_key]
            if cache_age < self.cache_ttl:
                logger.info(f"Using cached data for {ticker} (age: {cache_age.seconds}s)")
                return self.cache[cache_key]
            else:
                logger.info(f"Cache expired for {ticker} (age: {cache_age.seconds}s > {self.cache_ttl.seconds}s)")
                # Remove expired cache
                del self.cache[cache_key]
                del self.cache_timestamps[cache_key]

        try:
            logger.info(f"Fetching FRESH data for {ticker} (period={period}, interval={interval})")

            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if df.empty:
                logger.error(f"No data returned for {ticker}")
                return None

            # Clean data
            df = self._clean_data(df)

            # Cache the result with timestamp
            self.cache[cache_key] = df
            self.cache_timestamps[cache_key] = now

            logger.info(f"Successfully fetched {len(df)} records for {ticker} (latest price: ${df['close'].iloc[-1]:.2f})")
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
        """Clear the data cache and timestamps."""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Data cache cleared")

    def expire_cache(self):
        """Manually expire all cached data (force refresh on next fetch)."""
        expired_count = len(self.cache)
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info(f"Manually expired {expired_count} cache entries - next fetch will get fresh data")

    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging."""
        now = datetime.now()
        stats = {
            "total_cached": len(self.cache),
            "cache_ttl_minutes": self.cache_ttl.total_seconds() / 60,
            "entries": []
        }
        for key, timestamp in self.cache_timestamps.items():
            age = now - timestamp
            stats["entries"].append({
                "key": key,
                "age_seconds": age.total_seconds(),
                "expired": age >= self.cache_ttl
            })
        return stats


# Singleton instance
_data_agent_instance = None


def get_data_agent() -> DataAgent:
    """Get or create the DataAgent singleton."""
    global _data_agent_instance
    if _data_agent_instance is None:
        _data_agent_instance = DataAgent()
    return _data_agent_instance
