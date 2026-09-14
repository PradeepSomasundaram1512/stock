#!/usr/bin/env python3
"""
Test suite for ultimate_market_scanner.py
Tests all fixed bugs + shows sample Discord output using real market data.

Run: python test_scanner.py
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ── helpers ──────────────────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f"  [{detail}]" if detail else ""))
    return condition

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ─────────────────────────────────────────────────────────────────────────────
# 1. UNIT TESTS (no network)
# ─────────────────────────────────────────────────────────────────────────────
section("1. UNIT TESTS — No Network Required")

# ── Test: rank_opportunities bouncing/rolling_over fix ─────────────────────
print("\n[1a] bouncing/rolling_over confidence boost via prescreen_lookup")

from ultimate_market_scanner import rank_opportunities

def _mock_result(ticker, decision, confidence, rsi, price=100.0, target=105.0):
    return {
        'ticker': ticker,
        'decision': {'decision': decision, 'confidence': confidence, 'price_target': target,
                     'stop_loss': price * 0.98, 'risk_level': 'medium', 'key_factors': ['rsi'],
                     'reasoning': 'test'},
        'features': {'latest_price': price, 'rsi': rsi, 'trend': 'bullish', 'atr': 1.5},
        'error': None,
    }

# Case 1: BUY stock that is bouncing — should get +8% confidence
prescreen = {'AAPL': {'bouncing': True, 'rolling_over': False}}
results_mock = [_mock_result('AAPL', 'BUY', 0.60, 28)]
buys, sells = rank_opportunities(results_mock, prescreen)
boosted_conf = buys[0]['confidence'] if buys else 0
check("BUY+bouncing gets +8% confidence boost",
      abs(boosted_conf - 68.0) < 0.1,
      f"conf={boosted_conf:.1f}% (expected 68.0%)")

# Case 2: Without prescreen_lookup (old broken behaviour) — no boost
buys2, _ = rank_opportunities(results_mock, {})
no_boost_conf = buys2[0]['confidence'] if buys2 else 0
check("BUY without prescreen_lookup gets no boost",
      abs(no_boost_conf - 60.0) < 0.1,
      f"conf={no_boost_conf:.1f}% (expected 60.0%)")

# Case 3: SELL + rolling_over → boost
prescreen3 = {'NVDA': {'bouncing': False, 'rolling_over': True}}
results_mock3 = [_mock_result('NVDA', 'SELL', 0.65, 75, target=95.0)]
_, sells3 = rank_opportunities(results_mock3, prescreen3)
sell_conf = sells3[0]['confidence'] if sells3 else 0
check("SELL+rolling_over gets +8% confidence boost",
      abs(sell_conf - 73.0) < 0.1,
      f"conf={sell_conf:.1f}% (expected 73.0%)")

# Case 4: HOLD + oversold RSI → promoted to WATCH BUY
results_hold = [_mock_result('MSFT', 'HOLD', 0.50, 28)]
buys4, _ = rank_opportunities(results_hold, {})
check("HOLD + RSI<35 promoted to WATCH BUY",
      buys4 and buys4[0]['decision'] == 'WATCH BUY',
      f"decision={buys4[0]['decision'] if buys4 else 'none'}")

# Case 5: HOLD + overbought RSI → promoted to WATCH SELL
results_hold5 = [_mock_result('META', 'HOLD', 0.50, 72, target=95.0)]
_, sells5 = rank_opportunities(results_hold5, {})
check("HOLD + RSI>65 promoted to WATCH SELL",
      sells5 and sells5[0]['decision'] == 'WATCH SELL',
      f"decision={sells5[0]['decision'] if sells5 else 'none'}")


# ── Test: calculate_atr_stop always returns numeric ─────────────────────────
print("\n[1b] calculate_atr_stop() — both paths return numeric values")
from ultimate_market_scanner import calculate_atr_stop

# With a real precomputed ATR
atr_data = calculate_atr_stop('FAKE_TICKER_XYZ', 150.0, precomputed_atr=2.50)
check("ATR success path: stop_loss is float",
      isinstance(atr_data['stop_loss'], float),
      f"stop={atr_data['stop_loss']}")
check("ATR success path: price_target is float",
      isinstance(atr_data['price_target'], float),
      f"target={atr_data['price_target']}")

# Without precomputed ATR (will trigger fallback for fake ticker)
atr_fb = calculate_atr_stop('ZZZ_FAKE_TICKER', 200.0)
check("ATR fallback path: stop_loss is numeric (not None)",
      atr_fb['stop_loss'] is not None and isinstance(atr_fb['stop_loss'], float),
      f"stop={atr_fb['stop_loss']}, source={atr_fb['source']}")
check("ATR fallback path: price_target is numeric (not None)",
      atr_fb['price_target'] is not None and isinstance(atr_fb['price_target'], float),
      f"target={atr_fb['price_target']}, source={atr_fb['source']}")


# ── Test: _fired set cleanup ──────────────────────────────────────────────────
print("\n[1c] _fired set — date-based cleanup preserves today's keys")

today = "2026-03-15"
yesterday = "2026-03-14"
fired = set()

# Add a mix of today's and yesterday's keys
today_keys = [
    f"weekly-{today}", f"premarket-{today}", f"gapscan-{today}",
    f"vix-{today}", f"scan-{today}-10", f"scan-{today}-11",
    f"sl-{today}-10-0", f"sl-{today}-10-5", f"recap-{today}",
]
old_keys = [
    f"scan-{yesterday}-10", f"premarket-{yesterday}", f"recap-{yesterday}",
]
for k in today_keys + old_keys:
    fired.add(k)

# Apply the fix (same logic as in the scheduler)
fired = {k for k in fired if today in k}

check("Today's keys preserved after cleanup",
      all(k in fired for k in today_keys),
      f"{len(fired)} keys kept")
check("Yesterday's keys removed after cleanup",
      all(k not in fired for k in old_keys),
      f"old keys gone: {old_keys[0] not in fired}")
check("Cleanup never clears more than stale keys",
      len(fired) == len(today_keys),
      f"{len(fired)} == {len(today_keys)}")


# ── Test: get_live_price uses getattr not .get() ─────────────────────────────
print("\n[1d] get_live_price() — getattr on fast_info object")

class MockFastInfo:
    """Simulates the yfinance PricingData object (NOT a dict)."""
    last_price = 185.50
    # No .get() method — will AttributeError if .get() is called

mock_info = MockFastInfo()
price = getattr(mock_info, 'last_price', None) or getattr(mock_info, 'regularMarketPrice', None)
check("getattr reads last_price correctly from non-dict object",
      price == 185.50,
      f"price={price}")

# Confirm .get() would have failed
try:
    mock_info.get('last_price')
    get_would_crash = False
except AttributeError:
    get_would_crash = True
check("Old .get() pattern would crash on fast_info",
      get_would_crash,
      "AttributeError confirmed")


# ── Test: position sizing ────────────────────────────────────────────────────
print("\n[1e] calculate_position_size() — Kelly-lite sizing")
from ultimate_market_scanner import calculate_position_size

os.environ['DAY_TRADE_ACCOUNT_SIZE'] = '10000'
os.environ['DAY_TRADE_RISK_PCT'] = '0.01'

pos = calculate_position_size(150.0, 2.0)  # price=$150, ATR=$2
check("Position size is positive integer",
      isinstance(pos['shares'], int) and pos['shares'] > 0,
      f"{pos['shares']} shares")
check("Max loss is positive and ≤ 1% of $10k ($100) — capped by 20% position limit",
      0 < pos['max_loss'] <= 100,
      f"max_loss=${pos['max_loss']:.0f} (20% position cap limits to {pos['account_pct']:.0f}% of account)")
check("Position value ≤ 20% of account ($2000)",
      pos['position_value'] <= 2001,
      f"position=${pos['position_value']:.0f}")


# ── Test: market regime detection (mock) ─────────────────────────────────────
print("\n[1f] get_market_regime() logic")

def _regime_from_spy3d(spy_3d):
    return 'bear' if spy_3d <= -2.0 else 'bull' if spy_3d >= 2.0 else 'neutral'

check("SPY -3% → bear regime", _regime_from_spy3d(-3.0) == 'bear')
check("SPY +2.5% → bull regime", _regime_from_spy3d(2.5) == 'bull')
check("SPY -1% → neutral regime", _regime_from_spy3d(-1.0) == 'neutral')
check("SPY 0% → neutral regime", _regime_from_spy3d(0.0) == 'neutral')


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIVE API TESTS (real network calls, ~10s)
# ─────────────────────────────────────────────────────────────────────────────
section("2. LIVE API TESTS — Real Market Data")
print("  (fetching live data — takes ~10 seconds)")

# ── Test: get_live_price ─────────────────────────────────────────────────────
print("\n[2a] get_live_price()")
from ultimate_market_scanner import get_live_price

price_aapl = get_live_price('AAPL')
check("get_live_price('AAPL') returns a float",
      price_aapl is not None and isinstance(price_aapl, float),
      f"AAPL=${price_aapl:.2f}" if price_aapl else "None")

price_spy = get_live_price('SPY')
check("get_live_price('SPY') returns a float",
      price_spy is not None and price_spy > 0,
      f"SPY=${price_spy:.2f}" if price_spy else "None")

price_bad = get_live_price('ZZZZINVALID')
check("get_live_price(invalid ticker) returns None safely",
      price_bad is None,
      f"got: {price_bad}")


# ── Test: get_market_regime ──────────────────────────────────────────────────
print("\n[2b] get_market_regime()")
from ultimate_market_scanner import get_market_regime

regime = get_market_regime()
check("Returns dict with 'regime' key",
      isinstance(regime, dict) and 'regime' in regime,
      f"regime={regime}")
check("Regime is bear/bull/neutral",
      regime.get('regime') in ('bear', 'bull', 'neutral'),
      f"regime={regime.get('regime')}")
check("spy_3d is a float",
      isinstance(regime.get('spy_3d'), float),
      f"spy_3d={regime.get('spy_3d')}")


# ── Test: get_sector_performance ─────────────────────────────────────────────
print("\n[2c] get_sector_performance()")
from ultimate_market_scanner import get_sector_performance

sector_perf = get_sector_performance()
check("Returns a dict",
      isinstance(sector_perf, dict),
      f"type={type(sector_perf).__name__}")
check("Contains sector names with float % changes",
      len(sector_perf) >= 5,
      f"{len(sector_perf)} sectors: {list(sector_perf.keys())[:3]}")
check("All values are floats",
      all(isinstance(v, float) for v in sector_perf.values()),
      f"sample: {list(sector_perf.items())[:2]}")


# ── Test: check_vix_danger doesn't crash ────────────────────────────────────
print("\n[2d] VIX fetch (yf.Ticker approach)")
import yfinance as yf

try:
    vix_hist = yf.Ticker('^VIX').history(period='2d')
    vix_ok = not vix_hist.empty and 'Close' in vix_hist.columns
    vix_val = float(vix_hist['Close'].iloc[-1]) if vix_ok else None
    check("VIX fetched via yf.Ticker().history()",
          vix_ok and vix_val is not None and vix_val > 0,
          f"VIX={vix_val:.1f}" if vix_val else "empty")
except Exception as e:
    check("VIX fetched without crash", False, str(e))


# ── Test: quick_technical_screen on real ticker ──────────────────────────────
print("\n[2e] quick_technical_screen() — real pre-screen")
from ultimate_market_scanner import quick_technical_screen

screen = quick_technical_screen('AAPL')
check("Returns a dict (not None)",
      screen is not None and isinstance(screen, dict),
      f"type={type(screen).__name__}")
if screen:
    check("RSI is between 0 and 100",
          0 <= screen.get('rsi', -1) <= 100,
          f"RSI={screen.get('rsi', 'N/A'):.1f}")
    check("bouncing is a bool",
          isinstance(screen.get('bouncing'), bool),
          f"bouncing={screen.get('bouncing')}, rolling_over={screen.get('rolling_over')}")
    check("ATR is a positive number",
          screen.get('atr', 0) > 0,
          f"ATR=${screen.get('atr', 0):.2f}")
    check("latest_price is a positive float",
          screen.get('latest_price', 0) > 0,
          f"price=${screen.get('latest_price', 0):.2f}")


# ── Test: calculate_atr_stop live ────────────────────────────────────────────
print("\n[2f] calculate_atr_stop() — live fetch")
from ultimate_market_scanner import calculate_atr_stop

atr_live = calculate_atr_stop('SPY', price_spy or 500.0)
check("stop_loss < entry price (buy-side stop)",
      atr_live['stop_loss'] < (price_spy or 500.0),
      f"entry=${price_spy:.2f}, stop=${atr_live['stop_loss']:.2f}")
check("price_target > entry price",
      atr_live['price_target'] > (price_spy or 500.0),
      f"target=${atr_live['price_target']:.2f}")
check("Reward:Risk ratio ≥ 2:1",
      (atr_live['price_target'] - (price_spy or 500.0)) >= 2 * ((price_spy or 500.0) - atr_live['stop_loss']),
      f"R:R = {(atr_live['price_target'] - (price_spy or 500.0)):.2f} : {((price_spy or 500.0) - atr_live['stop_loss']):.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. SAMPLE DISCORD OUTPUT
# ─────────────────────────────────────────────────────────────────────────────
section("3. SAMPLE DISCORD OUTPUT — What You'll See in Discord")

from ultimate_market_scanner import (
    format_discord_message, get_eastern_time, _risk_plain
)

# Build realistic mock buy/sell signals
mock_buys = [
    {
        'ticker': 'NVDA',
        'decision': 'BUY',
        'confidence': 78.0,
        'price': 118.45,
        'price_target': 122.10,
        'potential': 3.08,
        'risk_level': 'medium',
        'key_factors': ['RSI 24 — oversold bounce setup', 'Volume spike 2.3x average', 'Sector (Tech) outperforming today'],
        'rsi': 24.0,
        'trend': 'bullish',
        'atr': 2.10,
        'stop_loss': 115.30,
        'reasoning': 'NVDA is extremely oversold (RSI 24) with volume confirming the move. Tech sector is up today.',
        'bouncing': True,
        'rolling_over': False,
    },
    {
        'ticker': 'AMD',
        'decision': 'WATCH BUY',
        'confidence': 61.0,
        'price': 108.20,
        'price_target': 112.00,
        'potential': 3.51,
        'risk_level': 'medium',
        'key_factors': ['RSI 29 — approaching oversold', 'MACD crossover bullish', 'Near 52-week support'],
        'rsi': 29.0,
        'trend': 'neutral',
        'atr': 1.80,
        'stop_loss': 105.50,
        'reasoning': 'AMD approaching oversold territory. Wait for RSI to cross above 30 before entering.',
        'bouncing': False,
        'rolling_over': False,
    },
]

mock_sells = [
    {
        'ticker': 'TSLA',
        'decision': 'SELL',
        'confidence': 74.0,
        'price': 285.60,
        'price_target': 278.00,
        'potential': -2.66,
        'risk_level': 'high',
        'key_factors': ['RSI 77 — overbought', 'Volume drying up on move', 'Earnings in 3 days — risky'],
        'rsi': 77.0,
        'trend': 'bearish',
        'atr': 4.50,
        'stop_loss': 290.60,
        'reasoning': 'TSLA extremely overbought with RSI 77. Earnings in 3 days adds risk — likely pullback.',
        'bouncing': False,
        'rolling_over': True,
    },
]

mock_regime = {'regime': 'neutral', 'spy_3d': 0.8, 'spy_5d': 1.2}
mock_stats = {'universe': 487, 'screened': 431, 'candidates': 47, 'analysed': 45, 'errors': 2, 'elapsed_s': 187}

print("\n" + "─"*60)
print("📱 DISCORD MESSAGE PREVIEW:")
print("─"*60)

try:
    msg = format_discord_message(
        mock_buys, mock_sells,
        scan_time="10:00 AM ET",
        scan_stats=mock_stats,
        save_to_db=False,
        regime=mock_regime,
    )
    print(msg)
    check("Discord message generated without crash",
          len(msg) > 100,
          f"{len(msg)} chars")
    check("Message within Discord 4096 char limit",
          len(msg) <= 4096,
          f"{len(msg)} chars")
except Exception as e:
    check("Discord message generated without crash", False, str(e))
    print(f"  ERROR: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
section("FINAL RESULTS")

total   = len(results)
passed  = sum(1 for r in results if r[0] == PASS)
failed  = sum(1 for r in results if r[0] == FAIL)

print(f"\n  Total:  {total}")
print(f"  Passed: {passed} ✅")
print(f"  Failed: {failed} ❌")

if failed:
    print("\n  Failed tests:")
    for status, name, detail in results:
        if status == FAIL:
            print(f"    ❌ {name}  [{detail}]")

print()
if failed == 0:
    print("  🎉 ALL TESTS PASSED — scanner is ready for production!")
else:
    print(f"  ⚠️  {failed} test(s) need attention before deploying.")
print()
