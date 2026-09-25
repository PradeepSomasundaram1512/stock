#!/usr/bin/env python3
"""
🚀 ULTIMATE MARKET SCANNER 🚀

Scans the ENTIRE market, finds the best opportunities,
and sends you Discord alerts every hour during market hours.

Features:
- ✅ Scans S&P 500 stocks (500 major companies)
- ✅ Finds TOP 2 BUY and TOP 2 SELL opportunities
- ✅ Hourly Discord updates during market hours (9:30 AM - 4:00 PM ET)
- ✅ Uses all advanced analysis (Technical, Fundamental, News, ML)
- ✅ Automatically runs from market open to close

Usage:
    # Scan once now
    python ultimate_market_scanner.py --scan-now

    # Run continuously during market hours (auto-hourly updates)
    python ultimate_market_scanner.py --monitor

    # Quick scan (top 100 stocks only)
    python ultimate_market_scanner.py --scan-now --quick

    # Test Discord notifications
    python ultimate_market_scanner.py --test-discord
"""

import sys
import os
import logging
import argparse
import json
import time
import threading
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime, time as dt_time
from typing import List, Dict, Any, Tuple, Optional
import pytz
import yfinance as yf
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import components
from app.config import validate_config
from rag.ingest import initialize_knowledge_base
from graph.autonomous_decision_graph import get_autonomous_decision_graph


# Sector ETF map — used for sector performance context
SECTOR_ETFS = {
    'Technology': 'XLK',
    'Financials': 'XLF',
    'Energy': 'XLE',
    'Healthcare': 'XLV',
    'Industrials': 'XLI',
    'Consumer Discretionary': 'XLY',
    'Consumer Staples': 'XLP',
    'Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
    'Communication Services': 'XLC',
}

# Module-level sector cache so we fetch it once per scan, not once per stock
_sector_cache: Dict[str, float] = {}
_sector_cache_time: float = 0.0


def get_sector_performance() -> Dict[str, float]:
    """
    Fetch today's % change for each sector ETF.
    Cached for 30 minutes so we don't refetch on every stock analysis.
    Returns dict: sector_name → % change today.
    """
    global _sector_cache, _sector_cache_time
    if time.time() - _sector_cache_time < 1800 and _sector_cache:
        return _sector_cache
    try:
        etf_list = list(SECTOR_ETFS.values())
        raw = yf.download(etf_list, period='2d', progress=False, auto_adjust=True)
        # Newer yfinance returns MultiIndex columns (metric, ticker) — flatten to just tickers
        if hasattr(raw.columns, 'levels'):
            data = raw['Close']
        else:
            data = raw['Close'] if 'Close' in raw.columns else raw
        result = {}
        for sector, etf in SECTOR_ETFS.items():
            if etf in data.columns:
                vals = data[etf].dropna()
                if len(vals) >= 2:
                    chg = (vals.iloc[-1] / vals.iloc[-2] - 1) * 100
                    result[sector] = round(float(chg), 2)
        _sector_cache = result
        _sector_cache_time = time.time()
        return result
    except Exception:
        return {}


# Full S&P 500 stock list (500 major US companies)
SP500_ALL = [
    # Mega-cap Tech (>$1T)
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
    # Large-cap Tech ($100B-$1T)
    'AVGO', 'ORCL', 'ADBE', 'CRM', 'CSCO', 'INTC', 'AMD', 'QCOM', 'TXN', 'IBM',
    'NOW', 'PANW', 'INTU', 'AMAT', 'ADI', 'LRCX', 'KLAC', 'SNPS', 'CDNS', 'MRVL',
    'MU', 'NXPI', 'MCHP', 'FTNT', 'WDAY', 'TEAM', 'DDOG', 'NET', 'ZS', 'CRWD',
    # Finance & Banking
    'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'SPGI', 'BLK', 'C',
    'SCHW', 'AXP', 'CME', 'USB', 'PNC', 'TFC', 'BK', 'COF', 'AIG', 'MET', 'PRU',
    'AFL', 'ALL', 'TRV', 'PGR', 'CB', 'AMP', 'CINF', 'WRB', 'L', 'GL', 'RJF',
    # Healthcare & Pharma
    'UNH', 'LLY', 'JNJ', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'BMY', 'AMGN',
    'ELV', 'CVS', 'CI', 'GILD', 'VRTX', 'REGN', 'HUM', 'ISRG', 'ZTS', 'BSX', 'MDT',
    'SYK', 'BDX', 'EW', 'IDXX', 'RMD', 'DXCM', 'IQV', 'A', 'ALGN', 'MTD', 'HOLX',
    # Consumer Discretionary
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'TJX', 'SBUX', 'BKNG', 'ABNB', 'CMG',
    'MAR', 'GM', 'F', 'HLT', 'ORLY', 'AZO', 'DG', 'ROST', 'YUM', 'EBAY', 'ETSY',
    'BBY', 'ULTA', 'DPZ', 'TSCO', 'LVS', 'WYNN', 'MGM', 'NCLH', 'RCL', 'CCL',
    # Consumer Staples
    'WMT', 'COST', 'PG', 'KO', 'PEP', 'PM', 'MO', 'CL', 'MDLZ', 'GIS', 'KMB', 'K',
    'SYY', 'HSY', 'CHD', 'CLX', 'CAG', 'CPB', 'KHC', 'SJM', 'HRL', 'TSN', 'TAP',
    # Communication Services
    'META', 'GOOGL', 'GOOG', 'NFLX', 'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR',
    'EA', 'TTWO', 'PARA', 'WBD', 'MTCH', 'NWSA', 'FOX', 'DISH', 'OMC', 'IPG',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL', 'KMI',
    'WMB', 'HES', 'DVN', 'FANG', 'MRO', 'APA', 'BKR', 'NOV', 'FTI', 'CTRA', 'OVV',
    # Materials
    'LIN', 'APD', 'SHW', 'ECL', 'DD', 'NEM', 'FCX', 'CTVA', 'DOW', 'PPG', 'NUE',
    'VMC', 'MLM', 'ALB', 'CE', 'EMN', 'FMC', 'IFF', 'CF', 'MOS', 'IP', 'PKG',
    # Industrials
    'BA', 'CAT', 'HON', 'UNP', 'RTX', 'LMT', 'GE', 'DE', 'MMM', 'UPS', 'FDX', 'WM',
    'ITW', 'EMR', 'ETN', 'PH', 'CMI', 'NOC', 'GD', 'TDG', 'NSC', 'CSX', 'PSA', 'PLD',
    'AME', 'ROK', 'CARR', 'OTIS', 'IR', 'PCAR', 'JCI', 'FAST', 'ODFL', 'VRSK', 'PAYX',
    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'WEC', 'ED', 'PEG', 'ES',
    'AWK', 'DTE', 'PPL', 'AEE', 'FE', 'EIX', 'ETR', 'CMS', 'CNP', 'NI', 'LNT',
    # Real Estate
    'PLD', 'AMT', 'EQIX', 'PSA', 'CCI', 'WELL', 'DLR', 'SBAC', 'O', 'SPG', 'VICI',
    'AVB', 'EQR', 'VTR', 'ESS', 'MAA', 'INVH', 'UDR', 'CPT', 'ARE', 'KIM', 'REG',
    # Additional Large Caps
    'UBER', 'PLTR', 'SNOW', 'COIN', 'RBLX', 'U', 'SQ', 'SHOP', 'ROKU', 'ZM', 'DOCU',
    'OKTA', 'TWLO', 'DKNG', 'RIVN', 'LCID', 'HOOD', 'SOFI', 'AFRM', 'UPST', 'PATH',
    # More S&P 500
    'ADSK', 'ADP', 'AKAM', 'ARE', 'APTV', 'ACGL', 'ADM', 'AES', 'AOS', 'ATVI',
    'BALL', 'BAX', 'BBWI', 'BDX', 'BEN', 'BF.B', 'BIIB', 'BIO', 'BLL', 'BWA',
    'CBOE', 'CBRE', 'CDW', 'CDAY', 'CE', 'CHRW', 'CTAS', 'CNC', 'CNP', 'CPRT',
    'CRL', 'CSL', 'CTLT', 'CTSH', 'CTVA', 'CTRA', 'CZR', 'DAL', 'DFS', 'DGX',
    'DHI', 'DIS', 'DOV', 'DPZ', 'DRE', 'DRI', 'DVA', 'EBAY', 'ECL', 'EFX',
    'EG', 'EIX', 'EL', 'ELV', 'ENPH', 'EPAM', 'EQT', 'ESS', 'ETN', 'ETSY',
    'EVRG', 'EW', 'EXR', 'FANG', 'FAST', 'FICO', 'FIS', 'FITB', 'FLT', 'FMC',
    'FOXA', 'FRT', 'FTNT', 'FTV', 'GEN', 'GILD', 'GIS', 'GLW', 'GPC', 'GRMN',
    'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HES', 'HIG', 'HII', 'HOLX', 'HPE',
    'HPQ', 'HRL', 'HSIC', 'HST', 'HSY', 'HWM', 'IEX', 'IFF', 'ILMN', 'INCY',
    'INVH', 'IP', 'IPG', 'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITW', 'IVZ',
    'J', 'JBHT', 'JBL', 'JKHY', 'JNJ', 'JNPR', 'JPM', 'K', 'KEY', 'KEYS',
    'KHC', 'KIM', 'KMB', 'KMI', 'KMX', 'KO', 'KR', 'KVUE', 'L', 'LEN',
    'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LUV',
    'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP',
    'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM', 'MHK', 'MKC', 'MKTX',
    'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA',
    'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH', 'MTD', 'MU', 'NCLH',
    'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NOC', 'NOW', 'NRG',
    'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWS', 'NWSA', 'NXPI', 'O',
    'ODFL', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY', 'PARA', 'PAYC',
    'PAYX', 'PCAR', 'PCG', 'PEG', 'PEP', 'PFE', 'PFG', 'PG', 'PGR', 'PH',
    'PHM', 'PKG', 'PLD', 'PM', 'PNC', 'PNR', 'PNW', 'PODD', 'POOL', 'PPG',
    'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PWR', 'PXD', 'QCOM', 'QRVO', 'RCL',
    'RE', 'REG', 'REGN', 'RF', 'RHI', 'RJF', 'RL', 'RMD', 'ROK', 'ROL',
    'ROP', 'ROST', 'RSG', 'RTX', 'RVTY', 'SBAC', 'SBUX', 'SCHW', 'SHW', 'SJM',
    'SLB', 'SMCI', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STLD',
    'STT', 'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP',
    'TDG', 'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT', 'TJX', 'TMO',
    'TMUS', 'TPR', 'TRGP', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT',
    'TTWO', 'TXN', 'TXT', 'TYL', 'UAL', 'UBER', 'UDR', 'UHS', 'UNH', 'UNP',
    'UPS', 'URI', 'USB', 'V', 'VICI', 'VLO', 'VLTO', 'VMC', 'VRSK', 'VRSN',
    'VRTX', 'VST', 'VTR', 'VTRS', 'VZ', 'WAB', 'WAT', 'WBA', 'WBD', 'WDC',
    'WEC', 'WELL', 'WFC', 'WM', 'WMB', 'WMT', 'WRB', 'WST', 'WTW', 'WY',
    'WYNN', 'XEL', 'XOM', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZTS'
]

# Popular subset for quick scans (top 100 by market cap)
SP500_ALL = list(dict.fromkeys(SP500_ALL))   # the literal above lists ~180 tickers more than once
SP500_POPULAR = SP500_ALL[:100]


def get_discord_webhook() -> str:
    """Get Discord webhook URL from environment."""
    webhook = os.getenv('DISCORD_WEBHOOK_URL', '')
    if not webhook:
        logger.warning("DISCORD_WEBHOOK_URL not set in .env file")
    return webhook


