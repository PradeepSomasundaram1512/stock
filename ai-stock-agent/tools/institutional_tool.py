"""
Institutional Data Tool (FREE VERSION)

Provides institutional-grade data using FREE sources:
- Yahoo Finance (yfinance) - Institutional holders, insider trades
- SEC EDGAR API - Direct SEC filings (13F, Form 4)
- FINRA - Short interest data

No API key required!
"""

import os
import requests
import logging
import yfinance as yf
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)


class InstitutionalDataClient:
    """Client for FREE institutional data sources."""

    def __init__(self):
        self.sec_base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': 'StockAnalysis/1.0 (contact@example.com)',
            'Accept': 'application/json'
        }

    # =========================================================================
    # YAHOO FINANCE - INSTITUTIONAL HOLDERS (FREE)
    # =========================================================================

    def get_institutional_holders(self, ticker: str) -> Optional[Dict]:
        """
        Get institutional holders from Yahoo Finance (FREE).

        Returns:
            - Major institutional holders
            - Ownership percentages
            - Recent changes
        """
        try:
            stock = yf.Ticker(ticker)

            # Get institutional holders
            inst_holders = stock.institutional_holders
            major_holders = stock.major_holders

            if inst_holders is None or inst_holders.empty:
                logger.warning(f"No institutional holder data for {ticker}")
                return None

            # Parse major holders percentages
            ownership_pct = 0
            num_institutions = 0

            if major_holders is not None and not major_holders.empty:
                for idx, row in major_holders.iterrows():
                    if 'Institutions' in str(row.iloc[1]):
                        try:
                            ownership_pct = float(str(row.iloc[0]).replace('%', ''))
                        except:
                            pass
                    if 'Number of Institutions' in str(row.iloc[1]):
                        try:
                            num_institutions = int(row.iloc[0])
                        except:
                            pass

            # Get top holders
            top_holders = []
            for idx, row in inst_holders.head(10).iterrows():
                holder = {
                    'name': row.get('Holder', 'Unknown'),
                    'shares': int(row.get('Shares', 0)),
                    'value': float(row.get('Value', 0)),
                    'pct_out': float(row.get('% Out', 0)) if '% Out' in row else 0,
                    'date_reported': str(row.get('Date Reported', ''))
                }
                top_holders.append(holder)

            return {
                'ticker': ticker,
                'institutional_ownership_pct': ownership_pct,
                'num_institutional_holders': num_institutions,
                'top_holders': top_holders,
                'data_source': 'Yahoo Finance (FREE)'
            }

        except Exception as e:
            logger.error(f"Error fetching institutional data for {ticker}: {str(e)}")
            return None

    # =========================================================================
    # YAHOO FINANCE - INSIDER TRANSACTIONS (FREE)
    # =========================================================================

    def get_insider_trades(self, ticker: str) -> Optional[Dict]:
        """
        Get insider trading activity from Yahoo Finance (FREE).

        Returns:
            - Recent insider buys/sells
            - Insider sentiment
            - Transaction details
        """
        try:
            stock = yf.Ticker(ticker)

            # Get insider transactions
            insider_txns = stock.insider_transactions
            insider_roster = stock.insider_roster_holders

            if insider_txns is None or insider_txns.empty:
                logger.warning(f"No insider transaction data for {ticker}")
                return None

            # Analyze transactions
            total_buys = 0
            total_sells = 0
            buy_value = 0
            sell_value = 0

            recent_trades = []

            for idx, row in insider_txns.head(20).iterrows():
                txn_type = str(row.get('Transaction', '')).lower()
                shares = abs(int(row.get('Shares', 0)))
                value = abs(float(row.get('Value', 0)))

                is_buy = 'buy' in txn_type or 'purchase' in txn_type or 'acquisition' in txn_type
                is_sell = 'sell' in txn_type or 'sale' in txn_type or 'disposition' in txn_type

                if is_buy:
                    total_buys += 1
                    buy_value += value
                elif is_sell:
                    total_sells += 1
                    sell_value += value

                trade = {
                    'insider': row.get('Insider', 'Unknown'),
                    'relationship': row.get('Relationship', 'Unknown'),
                    'transaction': row.get('Transaction', 'Unknown'),
                    'shares': shares,
                    'value': value,
                    'date': str(row.get('Start Date', ''))
                }
                recent_trades.append(trade)

            # Determine sentiment
            if total_buys > total_sells * 1.5:
                sentiment = 'BULLISH'
            elif total_sells > total_buys * 1.5:
                sentiment = 'BEARISH'
            else:
                sentiment = 'NEUTRAL'

            return {
                'ticker': ticker,
                'total_trades': len(recent_trades),
                'total_buys': total_buys,
                'total_sells': total_sells,
                'buy_value': buy_value,
                'sell_value': sell_value,
                'net_value': buy_value - sell_value,
                'insider_sentiment': sentiment,
                'recent_trades': recent_trades[:10],
                'data_source': 'Yahoo Finance (FREE)'
            }

        except Exception as e:
            logger.error(f"Error fetching insider data for {ticker}: {str(e)}")
            return None

    # =========================================================================
    # YAHOO FINANCE - SHORT INTEREST (FREE)
    # =========================================================================

    def get_short_interest(self, ticker: str) -> Optional[Dict]:
        """
        Get short interest data from Yahoo Finance (FREE).

        Returns:
            - Short percent of float
            - Short ratio (days to cover)
            - Short squeeze potential
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            short_pct_float = info.get('shortPercentOfFloat', 0)
            if short_pct_float:
                short_pct_float *= 100  # Convert to percentage

            short_ratio = info.get('shortRatio', 0)  # Days to cover
            shares_short = info.get('sharesShort', 0)
            shares_short_prior = info.get('sharesShortPriorMonth', 0)

            # Calculate change
            short_change = 0
            if shares_short_prior > 0:
                short_change = ((shares_short - shares_short_prior) / shares_short_prior) * 100

            # Calculate squeeze potential
            if short_pct_float > 20 and short_ratio > 5:
                squeeze_potential = 'HIGH'
            elif short_pct_float > 10 and short_ratio > 3:
                squeeze_potential = 'MEDIUM'
            else:
                squeeze_potential = 'LOW'

            return {
                'ticker': ticker,
                'short_interest': shares_short,
                'short_pct_float': short_pct_float,
                'short_ratio': short_ratio,  # Days to cover
                'shares_short_prior_month': shares_short_prior,
                'short_change_pct': short_change,
                'squeeze_potential': squeeze_potential,
                'data_source': 'Yahoo Finance (FREE)'
            }

        except Exception as e:
            logger.error(f"Error fetching short data for {ticker}: {str(e)}")
            return None

    # =========================================================================
    # YAHOO FINANCE - OPTIONS DATA (FREE)
    # =========================================================================

    def get_options_sentiment(self, ticker: str) -> Optional[Dict]:
        """
        Get options data and sentiment from Yahoo Finance (FREE).

        Returns:
            - Put/Call ratio
            - Options volume
            - Implied sentiment
        """
        try:
            stock = yf.Ticker(ticker)

            # Get options expiration dates
            expirations = stock.options

            if not expirations:
                logger.warning(f"No options data for {ticker}")
                return None

            # Get nearest expiration options chain
            nearest_exp = expirations[0]
            opt_chain = stock.option_chain(nearest_exp)

            calls = opt_chain.calls
            puts = opt_chain.puts

            # Calculate volumes
            call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
            put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0

            call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
            put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 0

            # Put/Call ratio
            pc_ratio_volume = put_volume / call_volume if call_volume > 0 else 0
            pc_ratio_oi = put_oi / call_oi if call_oi > 0 else 0

            # Determine sentiment
            # Lower P/C ratio = bullish (more calls than puts)
            # Higher P/C ratio = bearish (more puts than calls)
            if pc_ratio_volume < 0.7:
                sentiment = 'BULLISH'
            elif pc_ratio_volume > 1.3:
                sentiment = 'BEARISH'
            else:
                sentiment = 'NEUTRAL'

            return {
                'ticker': ticker,
                'nearest_expiration': nearest_exp,
                'call_volume': int(call_volume),
                'put_volume': int(put_volume),
                'call_open_interest': int(call_oi),
                'put_open_interest': int(put_oi),
                'put_call_ratio_volume': round(pc_ratio_volume, 2),
                'put_call_ratio_oi': round(pc_ratio_oi, 2),
                'options_sentiment': sentiment,
                'data_source': 'Yahoo Finance (FREE)'
            }

        except Exception as e:
            logger.error(f"Error fetching options data for {ticker}: {str(e)}")
            return None

    # =========================================================================
    # SEC EDGAR - DIRECT FILINGS (FREE)
    # =========================================================================

    def get_sec_filings(self, ticker: str, filing_types: List[str] = None) -> Optional[List[Dict]]:
        """
        Get recent SEC filings from EDGAR (FREE).

        Args:
            ticker: Stock symbol
            filing_types: Filter by type (10-K, 10-Q, 8-K, 4, etc.)
        """
        try:
            # First get CIK number
            cik = self._get_cik(ticker)
            if not cik:
                return None

            # Get recent filings
            url = f"{self.sec_base_url}/submissions/CIK{cik.zfill(10)}.json"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            filings = data.get('filings', {}).get('recent', {})

            if not filings:
                return None

            # Parse filings
            results = []
            forms = filings.get('form', [])
            dates = filings.get('filingDate', [])
            descriptions = filings.get('primaryDocument', [])
            accession_numbers = filings.get('accessionNumber', [])

            for i in range(min(20, len(forms))):
                form_type = forms[i]

                # Filter by type if specified
                if filing_types and form_type not in filing_types:
                    continue

                filing = {
                    'form_type': form_type,
                    'filing_date': dates[i] if i < len(dates) else '',
                    'document': descriptions[i] if i < len(descriptions) else '',
                    'accession_number': accession_numbers[i] if i < len(accession_numbers) else ''
                }
                results.append(filing)

            return results[:10]

        except Exception as e:
            logger.error(f"Error fetching SEC filings for {ticker}: {str(e)}")
            return None

    def _get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK number for a ticker."""
        try:
            url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={}&type=&dateb=&owner=include&count=1&output=atom"
            response = requests.get(url.format(ticker), headers=self.headers, timeout=10)

            # Try ticker to CIK mapping
            tickers_url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(tickers_url, headers=self.headers, timeout=10)
            data = response.json()

            for key, company in data.items():
                if company.get('ticker', '').upper() == ticker.upper():
                    return str(company.get('cik_str', ''))

            return None

        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {str(e)}")
            return None

    # =========================================================================
    # COMPREHENSIVE ANALYSIS (ALL FREE SOURCES)
    # =========================================================================

    def get_comprehensive_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive institutional analysis using ALL FREE sources.
        """
        logger.info(f"Fetching comprehensive institutional analysis for {ticker} (FREE)")

        analysis = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'institutional_holders': None,
            'insider_trading': None,
            'short_interest': None,
            'options_sentiment': None,
            'sec_filings': None,
            'overall_sentiment': 'NEUTRAL',
            'signals': [],
            'data_sources': ['Yahoo Finance', 'SEC EDGAR']
        }

        # Gather all data
        analysis['institutional_holders'] = self.get_institutional_holders(ticker)
        analysis['insider_trading'] = self.get_insider_trades(ticker)
        analysis['short_interest'] = self.get_short_interest(ticker)
        analysis['options_sentiment'] = self.get_options_sentiment(ticker)
        analysis['sec_filings'] = self.get_sec_filings(ticker, ['10-K', '10-Q', '8-K', '4'])

        # Generate signals
        bullish_signals = 0
        bearish_signals = 0

        # Institutional signals
        if analysis['institutional_holders']:
            io = analysis['institutional_holders']
            ownership = io.get('institutional_ownership_pct', 0)
            if ownership > 70:
                analysis['signals'].append(f'High institutional ownership ({ownership:.1f}%)')
                bullish_signals += 1

        # Insider trading signals
        if analysis['insider_trading']:
            it = analysis['insider_trading']
            if it.get('insider_sentiment') == 'BULLISH':
                analysis['signals'].append('Insider buying activity detected')
                bullish_signals += 2
            elif it.get('insider_sentiment') == 'BEARISH':
                analysis['signals'].append('Insider selling activity detected')
                bearish_signals += 2

        # Short interest signals
        if analysis['short_interest']:
            si = analysis['short_interest']
            if si.get('squeeze_potential') == 'HIGH':
                analysis['signals'].append(f"High short squeeze potential ({si.get('short_pct_float', 0):.1f}% short)")
                bullish_signals += 1
            elif si.get('short_pct_float', 0) > 20:
                analysis['signals'].append(f"High short interest ({si.get('short_pct_float', 0):.1f}%)")
                bearish_signals += 1

        # Options sentiment
        if analysis['options_sentiment']:
            os = analysis['options_sentiment']
            if os.get('options_sentiment') == 'BULLISH':
                analysis['signals'].append('Bullish options sentiment (low P/C ratio)')
                bullish_signals += 1
            elif os.get('options_sentiment') == 'BEARISH':
                analysis['signals'].append('Bearish options sentiment (high P/C ratio)')
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
# FORMAT REPORT
# =========================================================================

def format_institutional_report(analysis: Dict[str, Any]) -> str:
    """Format institutional analysis as readable report."""
    if not analysis:
        return "Institutional data not available"

    report = []
    report.append(f"\n{'='*60}")
    report.append(f"INSTITUTIONAL ANALYSIS - {analysis['ticker']} (FREE DATA)")
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
    io = analysis.get('institutional_holders')
    if io:
        report.append(f"\n📊 Institutional Ownership:")
        report.append(f"  • Ownership: {io.get('institutional_ownership_pct', 0):.1f}%")
        report.append(f"  • # of Holders: {io.get('num_institutional_holders', 0):,}")
        if io.get('top_holders'):
            report.append(f"  • Top Holder: {io['top_holders'][0].get('name', 'N/A')}")

    # Insider Trading
    it = analysis.get('insider_trading')
    if it:
        report.append(f"\n👔 Insider Trading:")
        report.append(f"  • Sentiment: {it.get('insider_sentiment', 'N/A')}")
        report.append(f"  • Buys: {it.get('total_buys', 0)} | Sells: {it.get('total_sells', 0)}")
        net = it.get('net_value', 0)
        report.append(f"  • Net Value: ${net:,.0f}")

    # Short Interest
    si = analysis.get('short_interest')
    if si:
        report.append(f"\n📉 Short Interest:")
        report.append(f"  • Short % of Float: {si.get('short_pct_float', 0):.1f}%")
        report.append(f"  • Days to Cover: {si.get('short_ratio', 0):.1f}")
        report.append(f"  • Squeeze Potential: {si.get('squeeze_potential', 'N/A')}")

    # Options
    os = analysis.get('options_sentiment')
    if os:
        report.append(f"\n📈 Options Flow:")
        report.append(f"  • Sentiment: {os.get('options_sentiment', 'N/A')}")
        report.append(f"  • Put/Call Ratio: {os.get('put_call_ratio_volume', 0):.2f}")
        report.append(f"  • Call Volume: {os.get('call_volume', 0):,}")
        report.append(f"  • Put Volume: {os.get('put_volume', 0):,}")

    # SEC Filings
    filings = analysis.get('sec_filings')
    if filings:
        report.append(f"\n📄 Recent SEC Filings:")
        for filing in filings[:5]:
            report.append(f"  • {filing.get('form_type', 'N/A')} - {filing.get('filing_date', 'N/A')}")

    report.append(f"\n{'='*60}")
    report.append("Data Sources: Yahoo Finance, SEC EDGAR (100% FREE)")
    report.append(f"{'='*60}\n")

    return '\n'.join(report)


# =========================================================================
# TOOL FUNCTIONS (For LangChain Integration)
# =========================================================================

def get_institutional_analysis(ticker: str) -> Dict[str, Any]:
    """Get comprehensive institutional analysis (FREE)."""
    client = InstitutionalDataClient()
    return client.get_comprehensive_analysis(ticker)


def get_institutional_score(ticker: str) -> int:
    """
    Calculate institutional sentiment score (-100 to +100).
    """
    client = InstitutionalDataClient()
    analysis = client.get_comprehensive_analysis(ticker)

    score = 0

    # Insider trading (most important)
    it = analysis.get('insider_trading')
    if it:
        sentiment = it.get('insider_sentiment')
        if sentiment == 'BULLISH':
            score += 30
        elif sentiment == 'BEARISH':
            score -= 30

    # Short interest
    si = analysis.get('short_interest')
    if si:
        squeeze = si.get('squeeze_potential')
        if squeeze == 'HIGH':
            score += 15
        short_pct = si.get('short_pct_float', 0)
        if short_pct > 30:
            score -= 15

    # Options sentiment
    os = analysis.get('options_sentiment')
    if os:
        sentiment = os.get('options_sentiment')
        if sentiment == 'BULLISH':
            score += 15
        elif sentiment == 'BEARISH':
            score -= 15

    # Institutional ownership
    io = analysis.get('institutional_holders')
    if io:
        ownership = io.get('institutional_ownership_pct', 0)
        if ownership > 80:
            score += 10
        elif ownership < 30:
            score -= 10

    return max(-100, min(100, score))


# =========================================================================
# CLI TEST
# =========================================================================

if __name__ == "__main__":
    import sys

    ticker = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'

    print(f"\n🔍 Fetching FREE institutional data for {ticker}...")

    client = InstitutionalDataClient()
    analysis = client.get_comprehensive_analysis(ticker)

    print(format_institutional_report(analysis))

    # Calculate score
    score = get_institutional_score(ticker)
    print(f"📊 Institutional Score: {score:+d}/100")

    if score > 30:
        print("   → Strong bullish institutional sentiment")
    elif score > 10:
        print("   → Moderately bullish sentiment")
    elif score < -30:
        print("   → Strong bearish institutional sentiment")
    elif score < -10:
        print("   → Moderately bearish sentiment")
    else:
        print("   → Neutral sentiment")
