"""
Fintel.io Integration Tool

Provides institutional-grade data for stock analysis:
- Institutional Ownership (13F filings)
- Insider Trading (Form 4)
- Short Interest Data
- Hedge Fund Holdings
- Options Flow
- SEC Filings

API Documentation: https://fintel.io/doc/api
"""

import os
import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Fintel.io API Configuration
FINTEL_API_KEY = os.getenv('FINTEL_API_KEY', '')
FINTEL_BASE_URL = 'https://api.fintel.io/web/us'


class FintelClient:
    """Client for Fintel.io API interactions."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or FINTEL_API_KEY
        self.base_url = FINTEL_BASE_URL
        self.headers = {
            'X-API-KEY': self.api_key,
            'Accept': 'application/json'
        }

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Fintel.io."""
        if not self.api_key:
            logger.warning("Fintel API key not configured")
            return None

        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fintel API error: {str(e)}")
            return None

    # =========================================================================
    # INSTITUTIONAL OWNERSHIP (13F Filings)
    # =========================================================================

    def get_institutional_ownership(self, ticker: str) -> Optional[Dict]:
        """
        Get institutional ownership data from 13F filings.

        Returns:
            - Total institutional ownership percentage
            - Number of institutional holders
            - Recent changes in ownership
            - Top institutional holders
        """
        data = self._make_request(f"so/i/{ticker.lower()}")
        if not data:
            return None

        return {
            'ticker': ticker,
            'institutional_ownership_pct': data.get('institutionalOwnershipPct', 0),
            'num_institutional_holders': data.get('numInstitutionalHolders', 0),
            'shares_held_institutional': data.get('sharesHeldInstitutional', 0),
            'ownership_change_3m': data.get('ownershipChange3m', 0),
            'ownership_change_6m': data.get('ownershipChange6m', 0),
            'top_holders': data.get('topHolders', [])[:10]
        }

    def get_institutional_ownership_history(self, ticker: str) -> Optional[List[Dict]]:
        """Get historical institutional ownership data."""
        data = self._make_request(f"so/i/h/{ticker.lower()}")
        return data if data else None

    # =========================================================================
    # INSIDER TRADING (Form 4 Filings)
    # =========================================================================

    def get_insider_trades(self, ticker: str, days: int = 90) -> Optional[Dict]:
        """
        Get insider trading activity from Form 4 filings.

        Returns:
            - Recent insider buys/sells
            - Net insider sentiment
            - Notable insider transactions
        """
        data = self._make_request(f"n/i/{ticker.lower()}")
        if not data:
            return None

        trades = data.get('trades', [])

        # Calculate insider sentiment
        total_buys = sum(1 for t in trades if t.get('transactionType') == 'Buy')
        total_sells = sum(1 for t in trades if t.get('transactionType') == 'Sell')

        buy_value = sum(t.get('value', 0) for t in trades if t.get('transactionType') == 'Buy')
        sell_value = sum(t.get('value', 0) for t in trades if t.get('transactionType') == 'Sell')

        # Determine sentiment
        if total_buys > total_sells * 1.5:
            sentiment = 'BULLISH'
        elif total_sells > total_buys * 1.5:
            sentiment = 'BEARISH'
        else:
            sentiment = 'NEUTRAL'

        return {
            'ticker': ticker,
            'total_trades': len(trades),
            'total_buys': total_buys,
            'total_sells': total_sells,
            'buy_value': buy_value,
            'sell_value': sell_value,
            'net_value': buy_value - sell_value,
            'insider_sentiment': sentiment,
            'recent_trades': trades[:10]
        }

    def get_insider_roster(self, ticker: str) -> Optional[List[Dict]]:
        """Get list of company insiders."""
        data = self._make_request(f"n/i/roster/{ticker.lower()}")
        return data if data else None

    # =========================================================================
    # SHORT INTEREST DATA
    # =========================================================================

    def get_short_interest(self, ticker: str) -> Optional[Dict]:
        """
        Get short interest data.

        Returns:
            - Short interest ratio
            - Short percent of float
            - Days to cover
            - Short squeeze potential
        """
        data = self._make_request(f"ss/us/{ticker.lower()}")
        if not data:
            return None

        short_pct_float = data.get('shortPercentOfFloat', 0)
        days_to_cover = data.get('daysToCover', 0)

        # Calculate short squeeze potential
        if short_pct_float > 20 and days_to_cover > 5:
            squeeze_potential = 'HIGH'
        elif short_pct_float > 10 and days_to_cover > 3:
            squeeze_potential = 'MEDIUM'
        else:
            squeeze_potential = 'LOW'

        return {
            'ticker': ticker,
            'short_interest': data.get('shortInterest', 0),
            'short_pct_float': short_pct_float,
            'short_pct_outstanding': data.get('shortPercentOfOutstanding', 0),
            'days_to_cover': days_to_cover,
            'short_interest_change': data.get('shortInterestChange', 0),
            'squeeze_potential': squeeze_potential,
            'updated_date': data.get('settlementDate', '')
        }

    def get_short_volume(self, ticker: str) -> Optional[Dict]:
        """Get daily short volume data."""
        data = self._make_request(f"sv/us/{ticker.lower()}")
        if not data:
            return None

        volumes = data.get('data', [])
        if volumes:
            latest = volumes[0]
            avg_short_vol_ratio = sum(v.get('shortVolRatio', 0) for v in volumes[:20]) / min(20, len(volumes))

            return {
                'ticker': ticker,
                'short_volume': latest.get('shortVolume', 0),
                'total_volume': latest.get('totalVolume', 0),
                'short_vol_ratio': latest.get('shortVolRatio', 0),
                'avg_short_vol_ratio_20d': avg_short_vol_ratio,
                'date': latest.get('date', '')
            }
        return None

    # =========================================================================
    # HEDGE FUND HOLDINGS
    # =========================================================================

    def get_hedge_fund_holdings(self, ticker: str) -> Optional[Dict]:
        """
        Get hedge fund holdings data.

        Returns:
            - Number of hedge funds holding
            - Notable hedge fund positions
            - Changes in hedge fund ownership
        """
        data = self._make_request(f"so/hf/{ticker.lower()}")
        if not data:
            return None

        return {
            'ticker': ticker,
            'num_hedge_funds': data.get('numHedgeFunds', 0),
            'hedge_fund_ownership_pct': data.get('hedgeFundOwnershipPct', 0),
            'shares_held_hf': data.get('sharesHeldHF', 0),
            'hf_ownership_change_qoq': data.get('ownershipChangeQoQ', 0),
            'top_hedge_funds': data.get('topHolders', [])[:10]
        }

    # =========================================================================
    # OPTIONS FLOW
    # =========================================================================

    def get_options_flow(self, ticker: str) -> Optional[Dict]:
        """
        Get unusual options activity.

        Returns:
            - Unusual options trades
            - Put/Call ratio
            - Large block trades
        """
        data = self._make_request(f"of/{ticker.lower()}")
        if not data:
            return None

        flows = data.get('data', [])

        # Analyze options sentiment
        calls = [f for f in flows if f.get('optionType') == 'Call']
        puts = [f for f in flows if f.get('optionType') == 'Put']

        call_premium = sum(f.get('premium', 0) for f in calls)
        put_premium = sum(f.get('premium', 0) for f in puts)

        if call_premium > put_premium * 1.5:
            options_sentiment = 'BULLISH'
        elif put_premium > call_premium * 1.5:
            options_sentiment = 'BEARISH'
        else:
            options_sentiment = 'NEUTRAL'

        return {
            'ticker': ticker,
            'total_unusual_trades': len(flows),
            'call_trades': len(calls),
            'put_trades': len(puts),
            'call_premium': call_premium,
            'put_premium': put_premium,
            'put_call_ratio': put_premium / call_premium if call_premium > 0 else 0,
            'options_sentiment': options_sentiment,
            'recent_flows': flows[:10]
        }

    # =========================================================================
    # SEC FILINGS
    # =========================================================================

    def get_sec_filings(self, ticker: str, filing_type: str = None) -> Optional[List[Dict]]:
        """
        Get SEC filings.

        Args:
            ticker: Stock symbol
            filing_type: Optional filter (10-K, 10-Q, 8-K, etc.)
        """
        endpoint = f"sf/{ticker.lower()}"
        params = {'type': filing_type} if filing_type else None
        data = self._make_request(endpoint, params)
        return data if data else None

    # =========================================================================
    # POLITICAL TRADING (Congress/Senate)
    # =========================================================================

    def get_political_trades(self, ticker: str) -> Optional[Dict]:
        """Get political trading activity (Congress/Senate)."""
        data = self._make_request(f"pt/{ticker.lower()}")
        if not data:
            return None

        trades = data.get('trades', [])

        buys = [t for t in trades if 'Purchase' in t.get('transactionType', '')]
        sells = [t for t in trades if 'Sale' in t.get('transactionType', '')]

        return {
            'ticker': ticker,
            'total_political_trades': len(trades),
            'political_buys': len(buys),
            'political_sells': len(sells),
            'recent_trades': trades[:10]
        }

    # =========================================================================
    # COMPREHENSIVE ANALYSIS
    # =========================================================================

    def get_comprehensive_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive institutional analysis for a stock.
        Combines all available Fintel data sources.
        """
        logger.info(f"Fetching comprehensive Fintel analysis for {ticker}")

        analysis = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'institutional_ownership': None,
            'insider_trading': None,
            'short_interest': None,
            'short_volume': None,
            'hedge_fund_holdings': None,
            'options_flow': None,
            'political_trades': None,
            'overall_sentiment': 'NEUTRAL',
            'signals': []
        }

        # Gather all data
        analysis['institutional_ownership'] = self.get_institutional_ownership(ticker)
        analysis['insider_trading'] = self.get_insider_trades(ticker)
        analysis['short_interest'] = self.get_short_interest(ticker)
        analysis['short_volume'] = self.get_short_volume(ticker)
        analysis['hedge_fund_holdings'] = self.get_hedge_fund_holdings(ticker)
        analysis['options_flow'] = self.get_options_flow(ticker)
        analysis['political_trades'] = self.get_political_trades(ticker)

        # Generate signals and overall sentiment
        bullish_signals = 0
        bearish_signals = 0

        # Institutional ownership signals
        if analysis['institutional_ownership']:
            io = analysis['institutional_ownership']
            if io.get('ownership_change_3m', 0) > 5:
                analysis['signals'].append('Institutional buying (ownership up >5% in 3mo)')
                bullish_signals += 1
            elif io.get('ownership_change_3m', 0) < -5:
                analysis['signals'].append('Institutional selling (ownership down >5% in 3mo)')
                bearish_signals += 1

        # Insider trading signals
        if analysis['insider_trading']:
            it = analysis['insider_trading']
            if it.get('insider_sentiment') == 'BULLISH':
                analysis['signals'].append('Insider buying activity')
                bullish_signals += 2  # Insiders know best
            elif it.get('insider_sentiment') == 'BEARISH':
                analysis['signals'].append('Insider selling activity')
                bearish_signals += 2

        # Short interest signals
        if analysis['short_interest']:
            si = analysis['short_interest']
            if si.get('squeeze_potential') == 'HIGH':
                analysis['signals'].append(f"High short squeeze potential ({si.get('short_pct_float', 0):.1f}% short)")
                bullish_signals += 1
            elif si.get('short_pct_float', 0) > 20:
                analysis['signals'].append(f"High short interest ({si.get('short_pct_float', 0):.1f}% of float)")
                bearish_signals += 1

        # Hedge fund signals
        if analysis['hedge_fund_holdings']:
            hf = analysis['hedge_fund_holdings']
            if hf.get('hf_ownership_change_qoq', 0) > 10:
                analysis['signals'].append('Hedge funds increasing positions')
                bullish_signals += 1
            elif hf.get('hf_ownership_change_qoq', 0) < -10:
                analysis['signals'].append('Hedge funds reducing positions')
                bearish_signals += 1

        # Options flow signals
        if analysis['options_flow']:
            of = analysis['options_flow']
            if of.get('options_sentiment') == 'BULLISH':
                analysis['signals'].append('Bullish options flow')
                bullish_signals += 1
            elif of.get('options_sentiment') == 'BEARISH':
                analysis['signals'].append('Bearish options flow')
                bearish_signals += 1

        # Determine overall sentiment
        if bullish_signals > bearish_signals + 1:
            analysis['overall_sentiment'] = 'BULLISH'
        elif bearish_signals > bullish_signals + 1:
            analysis['overall_sentiment'] = 'BEARISH'
        else:
            analysis['overall_sentiment'] = 'NEUTRAL'

        analysis['bullish_signals'] = bullish_signals
        analysis['bearish_signals'] = bearish_signals

        return analysis


# =========================================================================
# TOOL FUNCTIONS (For LangChain Integration)
# =========================================================================

def get_fintel_analysis(ticker: str) -> Dict[str, Any]:
    """
    LangChain tool function to get Fintel.io analysis.

    Args:
        ticker: Stock symbol (e.g., 'AAPL')

    Returns:
        Comprehensive institutional analysis
    """
    client = FintelClient()
    return client.get_comprehensive_analysis(ticker)


def get_institutional_data(ticker: str) -> Dict[str, Any]:
    """Get institutional ownership data for a stock."""
    client = FintelClient()
    return client.get_institutional_ownership(ticker)


def get_insider_data(ticker: str) -> Dict[str, Any]:
    """Get insider trading data for a stock."""
    client = FintelClient()
    return client.get_insider_trades(ticker)


def get_short_data(ticker: str) -> Dict[str, Any]:
    """Get short interest data for a stock."""
    client = FintelClient()
    return {
        'short_interest': client.get_short_interest(ticker),
        'short_volume': client.get_short_volume(ticker)
    }


def format_fintel_report(analysis: Dict[str, Any]) -> str:
    """Format Fintel analysis as readable report."""
    if not analysis:
        return "Fintel data not available"

    report = []
    report.append(f"\n{'='*60}")
    report.append(f"FINTEL.IO INSTITUTIONAL ANALYSIS - {analysis['ticker']}")
    report.append(f"{'='*60}\n")

    # Overall Sentiment
    sentiment = analysis.get('overall_sentiment', 'NEUTRAL')
    sentiment_emoji = '🟢' if sentiment == 'BULLISH' else '🔴' if sentiment == 'BEARISH' else '🟡'
    report.append(f"Overall Sentiment: {sentiment_emoji} {sentiment}")
    report.append(f"Bullish Signals: {analysis.get('bullish_signals', 0)}")
    report.append(f"Bearish Signals: {analysis.get('bearish_signals', 0)}")

    # Key Signals
    if analysis.get('signals'):
        report.append(f"\nKey Signals:")
        for signal in analysis['signals']:
            report.append(f"  • {signal}")

    # Institutional Ownership
    io = analysis.get('institutional_ownership')
    if io:
        report.append(f"\n📊 Institutional Ownership:")
        report.append(f"  • Ownership: {io.get('institutional_ownership_pct', 0):.1f}%")
        report.append(f"  • # of Holders: {io.get('num_institutional_holders', 0):,}")
        report.append(f"  • 3-Month Change: {io.get('ownership_change_3m', 0):+.1f}%")

    # Insider Trading
    it = analysis.get('insider_trading')
    if it:
        report.append(f"\n👔 Insider Trading:")
        report.append(f"  • Sentiment: {it.get('insider_sentiment', 'N/A')}")
        report.append(f"  • Buys: {it.get('total_buys', 0)} | Sells: {it.get('total_sells', 0)}")
        report.append(f"  • Net Value: ${it.get('net_value', 0):,.0f}")

    # Short Interest
    si = analysis.get('short_interest')
    if si:
        report.append(f"\n📉 Short Interest:")
        report.append(f"  • Short % of Float: {si.get('short_pct_float', 0):.1f}%")
        report.append(f"  • Days to Cover: {si.get('days_to_cover', 0):.1f}")
        report.append(f"  • Squeeze Potential: {si.get('squeeze_potential', 'N/A')}")

    # Hedge Funds
    hf = analysis.get('hedge_fund_holdings')
    if hf:
        report.append(f"\n🏦 Hedge Fund Holdings:")
        report.append(f"  • # of Hedge Funds: {hf.get('num_hedge_funds', 0)}")
        report.append(f"  • HF Ownership: {hf.get('hedge_fund_ownership_pct', 0):.1f}%")
        report.append(f"  • QoQ Change: {hf.get('hf_ownership_change_qoq', 0):+.1f}%")

    # Options Flow
    of = analysis.get('options_flow')
    if of:
        report.append(f"\n📈 Options Flow:")
        report.append(f"  • Sentiment: {of.get('options_sentiment', 'N/A')}")
        report.append(f"  • Unusual Trades: {of.get('total_unusual_trades', 0)}")
        report.append(f"  • Put/Call Ratio: {of.get('put_call_ratio', 0):.2f}")

    report.append(f"\n{'='*60}\n")

    return '\n'.join(report)


# =========================================================================
# CLI TEST
# =========================================================================

if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'

    print(f"\nFetching Fintel.io data for {ticker}...")

    client = FintelClient()
    analysis = client.get_comprehensive_analysis(ticker)

    print(format_fintel_report(analysis))