def send_discord_alert(title: str, message: str, color: int = 0x00FF00, webhook_url: str = None):
    """Send formatted alert to Discord."""
    if not webhook_url:
        webhook_url = get_discord_webhook()

    if not webhook_url:
        logger.warning("Discord webhook not configured, skipping notification")
        return False

    try:
        # Discord embed description hard limit is 4096 chars
        if len(message) > 4090:
            message = message[:4087] + "..."

        embed = {
            "title": title,
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Ultimate Market Scanner"
            }
        }

        payload = {
            "embeds": [embed]
        }

        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()

        logger.info(f"✓ Discord alert sent: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to send Discord alert: {str(e)}")
        return False


def get_live_price(ticker: str) -> Optional[float]:
    """Fetch the current live/real-time price using yfinance fast_info."""
    try:
        info = yf.Ticker(ticker).fast_info
        # fast_info is a property-based object, NOT a dict — use getattr, not .get()
        price = getattr(info, 'last_price', None) or getattr(info, 'regularMarketPrice', None)
        return float(price) if price else None
    except Exception:
        return None


def analyze_stock(ticker: str, period: str = '60d', sector_perf: Dict = None,
                  interval: str = '60m', swing_mode: bool = False) -> Dict[str, Any]:
    """Analyze a single stock."""
    try:
        logger.info(f"Analyzing {ticker}...")

        if swing_mode:
            from graph.autonomous_decision_graph import get_swing_decision_graph
            decision_graph = get_swing_decision_graph()
        else:
            decision_graph = get_autonomous_decision_graph()

        result = decision_graph.graph.invoke({
            'ticker': ticker,
            'period': period,
            'interval': interval,
            'sector_perf': sector_perf or {},
        })

        if result.get('error'):
            logger.warning(f"Error analyzing {ticker}: {result['error']}")
            return None

        return result

    except Exception as e:
        logger.error(f"Failed to analyze {ticker}: {str(e)}")
        return None


def get_eastern_time() -> str:
    """Get current time in Eastern timezone formatted for display."""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    return now.strftime('%I:%M %p ET')


