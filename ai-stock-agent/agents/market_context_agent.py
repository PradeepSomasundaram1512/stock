"""
Market Context Agent - Analyzes broader market conditions and economic indicators.
"""

import logging
from typing import Dict, Any, Optional
import yfinance as yf
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketContextAgent:
    """Analyzes market indices and economic context."""

    def __init__(self):
        """Initialize the Market Context Agent."""
        self.indices = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ',
            'DIA': 'Dow Jones',
            'IWM': 'Russell 2000'
        }

    def get_market_context(self) -> Dict[str, Any]:
        """
        Get current market conditions and trends.

        Returns:
            Market context data
        """
        context = {
            'market_trend': 'neutral',
            'market_strength': 0.5,
            'indices': {},
            'sector_performance': {},
            'volatility_index': None
        }

        try:
            # Get major indices performance
            for ticker, name in self.indices.items():
                context['indices'][name] = self._get_index_performance(ticker)

            # Get VIX (volatility index)
            context['volatility_index'] = self._get_vix()

            # Calculate overall market trend
            context['market_trend'] = self._calculate_market_trend(context['indices'])
            context['market_strength'] = self._calculate_market_strength(context['indices'])

            logger.info("Retrieved market context")

        except Exception as e:
            logger.error(f"Error getting market context: {str(e)}")

        return context

    def _get_index_performance(self, ticker: str) -> Dict[str, Any]:
        """Get performance data for an index."""
        try:
            index = yf.Ticker(ticker)
            hist = index.history(period='1mo')

            if hist.empty:
                return {'error': 'No data'}

            current_price = hist['Close'].iloc[-1]
            start_price = hist['Close'].iloc[0]
            month_change = ((current_price - start_price) / start_price) * 100

            # Get 5-day trend
            if len(hist) >= 5:
                week_start = hist['Close'].iloc[-5]
                week_change = ((current_price - week_start) / week_start) * 100
            else:
                week_change = month_change

            return {
                'current_price': round(current_price, 2),
                'month_change': round(month_change, 2),
                'week_change': round(week_change, 2),
                'trend': 'bullish' if month_change > 2 else 'bearish' if month_change < -2 else 'neutral'
            }

        except Exception as e:
            logger.debug(f"Error getting {ticker} performance: {e}")
            return {'error': str(e)}

    def _get_vix(self) -> Optional[float]:
        """Get current VIX (volatility) level."""
        try:
            vix = yf.Ticker('^VIX')
            hist = vix.history(period='1d')

            if not hist.empty:
                current_vix = hist['Close'].iloc[-1]
                return round(current_vix, 2)

        except Exception as e:
            logger.debug(f"Error getting VIX: {e}")

        return None

    def _calculate_market_trend(self, indices: Dict[str, Dict[str, Any]]) -> str:
        """
        Calculate overall market trend from indices.

        Returns:
            'bullish', 'neutral', or 'bearish'
        """
        bullish_count = 0
        bearish_count = 0

        for name, data in indices.items():
            if 'trend' in data:
                if data['trend'] == 'bullish':
                    bullish_count += 1
                elif data['trend'] == 'bearish':
                    bearish_count += 1

        if bullish_count > bearish_count + 1:
            return 'bullish'
        elif bearish_count > bullish_count + 1:
            return 'bearish'
        else:
            return 'neutral'

    def _calculate_market_strength(self, indices: Dict[str, Dict[str, Any]]) -> float:
        """
        Calculate market strength score (0-1).

        Returns:
            Market strength score
        """
        changes = []

        for name, data in indices.items():
            if 'month_change' in data:
                changes.append(data['month_change'])

        if not changes:
            return 0.5

        avg_change = sum(changes) / len(changes)

        # Map to 0-1 scale (-10% to +10% range)
        strength = (avg_change + 10) / 20
        return max(0.0, min(1.0, strength))

    def get_sector_context(self, sector: str) -> Dict[str, Any]:
        """
        Get performance context for a specific sector.

        Args:
            sector: Sector name (e.g., 'Technology', 'Healthcare')

        Returns:
            Sector performance data
        """
        # Sector ETF mapping
        sector_etfs = {
            'Technology': 'XLK',
            'Healthcare': 'XLV',
            'Financials': 'XLF',
            'Energy': 'XLE',
            'Consumer Discretionary': 'XLY',
            'Consumer Staples': 'XLP',
            'Industrials': 'XLI',
            'Materials': 'XLB',
            'Real Estate': 'XLRE',
            'Utilities': 'XLU',
            'Communication Services': 'XLC'
        }

        etf_ticker = sector_etfs.get(sector)

        if not etf_ticker:
            return {
                'sector': sector,
                'performance': 'unknown',
                'relative_strength': 0.5
            }

        try:
            # Get sector ETF performance
            sector_data = self._get_index_performance(etf_ticker)

            # Get S&P 500 for comparison
            spy_data = self._get_index_performance('SPY')

            relative_strength = 0.5
            if 'month_change' in sector_data and 'month_change' in spy_data:
                # Calculate relative strength vs market
                outperformance = sector_data['month_change'] - spy_data['month_change']
                relative_strength = (outperformance + 5) / 10  # Map -5 to +5 to 0-1
                relative_strength = max(0.0, min(1.0, relative_strength))

            return {
                'sector': sector,
                'performance': sector_data.get('trend', 'neutral'),
                'month_change': sector_data.get('month_change', 0),
                'relative_strength': round(relative_strength, 2),
                'vs_market': round(sector_data.get('month_change', 0) - spy_data.get('month_change', 0), 2)
            }

        except Exception as e:
            logger.debug(f"Error getting sector context for {sector}: {e}")
            return {
                'sector': sector,
                'performance': 'unknown',
                'relative_strength': 0.5
            }

    def interpret_context(self, market_data: Dict[str, Any], sector: str = None) -> str:
        """
        Generate human-readable market context interpretation.

        Args:
            market_data: Market context data
            sector: Optional sector for sector-specific context

        Returns:
            Interpretation string
        """
        interpretations = []

        # Market trend
        trend = market_data.get('market_trend', 'neutral')
        strength = market_data.get('market_strength', 0.5)

        if trend == 'bullish':
            interpretations.append(f"📈 Market is bullish with {strength*100:.0f}% strength")
        elif trend == 'bearish':
            interpretations.append(f"📉 Market is bearish with {(1-strength)*100:.0f}% weakness")
        else:
            interpretations.append("➡️ Market is neutral/mixed")

        # VIX
        vix = market_data.get('volatility_index')
        if vix:
            if vix > 25:
                interpretations.append(f"⚠️ High volatility (VIX: {vix})")
            elif vix < 15:
                interpretations.append(f"✅ Low volatility (VIX: {vix})")
            else:
                interpretations.append(f"📊 Moderate volatility (VIX: {vix})")

        return " | ".join(interpretations)


# Singleton instance
_market_context_agent_instance = None


def get_market_context_agent() -> MarketContextAgent:
    """Get or create the MarketContextAgent singleton."""
    global _market_context_agent_instance
    if _market_context_agent_instance is None:
        _market_context_agent_instance = MarketContextAgent()
    return _market_context_agent_instance
