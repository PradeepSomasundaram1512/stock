"""
Fundamental Analysis Agent - Analyzes company financials and valuation.
"""

import logging
from typing import Dict, Any, Optional
import yfinance as yf

logger = logging.getLogger(__name__)


class FundamentalAgent:
    """Analyzes fundamental financial data for stocks."""

    def __init__(self):
        """Initialize the Fundamental Agent."""
        pass

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Get fundamental financial data for a stock.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with fundamental metrics
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            fundamentals = {
                # Valuation metrics
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', None),
                'forward_pe': info.get('forwardPE', None),
                'peg_ratio': info.get('pegRatio', None),
                'price_to_book': info.get('priceToBook', None),
                'price_to_sales': info.get('priceToSalesTrailing12Months', None),

                # Profitability
                'profit_margin': info.get('profitMargins', None),
                'operating_margin': info.get('operatingMargins', None),
                'return_on_equity': info.get('returnOnEquity', None),
                'return_on_assets': info.get('returnOnAssets', None),

                # Financial health
                'current_ratio': info.get('currentRatio', None),
                'debt_to_equity': info.get('debtToEquity', None),
                'free_cashflow': info.get('freeCashflow', None),

                # Growth
                'revenue_growth': info.get('revenueGrowth', None),
                'earnings_growth': info.get('earningsGrowth', None),

                # Dividends
                'dividend_yield': info.get('dividendYield', None),
                'payout_ratio': info.get('payoutRatio', None),

                # Analyst ratings
                'target_mean_price': info.get('targetMeanPrice', None),
                'recommendation': info.get('recommendationKey', None),
                'number_of_analyst_opinions': info.get('numberOfAnalystOpinions', 0),

                # Company info
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'company_name': info.get('longName', ticker)
            }

            # Calculate derived metrics
            fundamentals['valuation_score'] = self._calculate_valuation_score(fundamentals)
            fundamentals['health_score'] = self._calculate_health_score(fundamentals)
            fundamentals['growth_score'] = self._calculate_growth_score(fundamentals)

            logger.info(f"Retrieved fundamentals for {ticker}")
            return fundamentals

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return {
                'error': str(e),
                'valuation_score': 0.5,
                'health_score': 0.5,
                'growth_score': 0.5,
                'company_name': ticker
            }

    def _calculate_valuation_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate valuation score (0-1).
        Lower P/E, P/B, P/S = better value = higher score.
        """
        score = 0.5  # Neutral default

        try:
            pe = data.get('pe_ratio')
            pb = data.get('price_to_book')
            ps = data.get('price_to_sales')

            scores = []

            # P/E ratio scoring (lower is better, typical range 10-30)
            if pe is not None and pe > 0:
                if pe < 15:
                    scores.append(0.8)
                elif pe < 25:
                    scores.append(0.6)
                elif pe < 35:
                    scores.append(0.4)
                else:
                    scores.append(0.2)

            # P/B ratio scoring (lower is better, typical range 1-5)
            if pb is not None and pb > 0:
                if pb < 1.5:
                    scores.append(0.8)
                elif pb < 3:
                    scores.append(0.6)
                elif pb < 5:
                    scores.append(0.4)
                else:
                    scores.append(0.2)

            # P/S ratio scoring (lower is better, typical range 1-5)
            if ps is not None and ps > 0:
                if ps < 2:
                    scores.append(0.8)
                elif ps < 4:
                    scores.append(0.6)
                elif ps < 7:
                    scores.append(0.4)
                else:
                    scores.append(0.2)

            if scores:
                score = sum(scores) / len(scores)

        except Exception as e:
            logger.debug(f"Error calculating valuation score: {e}")

        return round(score, 2)

    def _calculate_health_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate financial health score (0-1).
        Better margins, ROE, current ratio = higher score.
        """
        score = 0.5

        try:
            scores = []

            # Profit margin (higher is better)
            margin = data.get('profit_margin')
            if margin is not None:
                if margin > 0.2:
                    scores.append(0.9)
                elif margin > 0.1:
                    scores.append(0.7)
                elif margin > 0.05:
                    scores.append(0.5)
                elif margin > 0:
                    scores.append(0.3)
                else:
                    scores.append(0.1)

            # ROE (higher is better)
            roe = data.get('return_on_equity')
            if roe is not None:
                if roe > 0.2:
                    scores.append(0.9)
                elif roe > 0.15:
                    scores.append(0.7)
                elif roe > 0.1:
                    scores.append(0.5)
                elif roe > 0:
                    scores.append(0.3)
                else:
                    scores.append(0.1)

            # Current ratio (1.5-3 is good)
            current = data.get('current_ratio')
            if current is not None:
                if 1.5 <= current <= 3:
                    scores.append(0.8)
                elif 1 <= current < 1.5 or 3 < current <= 4:
                    scores.append(0.6)
                else:
                    scores.append(0.4)

            # Debt to equity (lower is better)
            debt = data.get('debt_to_equity')
            if debt is not None:
                if debt < 50:
                    scores.append(0.8)
                elif debt < 100:
                    scores.append(0.6)
                elif debt < 150:
                    scores.append(0.4)
                else:
                    scores.append(0.2)

            if scores:
                score = sum(scores) / len(scores)

        except Exception as e:
            logger.debug(f"Error calculating health score: {e}")

        return round(score, 2)

    def _calculate_growth_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate growth score (0-1).
        Higher revenue/earnings growth = higher score.
        """
        score = 0.5

        try:
            scores = []

            # Revenue growth
            rev_growth = data.get('revenue_growth')
            if rev_growth is not None:
                if rev_growth > 0.2:
                    scores.append(0.9)
                elif rev_growth > 0.1:
                    scores.append(0.7)
                elif rev_growth > 0.05:
                    scores.append(0.6)
                elif rev_growth > 0:
                    scores.append(0.4)
                else:
                    scores.append(0.2)

            # Earnings growth
            earn_growth = data.get('earnings_growth')
            if earn_growth is not None:
                if earn_growth > 0.2:
                    scores.append(0.9)
                elif earn_growth > 0.1:
                    scores.append(0.7)
                elif earn_growth > 0.05:
                    scores.append(0.6)
                elif earn_growth > 0:
                    scores.append(0.4)
                else:
                    scores.append(0.2)

            if scores:
                score = sum(scores) / len(scores)

        except Exception as e:
            logger.debug(f"Error calculating growth score: {e}")

        return round(score, 2)

    def get_analyst_consensus(self, ticker: str) -> Dict[str, Any]:
        """
        Get analyst recommendations and price targets.

        Args:
            ticker: Stock ticker

        Returns:
            Analyst consensus data
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                'recommendation': info.get('recommendationKey', 'none'),
                'target_price': info.get('targetMeanPrice', None),
                'analyst_count': info.get('numberOfAnalystOpinions', 0),
                'current_price': info.get('currentPrice', None)
            }

        except Exception as e:
            logger.error(f"Error fetching analyst data for {ticker}: {e}")
            return {
                'recommendation': 'none',
                'target_price': None,
                'analyst_count': 0
            }


# Singleton instance
_fundamental_agent_instance = None


def get_fundamental_agent() -> FundamentalAgent:
    """Get or create the FundamentalAgent singleton."""
    global _fundamental_agent_instance
    if _fundamental_agent_instance is None:
        _fundamental_agent_instance = FundamentalAgent()
    return _fundamental_agent_instance