def rank_opportunities(results: List[Dict[str, Any]], prescreen_lookup: Dict = None,
                       market_context: Dict = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Rank stocks by opportunity.
    prescreen_lookup:  ticker -> pre-screen result (bouncing/rolling_over flags).
    market_context:    dict with keys spy_return (float, % today) and sector_perf (dict).
    Returns: (top_buys, top_sells)
    """
    prescreen_lookup = prescreen_lookup or {}
    market_context   = market_context or {}
    buy_opportunities = []
    sell_opportunities = []

    # Market regime: how much is SPY up/down today?
    spy_return   = market_context.get('spy_return', 0.0)   # e.g. +0.9 or -0.5
    sector_perf  = market_context.get('sector_perf', {})   # sector → % today

    # Regime-aware confidence floors
    # In a bull market (SPY > +0.3%) SELL signals need much higher conviction;
    # in a bear market (SPY < -0.3%) BUY signals need higher conviction.
    sell_min_conf = 0.55
    buy_min_conf  = 0.40
    if spy_return > 0.3:
        sell_min_conf = 0.65   # bull day — SELL only with high conviction
    elif spy_return < -0.3:
        buy_min_conf  = 0.55   # bear day — BUY only with high conviction

    for result in results:
        if not result or result.get('error'):
            continue

        decision = result.get('decision', {})
        ticker = result.get('ticker', 'UNKNOWN')

        recommendation = decision.get('decision', 'HOLD')
        confidence = decision.get('confidence', 0)
        price = result.get('features', {}).get('latest_price', 0)
        price_target = decision.get('price_target', 0)

        # Price cap: scan all stocks but only recommend those within the configured max price
        max_price = float(os.getenv('MAX_STOCK_PRICE', '50'))
        if max_price > 0 and price > max_price:
            continue

        # Calculate potential
        potential = 0
        if price_target and price > 0:
            potential = ((price_target - price) / price) * 100

        # Boost confidence when momentum confirms the signal (bouncing/rolling over)
        pre = prescreen_lookup.get(ticker, {})
        bouncing     = pre.get('bouncing', False)
        rolling_over = pre.get('rolling_over', False)
        if recommendation == 'BUY' and bouncing:
            confidence = min(1.0, confidence + 0.08)
        elif recommendation == 'SELL' and rolling_over:
            confidence = min(1.0, confidence + 0.08)

        # Sector alignment: suppress SELL signals when stock's sector is strongly green
        stock_sector   = result.get('fundamentals', {}).get('sector', '')
        sector_today   = sector_perf.get(stock_sector, 0.0)
        # If the sector is up > +1.5% and we got a SELL, require very high confidence
        if recommendation == 'SELL' and sector_today > 1.5:
            sell_min_conf = max(sell_min_conf, 0.72)
        # If sector is down > -1.5% and we got a BUY, require higher confidence
        if recommendation == 'BUY' and sector_today < -1.5:
            buy_min_conf = max(buy_min_conf, 0.62)

        stock_data = {
            'ticker': ticker,
            'decision': recommendation,
            'confidence': confidence * 100,
            'price': price,
            'price_target': price_target,
            'potential': potential,
            'risk_level': decision.get('risk_level', 'MEDIUM'),
            'key_factors': decision.get('key_factors', [])[:3],
            'rsi': result.get('features', {}).get('rsi', 0),
            'trend': result.get('features', {}).get('trend', 'NEUTRAL'),
            'atr': result.get('features', {}).get('atr'),
            'stop_loss': decision.get('stop_loss'),
            'reasoning': decision.get('reasoning', ''),
            'bouncing': bouncing,
            'rolling_over': rolling_over,
            'daily_rsi': pre.get('daily_rsi'),
        }

        # ── Daily RSI confirmation ───────────────────────────────────────────
        daily_rsi = pre.get('daily_rsi')
        if daily_rsi is not None:
            if recommendation == 'BUY':
                if daily_rsi < 40:
                    confidence = min(1.0, confidence + 0.07)  # daily also oversold = strong
                elif daily_rsi > 60:
                    confidence = max(0.0, confidence - 0.08)  # daily overbought = don't buy dip
            elif recommendation == 'SELL':
                if daily_rsi > 65:
                    confidence = min(1.0, confidence + 0.07)  # daily also overbought = strong
                elif daily_rsi < 40:
                    confidence = max(0.0, confidence - 0.08)  # daily oversold = don't short

        # ── Earnings block: skip stocks with earnings within 1 day ───────────
        days_to_earnings = result.get('decision', {}).get('days_to_earnings')
        if days_to_earnings is not None and 0 <= days_to_earnings <= 1:
            continue  # too risky — earnings today or tomorrow, skip entirely

        # ── Gap-up rejection: stock gapped up 8%+ and RSI dropped (gap fill) ─
        price_change_20h = pre.get('price_change_20h', 0) or 0
        if recommendation == 'BUY' and price_change_20h > 8:
            # Stock is still up huge today — RSI oversold means it's crashing from gap high
            # Don't buy a falling gap — wait for it to stabilise
            confidence = min(confidence, 0.45)  # will be filtered below 55% floor

        # ── Minimum liquidity: avg hourly volume > 50K (~300K+ daily) ────────
        avg_vol_20d = result.get('features', {}).get('avg_volume_20d', 0) or 0
        if avg_vol_20d < 50_000:
            continue   # too illiquid, skip entirely

        # ── Win rate filter: penalise historically losing tickers ─────────────
        ticker_win_rates = market_context.get('ticker_win_rates', {})
        hist_wr = ticker_win_rates.get(ticker)
        if hist_wr is not None:
            if hist_wr < 0.40:
                confidence = max(0.0, confidence - 0.12)  # bad track record → reduce
            elif hist_wr >= 0.65:
                confidence = min(1.0, confidence + 0.06)  # strong track record → boost

        # ── Bollinger Band proximity boost ────────────────────────────────────
        bb_lower = result.get('features', {}).get('lower_band')
        bb_upper = result.get('features', {}).get('upper_band')
        feat_price = result.get('features', {}).get('latest_price', 0) or 0
        if bb_lower and feat_price and feat_price <= bb_lower * 1.01 and recommendation == 'BUY':
            confidence = min(1.0, confidence + 0.08)  # at/below lower BB = strong oversold
        if bb_upper and feat_price and feat_price >= bb_upper * 0.99 and recommendation == 'SELL':
            confidence = min(1.0, confidence + 0.08)  # at/above upper BB = strong overbought

        # ── MACD crossover momentum confirmation ──────────────────────────────
        macd_crossover = result.get('features', {}).get('macd_crossover', False)
        macd_signal_dir = (result.get('features', {}).get('macd_signal') or '').lower()
        if recommendation == 'BUY' and macd_crossover and macd_signal_dir == 'bullish':
            confidence = min(1.0, confidence + 0.06)  # MACD just crossed up = momentum confirming
        elif recommendation == 'SELL' and macd_crossover and macd_signal_dir == 'bearish':
            confidence = min(1.0, confidence + 0.06)

        # ── Support/resistance proximity boost ────────────────────────────────
        dist_to_support = result.get('features', {}).get('distance_to_support_pct')
        dist_to_resist  = result.get('features', {}).get('distance_to_resistance_pct')
        if recommendation == 'BUY' and dist_to_support is not None and 0 <= dist_to_support <= 2.0:
            confidence = min(1.0, confidence + 0.07)  # price sitting right on support
        if recommendation == 'SELL' and dist_to_resist is not None and 0 <= dist_to_resist <= 2.0:
            confidence = min(1.0, confidence + 0.07)  # price at resistance ceiling

        # ── VWAP filter: BUY below VWAP preferred, SELL above VWAP preferred ─
        vwap = pre.get('vwap')
        if vwap and feat_price:
            if recommendation == 'BUY' and feat_price > vwap * 1.02:
                confidence = max(0.0, confidence - 0.06)  # buying extended above VWAP
            elif recommendation == 'SELL' and feat_price < vwap * 0.98:
                confidence = max(0.0, confidence - 0.06)  # selling below VWAP less reliable

        # ── Relative strength vs SPY ──────────────────────────────────────────
        rel_strength = pre.get('rel_strength')
        if rel_strength is not None:
            if recommendation == 'BUY' and rel_strength < -2.0:
                confidence = max(0.0, confidence - 0.07)  # much weaker than SPY = avoid
            elif recommendation == 'BUY' and rel_strength > 1.0:
                confidence = min(1.0, confidence + 0.05)  # outperforming SPY = stronger BUY
            elif recommendation == 'SELL' and rel_strength > 2.0:
                confidence = max(0.0, confidence - 0.06)  # surging vs SPY = risky SELL

        # ── Options flow boost (from pre-screen unusual activity flag) ──────
        opts_signal = pre.get('options_signal', '')
        if recommendation == 'BUY' and 'call' in str(opts_signal).lower():
            confidence = min(1.0, confidence + 0.05)   # unusual calls confirm BUY
        elif recommendation == 'BUY' and 'put' in str(opts_signal).lower():
            confidence = max(0.0, confidence - 0.05)   # unusual puts warn against BUY
        elif recommendation == 'SELL' and 'put' in str(opts_signal).lower():
            confidence = min(1.0, confidence + 0.05)   # unusual puts confirm SELL

        # ── Volume confidence adjustment ────────────────────────────────────
        vol_ratio = result.get('features', {}).get('volume_ratio', 1.0) or 1.0
        stock_data['volume_ratio'] = round(vol_ratio, 2)
        if vol_ratio < 0.5:
            confidence = max(0.0, confidence - 0.10)   # low volume = weak signal
        elif vol_ratio > 1.5 and recommendation == 'BUY':
            confidence = min(1.0, confidence + 0.05)   # high volume confirms BUY bounce
        elif vol_ratio > 1.5 and recommendation == 'SELL':
            confidence = min(1.0, confidence + 0.05)   # high volume confirms SELL breakdown
        stock_data['confidence'] = round(confidence * 100, 1)

        # ── Time-of-day gate — no new entries after 2:30 PM ET ─────────────
        eastern = pytz.timezone('US/Eastern')
        now_et  = datetime.now(eastern).time()
        late_day = now_et >= dt_time(14, 30)   # 2:30 PM ET

        rsi  = stock_data.get('rsi', 50) or 50
        trend = (result.get('features', {}).get('trend') or '').upper()

        if late_day:
            # After 2:30 PM only carry forward strong oversold/overbought signals already in motion
            buy_min_conf  = max(buy_min_conf, 0.75)
            sell_min_conf = max(sell_min_conf, 0.75)

        # ── RSI gate: BUY requires RSI ≤ 50 (not just "not overbought") ────
        # Prevents MACD-only BUYs at RSI 55-70 with no real oversold setup
        if recommendation == 'BUY' and rsi > 50:
            confidence = min(confidence, 0.52)   # cap, won't pass 55%+ threshold

        # ── Downtrend penalty: oversold in downtrend needs RSI < 20 ─────────
        if recommendation == 'BUY' and 'DOWN' in trend and rsi > 20:
            confidence = min(confidence, 0.50)   # needs more extreme oversold to buy falling stock
        stock_data['confidence'] = round(confidence * 100, 1)

        if recommendation == 'BUY' and confidence >= buy_min_conf:
            buy_opportunities.append(stock_data)
        elif recommendation == 'SELL' and confidence >= sell_min_conf:
            sell_opportunities.append(stock_data)
        elif recommendation == 'HOLD':
            # HOLD + very oversold RSI → show as watchlist BUY entry
            if rsi < 30 and not late_day:
                stock_data['decision'] = 'WATCH BUY'
                buy_opportunities.append(stock_data)
            # HOLD + strongly overbought RSI → show as watchlist SELL entry
            # Only in neutral/bear markets (suppress in bull days) and not late day
            elif rsi > 80 and spy_return <= 0.3 and not late_day:
                stock_data['decision'] = 'WATCH SELL'
                sell_opportunities.append(stock_data)

    # Sort buys: strong BUY first (by confidence * potential), then WATCH BUY by RSI (lower = more oversold)
    buy_opportunities.sort(key=lambda x: (
        0 if x['decision'] == 'BUY' else 1,
        -(x['confidence'] * abs(x['potential'])) if x['decision'] == 'BUY' else x.get('rsi', 50)
    ))
    # Sort sells: strong SELL first, then WATCH SELL by RSI (higher = more overbought)
    sell_opportunities.sort(key=lambda x: (
        0 if x['decision'] == 'SELL' else 1,
        -(x['confidence'] * abs(x['potential'])) if x['decision'] == 'SELL' else -x.get('rsi', 50)
    ))

    # FALLBACK: If no signals found, show best-looking stocks from results
    if not buy_opportunities or not sell_opportunities:
        logger.info("No strong signals found, using fallback ranking...")
        all_stocks = []
        for result in results:
            if not result or result.get('error'):
                continue
            decision = result.get('decision', {})
            ticker = result.get('ticker', 'UNKNOWN')
            confidence = decision.get('confidence', 0)
            price = result.get('features', {}).get('latest_price', 0)
            price_target = decision.get('price_target', 0)
            potential = ((price_target - price) / price) * 100 if price_target and price > 0 else 0

            all_stocks.append({
                'ticker': ticker,
                'decision': decision.get('decision', 'HOLD'),
                'confidence': confidence * 100,
                'price': price,
                'price_target': price_target,
                'potential': potential,
                'risk_level': decision.get('risk_level', 'MEDIUM'),
                'key_factors': decision.get('key_factors', [])[:3],
                'rsi': result.get('features', {}).get('rsi', 0),
                'trend': result.get('features', {}).get('trend', 'NEUTRAL'),
            })

        # Sort by potential upside for buys; fall back to RSI if no price targets
        if not buy_opportunities and all_stocks:
            stocks_with_target = [s for s in all_stocks if s['potential'] != 0]
            if stocks_with_target:
                sorted_by_upside = sorted(stocks_with_target, key=lambda x: x['potential'], reverse=True)
                buy_opportunities = sorted_by_upside[:2]
            else:
                # No price targets available — use RSI (lower RSI = more oversold = better buy)
                sorted_by_rsi = sorted(all_stocks, key=lambda x: x.get('rsi', 50))
                buy_opportunities = sorted_by_rsi[:2]
            for s in buy_opportunities:
                s['decision'] = 'WATCH'

        # Sort by potential downside for sells; fall back to RSI if no price targets
        if not sell_opportunities and all_stocks:
            stocks_with_target = [s for s in all_stocks if s['potential'] != 0]
            if stocks_with_target:
                sorted_by_downside = sorted(stocks_with_target, key=lambda x: x['potential'])
                sell_opportunities = sorted_by_downside[:2]
            else:
                # No price targets available — use RSI (higher RSI = more overbought = better sell)
                sorted_by_rsi = sorted(all_stocks, key=lambda x: x.get('rsi', 50), reverse=True)
                sell_opportunities = sorted_by_rsi[:2]
            for s in sell_opportunities:
                s['decision'] = 'WATCH'

    logger.info(f"Final results: {len(buy_opportunities)} buys, {len(sell_opportunities)} sells")
    return buy_opportunities, sell_opportunities


def _market_mood(overview: str) -> str:
    """Derive a plain-English market mood from the overview string."""
    if not overview:
        return "⚪ Unknown"
    spy_down = '▼' in overview.split('SPY')[1][:10] if 'SPY' in overview else False
    vix_up = '▲' in overview.split('VIX')[1][:10] if 'VIX' in overview else False
    if spy_down and vix_up:
        return "🔴 Risky — market falling, volatility high. Be careful today."
    elif spy_down:
        return "🟡 Cautious — market is down today. Smaller trades."
    elif vix_up:
        return "🟡 Volatile — market is choppy. Use tight stop losses."
    else:
        return "🟢 Calm — decent day to trade."


def _risk_plain(risk: str) -> str:
    mapping = {'low': '🟢 Low risk', 'medium': '🟡 Medium risk', 'high': '🔴 High risk'}
    return mapping.get(str(risk).lower(), f'🟡 {risk}')


def format_discord_message(top_buys: List[Dict], top_sells: List[Dict], scan_time: str,
                            scan_stats: Dict = None, save_to_db: bool = True,
                            regime: Dict = None) -> str:
    """Format a beginner day-trader Discord message with live prices, ATR stops, earnings warnings."""

    market_overview = get_market_overview()
    mood = _market_mood(market_overview)
    regime = regime or get_market_regime()

    # Minimum confidence gate — filter out noise before Discord rendering
    top_buys  = [s for s in top_buys  if s.get('confidence', 0) >= 55]
    top_sells = [s for s in top_sells if s.get('confidence', 0) >= 55]

    # Pre-fetch options signals in parallel — avoids 6 serial HTTP calls in the render loop
    _opt_tickers = [s['ticker'] for s in top_buys[:3]] + [s['ticker'] for s in top_sells[:3]]
    _opt_prices  = {s['ticker']: s['price'] for s in top_buys[:3] + top_sells[:3]}
    _options_cache: Dict[str, str] = {}

    def _fetch_opt(t: str) -> tuple:
        return t, get_options_signal(t, _opt_prices.get(t, 0))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as _ex:
        for _t, _sig in _ex.map(_fetch_opt, _opt_tickers):
            _options_cache[_t] = _sig

    # Daily P&L banner — show open positions at a glance before new signals
    pnl_summary = get_pnl_summary()
    if pnl_summary:
        message = pnl_summary
    else:
        message = ''

    message += f"**📊 Day-Trade Scan — {scan_time}**\n"
    if market_overview:
        message += f"Market: {market_overview}\n"
    message += f"Mood: {mood}\n"
    if scan_stats:
        message += f"*(Scanned {scan_stats['universe']} stocks in {scan_stats['elapsed_s']}s — prices are LIVE)*\n"

    # Market regime banner
    r = regime.get('regime', 'neutral')
    spy_3d = regime.get('spy_3d', 0.0)
    if r == 'bear':
        message += f"\n🐻 **BEAR MODE** — SPY {spy_3d:+.1f}% over 3 days. Cut position sizes by **50%**. Favour SELLs.\n"
    elif r == 'bull':
        message += f"\n🐂 **BULL MODE** — SPY {spy_3d:+.1f}% over 3 days. Normal sizing OK. BUYs favoured.\n"

    # Show top best and worst sectors
    sector_perf = get_sector_performance()
    if sector_perf:
        sorted_sectors = sorted(sector_perf.items(), key=lambda x: x[1], reverse=True)
        best = [(s, v) for s, v in sorted_sectors if v > 0][:2]
        worst = [(s, v) for s, v in sorted_sectors if v < 0][-2:]
        parts = [f"{s} {v:+.1f}%" for s, v in best] + [f"{s} {v:+.1f}%" for s, v in worst]
        if parts:
            message += f"Sectors: {' | '.join(parts)}\n"

    message += "\n"

    # ── BUY section ──────────────────────────────────────────────────────────
    message += "**🟢 CONSIDER BUYING TODAY**\n"
    if top_buys:
        for stock in top_buys[:3]:
            ticker = stock['ticker']

            # Always use live price for accuracy
            live = get_live_price(ticker)
            price = live if live else stock['price']

            rsi = stock.get('rsi', 0)
            confidence = stock['confidence']
            risk = _risk_plain(stock.get('risk_level', 'medium'))
            factors = stock.get('key_factors', [])
            signal = stock['decision']

            atr_data = calculate_atr_stop(ticker, price, precomputed_atr=stock.get('atr'))
            pos = calculate_position_size(price, atr_data.get('atr'))
            # In bear regime, halve shares to protect capital
            if regime.get('regime') == 'bear':
                pos = {**pos, 'shares': max(1, pos['shares'] // 2),
                       'position_value': round(pos['position_value'] / 2, 2),
                       'max_loss': round(pos['max_loss'] / 2, 2)}
            earnings = get_earnings_warning(ticker)

            stop_loss = atr_data['stop_loss']
            target = atr_data['price_target']
            stop_pct = atr_data['stop_pct']
            target_pct = round((target - price) / price * 100, 1)

            bounce_tag = " 🔄 *bouncing*" if stock.get('bouncing') else ""
            # Daily RSI context — shows whether daily trend aligns with hourly signal
            daily_rsi = stock.get('daily_rsi')
            daily_tag = ''
            if daily_rsi is not None:
                if daily_rsi < 35:
                    daily_tag = f" | Daily RSI {daily_rsi:.0f} ⬇️ oversold on daily too"
                elif daily_rsi > 65:
                    daily_tag = f" | Daily RSI {daily_rsi:.0f} ⬆️ daily uptrend (dip buy)"
                else:
                    daily_tag = f" | Daily RSI {daily_rsi:.0f}"
            opts = _options_cache.get(ticker, '')
            opts_line = f"   📊 Options: {opts}\n" if opts else ''

            message += f"\n**${ticker}** — {signal}{bounce_tag}\n"
            if earnings['message']:
                message += earnings['message']
            message += f"   💰 Buy now at: **${price:.2f}** (live price)\n"
            message += f"   🎯 Target by close: **${target:.2f}** (+{target_pct:.1f}%)\n"
            message += f"   🛑 Stop loss: **${stop_loss:.2f}** (-{stop_pct:.1f}% — sell immediately if hits this)\n"
            message += f"   💼 Size: **{pos['shares']} shares** = ${pos['position_value']:.0f} | Max loss: ${pos['max_loss']:.0f}\n"
            message += f"   📊 Confidence: {confidence:.0f}% | RSI: {rsi:.0f}{daily_tag} | {risk}\n"
            if opts_line:
                message += opts_line
            if factors:
                message += f"   📝 Why: {factors[0]}\n"

            if save_to_db:
                try:
                    from tools.db_manager import save_recommendation
                    stock_for_db = {**stock, 'price': price}
                    save_recommendation(stock_for_db, atr_data, pos, earnings)
                except Exception as e:
                    logger.warning(f"Could not save recommendation to DB: {e}")
    else:
        message += "*No buy opportunities right now. Wait for the next scan.*\n"

    message += "\n"

    # ── SELL / AVOID section ─────────────────────────────────────────────────
    message += "**🔴 CONSIDER SELLING / AVOIDING**\n"
    if top_sells:
        for stock in top_sells[:3]:
            ticker = stock['ticker']
            live = get_live_price(ticker)
            price = live if live else stock['price']
            rsi = stock.get('rsi', 0)
            confidence = stock['confidence']
            risk = _risk_plain(stock.get('risk_level', 'medium'))
            factors = stock.get('key_factors', [])
            signal = stock['decision']
            earnings = get_earnings_warning(ticker)

            atr_data = calculate_atr_stop(ticker, price, precomputed_atr=stock.get('atr'))
            sell_stop   = atr_data['sell_stop']    # above entry — exit if price goes UP
            sell_target = atr_data['sell_target']  # below entry — profit if price drops
            downside = round((sell_target - price) / price * 100, 1)

            daily_rsi = stock.get('daily_rsi')
            daily_tag = ''
            if daily_rsi is not None:
                if daily_rsi > 65:
                    daily_tag = f" | Daily RSI {daily_rsi:.0f} ⬆️ overbought on daily too"
                elif daily_rsi < 35:
                    daily_tag = f" | Daily RSI {daily_rsi:.0f} ⬇️ daily downtrend"
                else:
                    daily_tag = f" | Daily RSI {daily_rsi:.0f}"
            opts = _options_cache.get(ticker, '')
            opts_line = f"   📊 Options: {opts}\n" if opts else ''

            message += f"\n**${ticker}** — {signal}\n"
            if earnings['message']:
                message += earnings['message']
            message += f"   ⚠️ Current price: **${price:.2f}** (live)\n"
            message += f"   📉 Could fall to: **${sell_target:.2f}** ({downside:.1f}%)\n"
            message += f"   🛑 Stop (exit if rises to): **${sell_stop:.2f}**\n"
            message += f"   💡 If you own this, consider selling to protect yourself.\n"
            message += f"   📊 Confidence: {confidence:.0f}% | RSI: {rsi:.0f}{daily_tag} | {risk}\n"
            if opts_line:
                message += opts_line
            if factors:
                message += f"   📝 Why: {factors[0]}\n"

            if save_to_db:
                try:
                    from tools.db_manager import save_recommendation
                    stock_for_db = {**stock, 'price': price}
                    # For SELL: save correct direction stop/target so check_stop_losses works right
                    sell_atr = {**atr_data,
                                'stop_loss':    atr_data['sell_stop'],
                                'price_target': atr_data['sell_target']}
                    save_recommendation(stock_for_db, sell_atr, {}, earnings)
                except Exception as e:
                    logger.warning(f"Could not save recommendation to DB: {e}")
    else:
        message += "*No strong sell signals right now.*\n"

    message += "\n"
    message += "**💡 Day Trading Rules**\n"
    message += "• Set your stop loss BEFORE you buy — not after\n"
    message += "• Close all positions before 3:55 PM ET\n"
    message += "• 🔴 Mood day = reduce size by 50% or sit out\n"
    message += "• Never risk more than 1-2% of your account on one trade\n"
    message += "---\n*Not financial advice. Always do your own research.*"

    return message


def quick_technical_screen(ticker: str) -> Optional[Dict]:
    """
    Fast intraday technical screen using 60-minute yfinance data — no LLM calls.
    Gets LIVE price via fast_info so prices are always current.
    Returns a dict with basic stats and an interest_score, or None on failure.
    """
    try:
        t = yf.Ticker(ticker)

        # 60-minute bars for last 30 trading days — enough to resample to daily for multi-timeframe RSI
        hist = t.history(period='30d', interval='60m')
        if hist.empty or len(hist) < 15:
            return None

        close = hist['Close']
        high = hist['High']
        low = hist['Low']

        # RSI-14 (on hourly bars)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])

        # ATR-14 (Average True Range — measures typical hourly swing)
        prev_close = close.shift(1)
        tr = np.maximum(high - low, np.maximum(abs(high - prev_close), abs(low - prev_close)))
        atr = float(tr.rolling(14).mean().iloc[-1])

        # Volume ratio vs 20-bar average
        avg_vol = hist['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = float(hist['Volume'].iloc[-1] / avg_vol) if avg_vol > 0 else 1.0

        # Momentum over last 5 and 20 hourly bars
        price_change_5h = float((close.iloc[-1] / close.iloc[-5] - 1) * 100)
        price_change_20h = float((close.iloc[-1] / close.iloc[-20] - 1) * 100) if len(close) >= 20 else 0.0

        # LIVE price — overrides the last bar's close with real-time market price
        live = get_live_price(ticker)
        latest_price = live if live else float(close.iloc[-1])

        # Momentum confirmation: is the last candle green (price starting to bounce)?
        # For oversold stocks we want a green last bar = beginning of reversal
        # For overbought stocks we want a red last bar = beginning of drop
        last_candle_green = bool(close.iloc[-1] > close.iloc[-2])

        # "Bouncing" = oversold AND price turning up (not still falling)
        bouncing = rsi < 38 and last_candle_green
        # "Rolling over" = overbought AND price starting to drop
        rolling_over = rsi > 68 and not last_candle_green

        # Daily RSI — resample 30d of hourly bars to daily and compute RSI-14
        # This shows whether the DAILY trend aligns with the hourly signal
        daily_rsi = None
        try:
            daily_close = hist['Close'].resample('1d').last().dropna()
            if len(daily_close) >= 15:
                d_delta = daily_close.diff()
                d_gain = d_delta.clip(lower=0).rolling(14).mean()
                d_loss = (-d_delta.clip(upper=0)).rolling(14).mean()
                d_rs = d_gain / (d_loss + 1e-9)
                daily_rsi = float((100 - 100 / (1 + d_rs)).iloc[-1])
        except Exception:
            pass

        # VWAP — today's intraday bars only
        vwap = None
        try:
            today_bars = hist[hist.index.date == hist.index[-1].date()]
            if not today_bars.empty and today_bars['Volume'].sum() > 0:
                vwap = float(
                    (today_bars['Close'] * today_bars['Volume']).sum() /
                    today_bars['Volume'].sum()
                )
        except Exception:
            pass

        # Relative strength vs SPY (stock % change vs SPY % change last 5 bars)
        rel_strength = None
        try:
            spy_hist = yf.Ticker('SPY').history(period='5d', interval='60m')
            if len(spy_hist) >= 5:
                spy_chg = float((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-5] - 1) * 100)
                rel_strength = round(price_change_5h - spy_chg, 2)  # positive = outperforming SPY
        except Exception:
            pass

        # A stock is "interesting" if it has extreme RSI with momentum, volume spike, or big move
        is_interesting = (
            bouncing or rolling_over or
            vol_ratio > 1.5 or
            abs(price_change_5h) > 3
        )

        # Higher score = more worth a deep LLM look
        # Bonus for momentum confirmation: bouncing/rolling-over stocks get higher priority
        momentum_bonus = 10 if (bouncing or rolling_over) else 0
        interest_score = abs(rsi - 50) + (vol_ratio - 1) * 10 + abs(price_change_5h) + momentum_bonus

        return {
            'ticker': ticker,
            'rsi': rsi,
            'atr': atr,
            'vol_ratio': vol_ratio,
            'price_change_5h': price_change_5h,
            'price_change_20h': price_change_20h,
            'latest_price': latest_price,
            'is_interesting': is_interesting,
            'interest_score': interest_score,
            'bouncing': bouncing,
            'rolling_over': rolling_over,
            'last_candle_green': last_candle_green,
            'daily_rsi': daily_rsi,
            'vwap': vwap,
            'rel_strength': rel_strength,
        }
    except Exception:
        return None


def calculate_atr_stop(ticker: str, price: float,
                        atr_stop_mult: float = 1.5,
                        atr_target_mult: float = 3.0,
                        precomputed_atr: float = None) -> Dict:
    """
    Compute ATR-based stop loss and profit target for day trading.
    Uses precomputed_atr if provided (avoids duplicate yfinance fetch).
    Falls back to fetching 60m data, then fixed 2%/4% if unavailable.
    """
    try:
        if precomputed_atr and precomputed_atr > 0:
            atr = precomputed_atr
        else:
            hist = yf.Ticker(ticker).history(period='5d', interval='60m')
            if hist.empty or len(hist) < 15:
                raise ValueError("insufficient data")
            h, l, c = hist['High'], hist['Low'], hist['Close']
            prev_c = c.shift(1)
            tr = np.maximum(h - l, np.maximum(abs(h - prev_c), abs(l - prev_c)))
            atr = float(tr.rolling(14).mean().iloc[-1])
        # BUY  stop = below entry; SELL stop = above entry (will be overridden per side at call site)
        stop_loss    = round(price - atr_stop_mult  * atr, 2)
        price_target = round(price + atr_target_mult * atr, 2)
        stop_pct = round((price - stop_loss) / price * 100, 2)
        return {
            'stop_loss': stop_loss,
            'price_target': price_target,
            'atr': atr,
            'sell_stop': round(price + atr_stop_mult * atr, 2),   # correct stop for SELL signals
            'sell_target': round(price - atr_target_mult * atr, 2),  # correct target for SELL signals
            'atr_pct': round(atr / price * 100, 2),
            'stop_pct': stop_pct,
            'source': 'atr',
        }
    except Exception:
        stop_loss = round(price * 0.98, 2)
        return {
            'stop_loss':    stop_loss,
            'price_target': round(price * 1.04, 2),
            'sell_stop':    round(price * 1.02, 2),   # fallback SELL stop: 2% above entry
            'sell_target':  round(price * 0.96, 2),   # fallback SELL target: 4% below entry
            'atr': None,
            'atr_pct': None,
            'stop_pct': 2.0,
            'source': 'fixed_fallback',
        }


def get_earnings_warning(ticker: str) -> Dict:
    """Check if earnings are within the next 5 days — risky for day traders."""
    try:
        from datetime import date as date_type
        cal = yf.Ticker(ticker).calendar
        dates = cal.get('Earnings Date', []) if isinstance(cal, dict) else []
        if not dates:
            return {'days_away': None, 'warning': False, 'message': ''}
        next_e = dates[0]
        if hasattr(next_e, 'date'):
            next_e = next_e.date()
        elif hasattr(next_e, 'to_pydatetime'):
            next_e = next_e.to_pydatetime().date()
        days_away = (next_e - date_type.today()).days
        if days_away < 0:
            return {'days_away': None, 'warning': False, 'message': ''}
        warn_days = int(os.getenv('EARNINGS_WARN_DAYS', '5'))
        warning = days_away <= warn_days
        if warning:
            msg = f"   ⚠️ **EARNINGS IN {days_away} DAY(S)** ({next_e}) — very risky, consider skipping\n"
        elif days_away <= 14:
            msg = f"   📅 Earnings in {days_away} days ({next_e}) — be cautious\n"
        else:
            msg = ''
        return {'days_away': days_away, 'warning': warning, 'message': msg}
    except Exception:
        return {'days_away': None, 'warning': False, 'message': ''}


def calculate_position_size(price: float, atr: Optional[float]) -> Dict:
    """
    Beginner-friendly position sizing: risk 1% of account per trade.
    Account size set via DAY_TRADE_ACCOUNT_SIZE env var (default $10,000).
    """
    account_size = float(os.getenv('DAY_TRADE_ACCOUNT_SIZE', '10000'))
    risk_pct = float(os.getenv('DAY_TRADE_RISK_PCT', '0.01'))
    atr_stop_mult = 1.5

    stop_distance = (atr or price * 0.02) * atr_stop_mult
    if stop_distance <= 0 or price <= 0:
        return {'shares': 1, 'position_value': price, 'max_loss': stop_distance,
                'account_pct': round(price / account_size * 100, 1), 'account_size': account_size}

    shares_by_risk = int((account_size * risk_pct) / stop_distance)
    shares_by_cap = int((account_size * 0.20) / price)   # max 20% in one stock
    shares = max(min(shares_by_risk, shares_by_cap), 1)

    return {
        'shares': shares,
        'position_value': round(shares * price, 2),
        'max_loss': round(shares * stop_distance, 2),
        'account_pct': round(shares * price / account_size * 100, 1),
        'account_size': account_size,
    }


def scan_gaps(stock_list: List[str], min_gap_pct: float = 1.5) -> List[Dict]:
    """
    Find stocks that gapped significantly at today's open vs yesterday's close.
    Run at 9:45 AM ET to catch the best early-session opportunities.
    """
    def check_gap(ticker: str) -> Optional[Dict]:
        try:
            hist = yf.Ticker(ticker).history(period='3d', interval='1d')
            if len(hist) < 2:
                return None
            prev_close = float(hist['Close'].iloc[-2])
            today_open = float(hist['Open'].iloc[-1])
            if prev_close <= 0:
                return None
            gap_pct = (today_open - prev_close) / prev_close * 100
            if abs(gap_pct) < min_gap_pct:
                return None
            live = get_live_price(ticker) or today_open
            return {
                'ticker': ticker,
                'gap_pct': round(gap_pct, 2),
                'prev_close': round(prev_close, 2),
                'open': round(today_open, 2),
                'live_price': round(live, 2),
                'direction': 'UP' if gap_pct > 0 else 'DOWN',
            }
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(check_gap, stock_list))

    gaps = [r for r in results if r is not None]
    gaps.sort(key=lambda x: abs(x['gap_pct']), reverse=True)
    return gaps


def send_gap_scan():
    """9:45 AM ET: send gap-up/gap-down alert for the market open."""
    logger.info("Running 9:45 AM gap scan...")
    try:
        gaps = scan_gaps(SP500_ALL)
        if not gaps:
            return

        gap_ups = [g for g in gaps if g['direction'] == 'UP'][:4]
        gap_downs = [g for g in gaps if g['direction'] == 'DOWN'][:4]

        msg = f"**🔔 Opening Gap Scanner — 9:45 AM ET**\n"
        msg += f"*(Stocks that opened significantly different from yesterday's close)*\n\n"

        if gap_ups:
            msg += "**⬆️ GAP UPS** — opened higher, often continue if volume is high\n"
            for g in gap_ups:
                msg += f"**${g['ticker']}** +{g['gap_pct']:.1f}% gap | Yesterday: ${g['prev_close']} → Open: ${g['open']} | Live: **${g['live_price']}**\n"
            msg += "\n"

        if gap_downs:
            msg += "**⬇️ GAP DOWNS** — opened lower, may bounce if RSI < 35\n"
            for g in gap_downs:
                msg += f"**${g['ticker']}** {g['gap_pct']:.1f}% gap | Yesterday: ${g['prev_close']} → Open: ${g['open']} | Live: **${g['live_price']}**\n"
            msg += "\n"

        msg += "💡 *Wait 15–30 min before trading gaps. Let price stabilize first.*"

        send_discord_alert(
            title="🔔 Gap Scanner",
            message=msg,
            color=0xFF8C00,
            webhook_url=get_discord_webhook()
        )
        logger.info(f"Gap scan sent: {len(gap_ups)} ups, {len(gap_downs)} downs")
    except Exception as e:
        logger.error(f"Gap scan error: {e}")


def _decision_rows(results: List[Dict[str, Any]], prescreen_lookup: Dict, scan_id: str) -> List[Dict[str, Any]]:
    """One flat row per analysed candidate for the llm_decisions table."""
    def num(v):
        try:
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None

    now = datetime.utcnow().isoformat()
    rows = []
    for r in results:
        d = r.get('decision') or {}
        f, fund = r.get('features') or {}, r.get('fundamentals') or {}
        news, mkt = r.get('news_analysis') or {}, r.get('market_context') or {}
        pre = (prescreen_lookup or {}).get(r.get('ticker')) or {}
        rows.append({
            'scan_id': scan_id, 'decided_at': now, 'ticker': r.get('ticker'),
            'llm_status': d.get('llm_status', 'unknown'), 'model': d.get('model'),
            'latency_s': num(d.get('latency_s')), 'error': d.get('error'),
            'raw_decision': d.get('decision'), 'raw_confidence': num(d.get('confidence')),
            'price_target': num(d.get('price_target')), 'stop_loss': num(d.get('stop_loss')),
            'risk_level': d.get('risk_level'), 'time_horizon': d.get('time_horizon'),
            'key_factors': json.dumps(d.get('key_factors') or []), 'reasoning': d.get('reasoning'),
            'price': num(f.get('latest_price')), 'rsi': num(f.get('rsi')), 'trend': f.get('trend'),
            'atr': num(f.get('atr')),
            'pre_rsi': num(pre.get('rsi')), 'pre_vol_ratio': num(pre.get('vol_ratio')),
            'pre_momentum_5h': num(pre.get('price_change_5h')), 'pre_interest': num(pre.get('interest_score')),
            'pe_ratio': num(fund.get('pe_ratio')), 'valuation_score': num(fund.get('valuation_score')),
            'health_score': num(fund.get('health_score')), 'growth_score': num(fund.get('growth_score')),
            'news_sentiment': news.get('sentiment'), 'news_score': num(news.get('sentiment_score')),
            'news_count': news.get('news_count'), 'market_trend': mkt.get('market_trend'),
        })
    return rows


def scan_market(stock_list: List[str], quick: bool = False, max_stocks: int = None) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Scan the market and return top opportunities.

    Args:
        stock_list: List of stock tickers to scan
        quick: If True, scan only top 20 stocks (legacy)
        max_stocks: Maximum number of stocks to scan (default: None = ALL stocks)

    Returns:
        (top_buys, top_sells, scan_stats)
    """
    scan_start = time.time()

    # Deduplicate while preserving order
    seen = set()
    stock_list = [t for t in stock_list if not (t in seen or seen.add(t))]

    # Legacy quick mode support
    if quick:
        stock_list = stock_list[:20]
    elif max_stocks is not None:
        stock_list = stock_list[:max_stocks]

    total_universe = len(stock_list)
    logger.info(f"Universe: {total_universe} stocks")

    # ── Step 1: Fast parallel technical pre-screen (no LLM) ──────────────────
    logger.info("Step 1/2: Pre-screening with RSI/volume/momentum (parallel)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        screen_results = list(executor.map(quick_technical_screen, stock_list))

    # Keep all stocks with valid price data; price filter applied later in rank_opportunities()
    screened = [r for r in screen_results if r is not None and r.get('latest_price', 0) > 0]
    logger.info(f"Pre-screen: {len(screened)}/{len(screen_results)} stocks returned valid data")

    # Build a balanced candidate set: top oversold (buy side) + top overbought (sell side)
    # Sorting all by RSI ensures we get candidates from both ends even in one-sided markets
    by_rsi_asc = sorted(screened, key=lambda x: x['rsi'])   # most oversold first
    by_rsi_desc = sorted(screened, key=lambda x: x['rsi'], reverse=True)  # most overbought first

    # Also include high interest_score stocks (volume spikes, big moves)
    by_interest = sorted(
        [r for r in screened if r['is_interesting']],
        key=lambda x: x['interest_score'], reverse=True
    )

    # Merge: 20 most oversold + 20 most overbought + 10 highest interest, deduplicated
    seen_tickers: set = set()
    candidates = []
    for r in by_rsi_asc[:20] + by_rsi_desc[:20] + by_interest[:10]:
        if r['ticker'] not in seen_tickers:
            seen_tickers.add(r['ticker'])
            candidates.append(r)

    # Fallback: if screened list is tiny, just use all of it
    if len(candidates) < 10 and screened:
        candidates = screened

    candidate_tickers = [r['ticker'] for r in candidates]

    # Build lookup so rank_opportunities can access pre-screen flags (bouncing, rolling_over)
    prescreen_lookup = {r['ticker']: r for r in candidates}

    # Filter out stocks already recommended today (no-repeat rule)
    try:
        from tools.db_manager import get_todays_recommended_tickers
        already_today = get_todays_recommended_tickers()
        if already_today:
            before = len(candidate_tickers)
            candidates = [c for c in candidates if c['ticker'] not in already_today]
            candidate_tickers = [r['ticker'] for r in candidates]
            logger.info(f"Skipping {before - len(candidate_tickers)} already-recommended today: {already_today}")
    except Exception:
        pass

    # Fetch sector performance once (cached 30 min) for LLM context
    sector_perf = get_sector_performance()

    logger.info(
        f"Pre-screen: {len(screened)}/{total_universe} returned data, "
        f"{len(by_interest)} flagged interesting → {len(candidate_tickers)} selected for deep analysis"
    )

    # ── Step 2: Deep parallel LLM analysis on candidates ─────────────────────
    logger.info(f"Step 2/2: Deep LLM analysis on {len(candidate_tickers)} stocks (parallel)...")

    # Pre-warm singleton now (single thread) so workers don't race to create it
    get_autonomous_decision_graph()

    errors = 0

    def analyze_with_delay(ticker: str):
        result = analyze_stock(ticker, sector_perf=sector_perf)
        time.sleep(0.3)  # light rate-limit buffer
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        deep_results = list(executor.map(analyze_with_delay, candidate_tickers))

    results = []
    for r in deep_results:
        if r:
            results.append(r)
        else:
            errors += 1

    scan_id = datetime.utcnow().replace(microsecond=0).isoformat()
    try:
        from tools.db_manager import save_llm_decisions
        n_logged = save_llm_decisions(_decision_rows(results, prescreen_lookup, scan_id))
        n_fb = sum(1 for r in results if (r.get('decision') or {}).get('llm_status') == 'fallback_error')
        logger.info(f"Logged {n_logged} candidate decisions ({n_fb} exception fallbacks)")
    except Exception as e:  # logging must never break a scan
        logger.warning(f"Could not log candidate decisions: {e}")

    elapsed = time.time() - scan_start
    logger.info(
        f"✓ Scan complete in {elapsed:.0f}s — "
        f"{len(results)} analysed, {errors} errors, {total_universe - len(screened)} data failures"
    )

    # Get SPY's today return for regime filter
    spy_return_today = 0.0
    try:
        spy_hist = yf.Ticker('SPY').history(period='2d')
        if len(spy_hist) >= 2:
            spy_return_today = round(
                (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-2] - 1) * 100, 2
            )
    except Exception:
        pass

    try:
        from tools.db_manager import get_ticker_win_rates
        ticker_win_rates = get_ticker_win_rates(min_trades=5)
        logger.info(f"Loaded win rates for {len(ticker_win_rates)} tickers from DB")
    except Exception:
        ticker_win_rates = {}

    mkt_ctx = {
        'spy_return': spy_return_today,
        'sector_perf': sector_perf,
        'ticker_win_rates': ticker_win_rates,
    }
    logger.info(f"Market regime: SPY {spy_return_today:+.2f}% today — "
                f"sell_floor={'65%' if spy_return_today > 0.3 else '55%'}")

    # Rank opportunities (pass pre-screen lookup + market context for regime filter)
    top_buys, top_sells = rank_opportunities(results, prescreen_lookup, mkt_ctx)
    logger.info(f"Signals: {len(top_buys)} BUY, {len(top_sells)} SELL")
    try:
        from tools.db_manager import mark_final_signals
        mark_final_signals(scan_id, list(top_buys) + list(top_sells))
    except Exception as e:
        logger.warning(f"Could not mark final signals: {e}")

    scan_stats = {
        'universe': total_universe,
        'screened': len(screened),
        'candidates': len(candidate_tickers),
        'analysed': len(results),
        'errors': errors,
        'elapsed_s': int(elapsed),
    }

    return top_buys, top_sells, scan_stats


def get_market_overview() -> str:
    """Fetch a one-line market summary (SPY, QQQ, VIX) using yfinance."""
    try:
        lines = []
        for sym, label in [('SPY', 'SPY'), ('QQQ', 'QQQ'), ('^VIX', 'VIX')]:
            try:
                hist = yf.Ticker(sym).history(period='2d')
                if len(hist) >= 2:
                    vals = hist['Close'].dropna()
                    chg = (vals.iloc[-1] / vals.iloc[-2] - 1) * 100
                    arrow = '▲' if chg >= 0 else '▼'
                    lines.append(f"{label} {arrow}{abs(chg):.1f}%")
            except Exception:
                pass
        return ' | '.join(lines) if lines else ''
    except Exception:
        return ''


def is_market_hours() -> bool:
    """Check if current time is during market hours (9:30 AM - 4:00 PM ET), excluding holidays."""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)

    logger.info(f"Current Eastern Time: {now.strftime('%Y-%m-%d %I:%M %p %Z')} (weekday={now.weekday()})")

    if now.weekday() >= 5:
        logger.info("Weekend - market closed")
        return False

    if is_market_holiday(now):
        logger.info("Market holiday - market closed")
        return False

    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    current_time = now.time()
    is_open = market_open <= current_time <= market_close
    logger.info(f"Market hours check: {current_time} vs {market_open}-{market_close} = {'OPEN' if is_open else 'CLOSED'}")
    return is_open


# US stock market holidays (NYSE) for 2026 and 2027
_MARKET_HOLIDAYS = {
    # 2026
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03',
    '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
    '2026-11-26', '2026-12-25',
    # 2027
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26',
    '2027-05-31', '2027-06-18', '2027-07-05', '2027-09-06',
    '2027-11-25', '2027-12-24',
}


def is_market_holiday(dt_et=None) -> bool:
    """Return True if the given Eastern datetime falls on a US market holiday."""
    if dt_et is None:
        eastern = pytz.timezone('US/Eastern')
        dt_et = datetime.now(eastern)
    return dt_et.strftime('%Y-%m-%d') in _MARKET_HOLIDAYS


def send_go_no_go():
    """
    9:50 AM ET — Send a single clear GO / CAUTION / SIT OUT signal every trading day.
    Checks VIX, market regime (SPY 3-day trend), and sector breadth.
    Replaces the VIX-only check with a full market health assessment.
    """
    try:
        eastern = pytz.timezone('US/Eastern')
        if datetime.now(eastern).weekday() >= 5:
            return

        regime      = get_market_regime()
        sector_perf = get_sector_performance()

        vix = 20.0
        try:
            vix_hist = yf.Ticker('^VIX').history(period='2d')
            if not vix_hist.empty:
                vix = float(vix_hist['Close'].iloc[-1])
        except Exception:
            pass

        red_sectors   = sum(1 for v in sector_perf.values() if v < 0) if sector_perf else 0
        total_sectors = len(sector_perf) if sector_perf else 11

        danger_count = 0
        warnings     = []

        if vix >= 30:
            danger_count += 1
            level = "extreme" if vix >= 40 else "high"
            warnings.append(f"⚠️ VIX {vix:.0f} — {level} fear. Expect wide price swings.")

        if regime['regime'] == 'bear':
            danger_count += 1
            warnings.append(f"⚠️ Bear market mode — SPY {regime['spy_3d']:+.1f}% over 3 days.")

        if total_sectors > 0 and red_sectors >= round(total_sectors * 0.72):  # 8/11 sectors
            danger_count += 1
            warnings.append(f"⚠️ Broad selloff — {red_sectors}/{total_sectors} sectors are red.")

        vix_str    = f"VIX={vix:.0f}"
        regime_str = f"SPY 3d {regime['spy_3d']:+.1f}%"
        sectors_str = f"{red_sectors}/{total_sectors} sectors red" if sector_perf else "sector data unavailable"

        if danger_count == 0:
            signal = "🟢 GO — Trade Normally"
            body   = (
                f"All clear. {vix_str}, {regime_str}, {sectors_str}.\n\n"
                f"✅ Use your normal position sizes.\n"
                f"✅ BUY and SELL signals are reliable today.\n"
                f"✅ Aim for your usual 2–3% daily targets."
            )
            color = 0x00CC44
        elif danger_count == 1:
            signal = "🟡 CAUTION — Trade Smaller"
            warn_line = warnings[0] if warnings else "One risk factor detected."
            body   = (
                f"{warn_line}\n\n"
                f"**Reduce position sizes by 50%.**\n"
                f"• If you normally buy 10 shares → buy 5.\n"
                f"• Use tighter stop losses than usual.\n"
                f"• Avoid chasing — wait for clean, obvious setups."
            )
            color = 0xFFD700
        else:
            signal = "🔴 SIT OUT — High Risk Day"
            body   = (
                f"**{danger_count} danger signs active:**\n"
                + '\n'.join(warnings)
                + f"\n\n**Recommendation: Do NOT trade today.**\n"
                f"• Missing one day costs nothing.\n"
                f"• Trading on bad days is how money is lost fast.\n"
                f"• Watch from the sidelines and learn from the moves."
            )
            color = 0xFF4500

        send_discord_alert(
            title=f"🚦 Market Open: {signal}",
            message=f"**{signal}**\n{body}",
            color=color,
            webhook_url=get_discord_webhook()
        )
        logger.info(f"Go/No-Go sent: {signal} (VIX={vix:.0f}, regime={regime['regime']}, red={red_sectors}/{total_sectors})")
    except Exception as e:
        logger.error(f"Go/No-Go error: {e}")


# ── Intraday stop loss / target monitoring ────────────────────────────────────
_sl_alerted: set = set()   # rec IDs already alerted (stop or target)


def _mark_stopped_out(rec_id: int, exit_price: float):
    """Mark a recommendation as stopped out in the DB."""
    try:
        from tools.db_manager import get_connection
        conn = get_connection()
        conn.execute(
            "UPDATE recommendations SET is_closed=1, exit_date=?, exit_price=?, "
            "profit_loss_pct=NULL, outcome='STOPPED_OUT', exit_reason='stop_loss_hit' WHERE id=?",
            (datetime.now().isoformat(), exit_price, rec_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not mark rec {rec_id} stopped: {e}")


def check_stop_losses():
    """
    Check every open position against live price.
    Sends an immediate Discord alert if stop loss OR target is hit.
    Called every 5 minutes during market hours.
    """
    if not is_market_hours():
        return
    try:
        from tools.db_manager import get_todays_recs
        recs = get_todays_recs()
        open_recs = [r for r in recs if not r['is_closed']]
        if not open_recs:
            return

        webhook = get_discord_webhook()
        for rec in open_recs:
            rec_id = rec['id']
            if rec_id in _sl_alerted:
                continue

            ticker   = rec['ticker']
            stop     = rec['stop_loss']
            target   = rec['price_target']
            entry    = rec['entry_price']
            decision = rec['decision'] or 'BUY'

            if not stop or not entry or entry == 0:
                continue

            live = get_live_price(ticker)
            if not live:
                continue

            is_buy = decision.upper() in ('BUY', 'WATCH BUY')

            # ── Stop loss hit ──────────────────────────────────────────────
            if is_buy and live <= stop:
                _sl_alerted.add(rec_id)
                pnl = (live - entry) / entry * 100

                # Quick news check — explain WHY it dropped
                why = ""
                try:
                    news = yf.Ticker(ticker).news
                    if news:
                        latest = news[0]
                        title = latest.get('content', {}).get('title', '') or latest.get('title', '')
                        if title:
                            why = f"\n📰 Latest news: *{title[:120]}*"
                except Exception:
                    pass

                msg = (
                    f"**🚨 STOP LOSS HIT — ${ticker}**\n"
                    f"Entry: **${entry:.2f}** | Stop: **${stop:.2f}** | Live: **${live:.2f}**\n"
                    f"Loss: **{pnl:+.1f}%** — **EXIT NOW. Do not wait.**{why}\n\n"
                    f"💡 Taking a small loss now prevents a bigger loss later. "
                    f"This is exactly what stop losses are for."
                )
                send_discord_alert(title="🚨 Stop Loss Alert", message=msg,
                                   color=0xFF0000, webhook_url=webhook)
                _mark_stopped_out(rec_id, live)
                logger.info(f"Stop loss alert: {ticker} @ ${live:.2f}")

            # ── Target hit ────────────────────────────────────────────────
            elif is_buy and target and live >= target:
                _sl_alerted.add(rec_id)
                pnl = (live - entry) / entry * 100
                msg = (
                    f"**🎯 TARGET HIT — ${ticker}**\n"
                    f"Entry: **${entry:.2f}** | Target: **${target:.2f}** | Live: **${live:.2f}**\n"
                    f"Gain: **{pnl:+.1f}%** — **Consider taking profit now!**\n\n"
                    f"💡 You can sell to lock in the gain, or move your stop loss up "
                    f"to **${entry:.2f}** (your entry = breakeven) and let it run a bit more."
                )
                send_discord_alert(title="🎯 Target Hit!", message=msg,
                                   color=0x00CC44, webhook_url=webhook)
                logger.info(f"Target hit alert: {ticker} @ ${live:.2f}")

            # ── Trailing stop — move to breakeven once halfway to target ──
            elif is_buy and target and entry:
                half_target = entry + (target - entry) * 0.5
                trail_key = f"trail-{rec_id}"
                if live >= half_target and trail_key not in _sl_alerted:
                    _sl_alerted.add(trail_key)
                    pnl = (live - entry) / entry * 100
                    msg = (
                        f"**🔒 MOVE STOP TO BREAKEVEN — ${ticker}**\n"
                        f"You're now **{pnl:+.1f}%** up — halfway to your target.\n"
                        f"**Action:** In your broker app, move your stop loss to **${entry:.2f}** "
                        f"(your original entry price).\n\n"
                        f"💡 This locks in a risk-free trade. Worst case you break even. "
                        f"Best case you hit the full target of **${target:.2f}**."
                    )
                    send_discord_alert(title="🔒 Move Stop to Breakeven", message=msg,
                                       color=0xFFD700, webhook_url=webhook)
                    logger.info(f"Trailing stop alert: {ticker} @ ${live:.2f}")

            # ── SELL-side: stop hit (price went UP — loss on SELL signal) ──
            # For SELL: sell_stop = entry + 1.5*ATR (above entry).
            # stop_loss in DB was saved as the BUY-side value; recompute proper SELL stop.
            elif not is_buy and entry:
                atr_info   = calculate_atr_stop(ticker, entry)
                sell_stop  = atr_info['sell_stop']   # above entry
                sell_tgt   = atr_info['sell_target']  # below entry

                if live >= sell_stop and rec_id not in _sl_alerted:
                    _sl_alerted.add(rec_id)
                    pnl = (entry - live) / entry * 100
                    msg = (
                        f"**🚨 SELL STOP HIT — ${ticker}**\n"
                        f"Entry: **${entry:.2f}** | Stop: **${sell_stop:.2f}** | Live: **${live:.2f}**\n"
                        f"Loss: **{pnl:+.1f}%** — **EXIT NOW. The stock went UP against your SELL call.**\n\n"
                        f"💡 Cut the loss immediately. Never let a small loss become a big one."
                    )
                    send_discord_alert(title="🚨 Sell Stop Alert", message=msg,
                                       color=0xFF0000, webhook_url=webhook)
                    logger.info(f"SELL stop alert: {ticker} @ ${live:.2f}")

                elif live <= sell_tgt and rec_id not in _sl_alerted:
                    _sl_alerted.add(rec_id)
                    pnl = (entry - live) / entry * 100
                    msg = (
                        f"**🎯 SELL TARGET HIT — ${ticker}**\n"
                        f"Entry: **${entry:.2f}** | Target: **${sell_tgt:.2f}** | Live: **${live:.2f}**\n"
                        f"Gain: **{pnl:+.1f}%** — **Consider closing your SELL position now!**\n\n"
                        f"💡 The stock dropped to your target. You can close to lock in the gain."
                    )
                    send_discord_alert(title="🎯 Sell Target Hit!", message=msg,
                                       color=0x00CC44, webhook_url=webhook)
                    logger.info(f"SELL target alert: {ticker} @ ${live:.2f}")

    except Exception as e:
        logger.error(f"Stop loss check error: {e}")


# ── Weekly performance report ─────────────────────────────────────────────────

def send_weekly_report():
    """Monday 9 AM ET: send last week's signal performance summary."""
    logger.info("Generating weekly performance report...")
    try:
        from tools.db_manager import get_weekly_recs
        recs = get_weekly_recs(days=7)

        if not recs:
            msg = "**📈 Weekly Report**\nNo completed trades tracked this week — signals were all HOLDs or market was closed."
        else:
            wins   = [r for r in recs if r['outcome'] == 'WIN']
            losses = [r for r in recs if r['outcome'] in ('LOSS', 'STOPPED_OUT')]
            flat   = [r for r in recs if r['outcome'] not in ('WIN', 'LOSS', 'STOPPED_OUT')]
            total  = len(recs)
            win_rate = len(wins) / total * 100 if total else 0

            pnls = [r['profit_loss_pct'] for r in recs if r['profit_loss_pct'] is not None]
            avg_pnl = sum(pnls) / len(pnls) if pnls else 0

            best  = max(recs, key=lambda r: r['profit_loss_pct'] or -999, default=None)
            worst = min(recs, key=lambda r: r['profit_loss_pct'] or 999, default=None)

            grade = "🏆 Excellent" if win_rate >= 70 else "✅ Good" if win_rate >= 55 else "⚠️ Needs work" if win_rate >= 40 else "❌ Rough week"

            msg = f"**📈 Weekly Performance Report**\n"
            msg += f"Week of {datetime.now().strftime('%b %d, %Y')}\n\n"
            msg += f"**Results:** ✅ {len(wins)} wins | ❌ {len(losses)} losses | ⬛ {len(flat)} flat\n"
            msg += f"**Win Rate:** {win_rate:.0f}% — {grade}\n"
            msg += f"**Avg P&L per trade:** {avg_pnl:+.1f}%\n\n"

            if best and best['profit_loss_pct']:
                msg += f"🏅 Best pick: **${best['ticker']}** {best['profit_loss_pct']:+.1f}%\n"
            if worst and worst['profit_loss_pct']:
                msg += f"📉 Worst pick: **${worst['ticker']}** {worst['profit_loss_pct']:+.1f}%\n"

            msg += f"\n💡 "
            if win_rate >= 60:
                msg += "Strong week! The RSI bounce signals are working well."
            elif win_rate >= 45:
                msg += "Decent week. Watch for high-VIX days — those tend to produce noisy signals."
            else:
                msg += "Tough week — likely caused by choppy/volatile market. Reduce trade size when VIX > 25."

        send_discord_alert(
            title="📈 Weekly Performance Report",
            message=msg,
            color=0x4169E1,
            webhook_url=get_discord_webhook()
        )
        logger.info("Weekly report sent")
    except Exception as e:
        logger.error(f"Weekly report error: {e}")


def get_market_regime() -> Dict:
    """
    Detect current market regime based on SPY's 3-day performance.
    Bear  = SPY down > 2% over 3 days → reduce BUY sizes, prioritise SELLs
    Bull  = SPY up  > 2% over 3 days → normal signals
    Neutral = in between
    """
    try:
        spy = yf.Ticker('SPY').history(period='7d', interval='1d')
        if len(spy) < 4:
            return {'regime': 'neutral', 'spy_3d': 0.0, 'spy_5d': 0.0}
        spy_3d = float((spy['Close'].iloc[-1] / spy['Close'].iloc[-4] - 1) * 100)
        spy_5d = float((spy['Close'].iloc[-1] / spy['Close'].iloc[0]  - 1) * 100) if len(spy) >= 5 else spy_3d
        regime = 'bear' if spy_3d <= -2.0 else 'bull' if spy_3d >= 2.0 else 'neutral'
        return {'regime': regime, 'spy_3d': round(spy_3d, 2), 'spy_5d': round(spy_5d, 2)}
    except Exception:
        return {'regime': 'neutral', 'spy_3d': 0.0, 'spy_5d': 0.0}


def get_options_signal(ticker: str, price: float) -> str:
    """
    Check for unusual near-the-money options activity (free via yfinance).
    Returns a short label or empty string if nothing unusual.
    Unusual = today's volume > 50% of open interest (new money flowing in).
    """
    try:
        t = yf.Ticker(ticker)
        exps = t.options
        if not exps:
            return ''
        chain = t.option_chain(exps[0])   # nearest expiry = most active
        calls = chain.calls
        puts  = chain.puts

        # Near-the-money: within 3% of current price
        atm_calls = calls[(calls['strike'] >= price * 0.97) & (calls['strike'] <= price * 1.03)]
        atm_puts  = puts[ (puts['strike']  >= price * 0.97) & (puts['strike']  <= price * 1.03)]

        call_vol = float(atm_calls['volume'].fillna(0).sum())
        put_vol  = float(atm_puts['volume'].fillna(0).sum())
        call_oi  = float(atm_calls['openInterest'].fillna(0).sum())
        put_oi   = float(atm_puts['openInterest'].fillna(0).sum())

        call_ratio = call_vol / max(call_oi, 1)
        put_ratio  = put_vol  / max(put_oi,  1)

        if call_ratio > 0.5 and call_ratio > put_ratio * 2:
            return '🔥 unusual call activity'
        elif put_ratio > 0.5 and put_ratio > call_ratio * 2:
            return '⚠️ unusual put activity'
        return ''
    except Exception:
        return ''


def get_pnl_summary() -> str:
    """
    Returns a formatted string of today's open positions with live P&L.
    Shown at the top of each hourly Discord scan — so you always know where you stand.
    """
    try:
        from tools.db_manager import get_todays_recs
        recs = get_todays_recs()
        open_recs = [r for r in recs if not r['is_closed']]
        if not open_recs:
            return ''

        lines = []
        total_pnl_est = 0.0

        for rec in open_recs[:6]:
            entry  = rec['entry_price'] or 0
            stop   = rec['stop_loss'] or 0
            ticker = rec['ticker']
            if not entry:
                continue

            live     = get_live_price(ticker) or entry
            pnl_pct  = (live - entry) / entry * 100
            # Estimate shares from 1% risk rule (mirrors calculate_position_size)
            stop_dist = abs(entry - stop) if stop else entry * 0.02
            shares    = max(1, min(int(100 / max(stop_dist, 0.01)), int(2000 / max(entry, 1))))
            dollar_pnl = shares * (live - entry)
            total_pnl_est += dollar_pnl

            icon = '✅' if pnl_pct > 0.3 else '🔴' if pnl_pct < -0.3 else '⬛'
            lines.append(
                f"{icon} **${ticker}** {rec['decision']}: "
                f"${entry:.2f} → ${live:.2f} ({pnl_pct:+.1f}%)"
            )

        if not lines:
            return ''

        total_icon = '✅' if total_pnl_est > 0 else '🔴' if total_pnl_est < 0 else '⬛'
        summary  = "**📈 Today's Open Positions**\n"
        summary += '\n'.join(lines)
        summary += f"\n{total_icon} **Estimated Day P&L: ${total_pnl_est:+.0f}**\n\n"
        return summary
    except Exception:
        return ''


_scan_lock = threading.Lock()
_scan_in_progress = False


def run_hourly_scan():
    """Run market scan and send Discord update."""
    global _scan_in_progress

    with _scan_lock:
        if _scan_in_progress:
            logger.warning("Previous scan still running — skipping this cycle")
            return
        _scan_in_progress = True

    if not is_market_hours():
        with _scan_lock:
            _scan_in_progress = False
        logger.info("Outside market hours, skipping scan")
        return

    try:
        _do_scan()
    finally:
        with _scan_lock:
            _scan_in_progress = False


def _do_scan():
    """Internal: perform the actual scan and send Discord alert."""
    logger.info("=" * 70)
    logger.info("DAY-TRADE SCAN STARTING")
    logger.info("=" * 70)

    from agents.data_agent import get_data_agent
    get_data_agent().expire_cache()

    regime = get_market_regime()
    logger.info(f"Market regime: {regime['regime'].upper()} (SPY 3d: {regime['spy_3d']:+.1f}%)")

    top_buys, top_sells, scan_stats = scan_market(SP500_ALL, quick=False)

    scan_time = get_eastern_time()
    # save_to_db=True logs every recommendation for the closing recap
    message = format_discord_message(top_buys, top_sells, scan_time, scan_stats, save_to_db=True, regime=regime)

    webhook = get_discord_webhook()
    if webhook:
        send_discord_alert(
            title="🚀 Day-Trade Scan",
            message=message,
            color=0x0099ff,
            webhook_url=webhook
        )

    logger.info("✓ Scan completed")
    logger.info("=" * 70)


def send_premarket_brief():
    """9:00 AM ET — watchlist brief before market opens."""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    if now.weekday() >= 5:
        return

    logger.info("Sending pre-market brief...")
    overview = get_market_overview()
    mood = _market_mood(overview)

    msg = f"**☀️ Pre-Market Brief — {now.strftime('%I:%M %p ET')}**\n"
    msg += f"Market mood: {mood}\n"
    if overview:
        msg += f"Overnight: {overview}\n\n"

    # Open positions from yesterday
    try:
        from tools.db_manager import get_open_recs
        open_recs = get_open_recs(since_days=2)
        if open_recs:
            msg += "**Yesterday's open positions — check these at open:**\n"
            for rec in open_recs[:5]:
                entry = rec['entry_price'] or 0
                if not entry:
                    continue
                live = get_live_price(rec['ticker']) or entry
                gap = (live - entry) / entry * 100
                stop = rec['stop_loss'] or 0
                target = rec['price_target'] or 0
                msg += (f"• **${rec['ticker']}** {rec['decision']} — "
                        f"entry ${entry:.2f}, now ${live:.2f} ({gap:+.1f}%)\n"
                        f"  Stop: ${stop:.2f} | Target: ${target:.2f}\n")
        else:
            msg += "No open positions from yesterday.\n"
    except Exception as e:
        logger.warning(f"Could not load open recs: {e}")

    msg += "\n**⏰ Market opens at 9:30 AM. First scan at 10:00 AM.**\n"
    msg += "💡 *Plan your trades now. Don't chase stocks at open — wait 15-30 min for volatility to settle.*"

    send_discord_alert(
        title="☀️ Pre-Market Watchlist",
        message=msg,
        color=0xFFD700,
        webhook_url=get_discord_webhook()
    )


def send_closing_recap():
    """3:45 PM ET — close all open recs and show P&L summary."""
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    if now.weekday() >= 5:
        return

    logger.info("Sending closing recap...")
    try:
        from tools.db_manager import get_todays_recs, close_todays_recs

        # Fetch live prices for all open positions
        todays = get_todays_recs()
        open_tickers = [r['ticker'] for r in todays if not r['is_closed']]
        price_map = {}
        for ticker in set(open_tickers):
            price_map[ticker] = get_live_price(ticker) or 0

        close_todays_recs(price_map)
        todays = get_todays_recs()   # re-fetch with updated outcomes

        wins = [r for r in todays if r['outcome'] == 'WIN']
        losses = [r for r in todays if r['outcome'] in ('LOSS', 'STOPPED_OUT')]
        flat = [r for r in todays if r['outcome'] not in ('WIN', 'LOSS', 'STOPPED_OUT')]

        msg = f"**📊 Closing Recap — {now.strftime('%b %d, %Y')}**\n"
        msg += f"Today's picks: ✅ {len(wins)} wins | ❌ {len(losses)} losses | ⬛ {len(flat)} flat\n\n"

        for rec in todays:
            icon = {"WIN": "✅", "LOSS": "❌", "STOPPED_OUT": "🛑"}.get(rec['outcome'], "⬛")
            entry = rec['entry_price'] or 0
            exit_p = rec['exit_price'] or entry
            pnl = rec['profit_loss_pct'] or 0
            msg += f"{icon} **${rec['ticker']}** {rec['decision']}: ${entry:.2f} → ${exit_p:.2f} ({pnl:+.1f}%)\n"

        msg += "\n💡 *Market closes in 15 minutes. Exit all positions before 4:00 PM.*"
        if len(wins) > len(losses):
            msg += "\n🎉 Good day! Review what worked and use the same signals tomorrow."
        elif len(losses) > len(wins):
            msg += "\n📚 Tough day. Review which signals failed — this is how you learn."

        # Tomorrow's watchlist — scan for most oversold stocks right now
        try:
            logger.info("Building tomorrow's watchlist...")
            watch_results = []
            sample = SP500_ALL[:150]   # quick sample, fast enough at close
            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
                screens = list(ex.map(quick_technical_screen, sample))
            oversold = sorted(
                [r for r in screens if r and r['rsi'] < 32],
                key=lambda x: x['rsi']
            )[:5]
            if oversold:
                msg += "\n\n**👀 Tomorrow's Watchlist — Most Oversold Right Now**\n"
                msg += "*(These are worth watching at tomorrow's open for a bounce)*\n"
                for r in oversold:
                    bounce = "🔄 bouncing" if r.get('bouncing') else "↘️ still falling"
                    msg += (f"**${r['ticker']}** RSI {r['rsi']:.0f} | "
                            f"${r['latest_price']:.2f} | {bounce} | "
                            f"Vol {r['vol_ratio']:.1f}x\n")
                msg += "💡 *Wait for RSI to cross above 30 and a green candle before buying.*"
        except Exception as e:
            logger.warning(f"Tomorrow watchlist error: {e}")

        # Warn about earnings reports tomorrow — don't hold overnight into earnings
        try:
            from datetime import date as date_type, timedelta
            tomorrow = date_type.today() + timedelta(days=1)
            all_tickers = list({r['ticker'] for r in todays})
            earnings_tmrw = []
            for t in all_tickers:
                try:
                    cal = yf.Ticker(t).calendar
                    dates = (cal.get('Earnings Date', []) if isinstance(cal, dict) else [])
                    if dates:
                        ed = dates[0]
                        if hasattr(ed, 'date'):
                            ed = ed.date()
                        if ed == tomorrow:
                            earnings_tmrw.append(t)
                except Exception:
                    pass
            if earnings_tmrw:
                msg += f"\n\n⚠️ **Earnings TOMORROW:** {', '.join(f'${t}' for t in earnings_tmrw)}\n"
                msg += "Do NOT hold these positions overnight — gap risk is very high."
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Closing recap error: {e}")
        msg = "**📊 Closing Recap**\n*Could not load today's data. Make sure to close all positions before 4 PM.*"

    send_discord_alert(
        title="📊 End-of-Day Recap",
        message=msg,
        color=0x4169E1,
        webhook_url=get_discord_webhook()
    )


def print_banner():
    """Print scanner banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║               🚀 ULTIMATE MARKET SCANNER 🚀                          ║
║                                                                      ║
║           Scans ALL Stocks, Finds Best Opportunities                ║
║           Sends Discord Alerts Every Hour During Market Hours       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='🚀 Ultimate Market Scanner - Find the best stock opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan market once and send Discord alert
  python ultimate_market_scanner.py --scan-now

  # Quick scan (top 20 stocks only)
  python ultimate_market_scanner.py --scan-now --quick

  # Monitor market with hourly updates
  python ultimate_market_scanner.py --monitor

  # Test Discord notifications
  python ultimate_market_scanner.py --test-discord

The scanner will automatically send Discord alerts with:
- TOP 2 BUY opportunities
- TOP 2 SELL opportunities
- Price targets, confidence levels, key factors
        """
    )

    parser.add_argument('--scan-now', action='store_true',
                       help='Scan the market once right now')
    parser.add_argument('--monitor', action='store_true',
                       help='Monitor market with hourly updates during market hours')
    parser.add_argument('--quick', action='store_true',
                       help='Quick scan mode (top 100 stocks only, default: ALL 500 S&P 500 stocks)')
    parser.add_argument('--test-discord', action='store_true',
                       help='Test Discord notification')
    parser.add_argument('--hourly-scan', action='store_true',
                       help='Run one hourly day-trade scan and exit (for external schedulers)')
    parser.add_argument('--premarket-brief', action='store_true',
                       help='Send the pre-market brief and exit (for external schedulers)')
    parser.add_argument('--gap-scan', action='store_true',
                       help='Run the gap scan and exit (for external schedulers)')
    parser.add_argument('--go-no-go', action='store_true',
                       help='Send the go/no-go signal and exit (for external schedulers)')
    parser.add_argument('--stop-loss-check', action='store_true',
                       help='Check stop losses/targets and exit (for external schedulers)')
    parser.add_argument('--weekly-report', action='store_true',
                       help='Send the weekly performance report and exit (for external schedulers)')
    parser.add_argument('--closing-recap', action='store_true',
                       help='Send the closing recap and exit (for external schedulers)')

    args = parser.parse_args()

    print_banner()

    # Validate configuration
    logger.info("Validating configuration...")
    if not validate_config():
        logger.error("Configuration validation failed")
        return 1
    logger.info("✓ Configuration valid")

    # Initialize knowledge base
    logger.info("Loading knowledge base...")
    initialize_knowledge_base()
    logger.info("✓ Knowledge base ready")

    # Migrate DB schema (idempotent, safe to run on every invocation —
    # each scheduled job runs as its own short-lived process)
    try:
        from tools.db_manager import migrate_schema
        migrate_schema()
    except Exception as e:
        logger.warning(f"DB migration warning: {e}")

    # Check Discord webhook
    webhook = get_discord_webhook()
    if not webhook:
        logger.warning("⚠️  Discord webhook not configured!")
        logger.warning("Set DISCORD_WEBHOOK_URL in .env to receive alerts")
        logger.warning("You can still run scans, but won't get Discord notifications")
    else:
        logger.info("✓ Discord notifications enabled")

    # Test Discord
    if args.test_discord:
        logger.info("Testing Discord notification...")
        send_discord_alert(
            title="✅ Test Notification",
            message="Discord notifications are working!\n\nYour Ultimate Market Scanner is ready to send hourly updates.",
            color=0x00ff00,
            webhook_url=webhook
        )
        logger.info("Check your Discord channel!")
        return 0

    # Scan once
    if args.scan_now:
        logger.info("\n" + "=" * 70)
        logger.info("MARKET SCAN STARTING")
        logger.info("=" * 70 + "\n")

        # Expire cache to ensure fresh data
        from agents.data_agent import get_data_agent
        data_agent = get_data_agent()
        logger.info("Expiring cache to get fresh stock prices...")
        data_agent.expire_cache()

        # Choose stock list based on mode
        stock_list = SP500_POPULAR if args.quick else SP500_ALL
        top_buys, top_sells, scan_stats = scan_market(stock_list, quick=False)

        # Print results
        print("\n" + "=" * 70)
        print("🟢 TOP 2 BUY OPPORTUNITIES")
        print("=" * 70)
        for i, stock in enumerate(top_buys[:3], 1):
            print(f"\n{i}. {stock['ticker']} [{stock['decision']}] @ ${stock['price']:.2f}")
            print(f"   Confidence: {stock['confidence']:.0f}% | RSI: {stock.get('rsi', 0):.0f}")
            if stock['price_target']:
                print(f"   Target: ${stock['price_target']:.2f} ({stock['potential']:+.1f}%)")
            print(f"   Risk: {stock['risk_level']}")
            print(f"   Key Factors: {', '.join(stock['key_factors'][:3])}")

        print("\n" + "=" * 70)
        print("🔴 TOP 2 SELL OPPORTUNITIES")
        print("=" * 70)
        for i, stock in enumerate(top_sells[:3], 1):
            print(f"\n{i}. {stock['ticker']} [{stock['decision']}] @ ${stock['price']:.2f}")
            print(f"   Confidence: {stock['confidence']:.0f}% | RSI: {stock.get('rsi', 0):.0f}")
            print(f"   Risk: {stock['risk_level']}")
            print(f"   Key Factors: {', '.join(stock['key_factors'][:3])}")

        print(f"\nStats: {scan_stats['universe']} universe → {scan_stats['analysed']} deep-analysed in {scan_stats['elapsed_s']}s")

        # Send to Discord
        if webhook:
            scan_time = get_eastern_time()
            message = format_discord_message(top_buys, top_sells, scan_time, scan_stats)
            send_discord_alert(
                title="📊 Market Scan Results",
                message=message,
                color=0x0099ff,
                webhook_url=webhook
            )

        print("\n✅ Scan complete!\n")
        return 0

    # Single-shot scheduled jobs (for external schedulers, e.g. Cloud Scheduler
    # triggering a Cloud Run Job — each runs one job and exits, instead of the
    # in-process loop that --monitor uses)
    single_shot_jobs = {
        'hourly_scan': run_hourly_scan,
        'premarket_brief': send_premarket_brief,
        'gap_scan': send_gap_scan,
        'go_no_go': send_go_no_go,
        'stop_loss_check': check_stop_losses,
        'weekly_report': send_weekly_report,
        'closing_recap': send_closing_recap,
    }
    for arg_name, job_fn in single_shot_jobs.items():
        if getattr(args, arg_name):
            logger.info(f"Running scheduled job: {arg_name}")
            try:
                job_fn()
            except Exception as e:
                logger.error(f"Job '{arg_name}' failed: {e}")
                return 1
            logger.info(f"✓ Job '{arg_name}' complete")
            return 0

    # Monitor mode - hourly updates
    if args.monitor:
        logger.info("\n🔄 MONITOR MODE ACTIVATED")
        logger.info("Schedule: pre-market 9 AM, hourly scans 10 AM-3 PM, recap 3:45 PM")
        logger.info("Press Ctrl+C to stop\n")

        # Run initial scan if market is open
        if is_market_hours():
            logger.info("Market is open, running initial scan...")
            run_hourly_scan()
        else:
            logger.info("Market is closed. Waiting for market hours...")

        # ET-aware scheduler — fires jobs at the correct Eastern time regardless of server timezone
        eastern = pytz.timezone('US/Eastern')
        _fired: set = set()

        try:
            while True:
                now_et = datetime.now(eastern)
                today = now_et.strftime('%Y-%m-%d')
                hhmm = now_et.strftime('%H:%M')
                hour = now_et.hour

                # Weekly report — Monday 8:55 AM ET (before pre-market brief)
                key = f"weekly-{today}"
                if now_et.weekday() == 0 and hhmm == '08:55' and key not in _fired:
                    _fired.add(key)
                    logger.info("Firing weekly performance report (Monday 8:55 AM ET)")
                    threading.Thread(target=send_weekly_report, daemon=True).start()

                # Pre-market brief at 9:00 AM ET
                key = f"premarket-{today}"
                if hhmm == '09:00' and key not in _fired:
                    _fired.add(key)
                    logger.info("Firing pre-market brief (9:00 AM ET)")
                    threading.Thread(target=send_premarket_brief, daemon=True).start()

                # Gap scan at 9:45 AM ET — catches opening moves
                key = f"gapscan-{today}"
                if hhmm == '09:45' and key not in _fired:
                    _fired.add(key)
                    logger.info("Firing gap scan (9:45 AM ET)")
                    threading.Thread(target=send_gap_scan, daemon=True).start()

                # Go/No-Go signal at 9:50 AM ET — always fires, includes VIX + regime + sector breadth
                key = f"gonogo-{today}"
                if hhmm == '09:50' and key not in _fired:
                    _fired.add(key)
                    threading.Thread(target=send_go_no_go, daemon=True).start()

                # Hourly scans at :00 during 10 AM – 3 PM ET
                key = f"scan-{today}-{hour}"
                if now_et.minute == 0 and 10 <= hour <= 15 and key not in _fired:
                    _fired.add(key)
                    logger.info(f"Firing hourly scan ({hour}:00 ET)")
                    threading.Thread(target=run_hourly_scan, daemon=True).start()

                # Stop loss / target check every 5 minutes during market hours
                if is_market_hours() and now_et.minute % 5 == 0:
                    key = f"sl-{today}-{hour}-{now_et.minute}"
                    if key not in _fired:
                        _fired.add(key)
                        threading.Thread(target=check_stop_losses, daemon=True).start()

                # Closing recap at 3:45 PM ET
                key = f"recap-{today}"
                if hhmm == '15:45' and key not in _fired:
                    _fired.add(key)
                    logger.info("Firing closing recap (3:45 PM ET)")
                    threading.Thread(target=send_closing_recap, daemon=True).start()

                # Clean up fired keys from previous days — keep only today's to prevent
                # duplicate scans. Never use _fired.clear() which would wipe today's keys.
                if len(_fired) > 200:
                    _fired = {k for k in _fired if today in k}

                time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            logger.info("\n\nMonitor stopped by user")
            return 0

    # No arguments - show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
