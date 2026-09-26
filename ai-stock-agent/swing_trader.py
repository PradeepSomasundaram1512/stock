"""
Swing Trading Engine — Automated weekly swing trading using AI predictions.

How it works:
  1. Scans 40 liquid S&P 500 stocks with 90-day daily data.
  2. Enters paper trades for BUY signals with confidence >= 65%.
  3. Monitors open positions every time it runs; exits on target / stop / 10-day timeout.
  4. Sends Discord notifications for entries and exits.

Usage:
  python swing_trader.py            # run one cycle (scan + monitor)
  python swing_trader.py --status   # show open positions
  python swing_trader.py --history  # show closed trades
  python swing_trader.py --reset    # wipe paper account and start fresh
"""

import json
import logging
import os
import sys
import time
import argparse
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from enhancements.paper_trading import get_paper_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Swing-trader universe: 40 highly liquid large-caps across sectors ──────────
SWING_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",
    # Semiconductors
    "AMD", "AVGO", "QCOM", "TXN", "MU",
    # Software / Cloud
    "CRM", "NOW", "ADBE", "ORCL", "SNOW", "PLTR",
    # Financials
    "JPM", "GS", "MS", "V", "MA",
    # Healthcare / Biotech
    "UNH", "LLY", "ABBV", "JNJ",
    # Industrials / Energy
    "CAT", "DE", "XOM", "CVX",
    # Consumer
    "AMZN", "COST", "MCD", "NKE",
    # ETFs for broad market swings
    "SPY", "QQQ", "IWM",
]
SWING_UNIVERSE = list(dict.fromkeys(SWING_UNIVERSE))  # deduplicate

# ── Parameters ─────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.65   # minimum confidence to enter a trade
MAX_POSITIONS = 5             # maximum simultaneous open swing trades
PORTFOLIO_RISK_PCT = 0.02     # risk 2% of portfolio per trade
MAX_HOLD_DAYS = 10            # auto-exit after this many calendar days
MIN_UPSIDE_PCT = 0.05         # require at least 5% upside to target
STARTING_PORTFOLIO = 10_000   # paper account starting balance ($)

TRADES_FILE = Path(__file__).parent / "data" / "swing_trades.json"


class SwingTradingEngine:
    """Fully automated paper swing trading engine driven by AI predictions."""

    def __init__(self):
        self.paper = get_paper_account(STARTING_PORTFOLIO)
        self.open_trades: Dict[str, Dict] = {}
        self._load_trades()

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_trades(self):
        if TRADES_FILE.exists():
            data = json.loads(TRADES_FILE.read_text())
            self.open_trades = data.get("open_trades", {})
            logger.info(f"Loaded {len(self.open_trades)} open swing positions")

    def _save_trades(self):
        existing = {}
        if TRADES_FILE.exists():
            existing = json.loads(TRADES_FILE.read_text())
        existing["open_trades"] = self.open_trades
        existing.setdefault("closed_trades", [])
        TRADES_FILE.write_text(json.dumps(existing, indent=2))

    def _record_closed_trade(self, trade: Dict):
        data = {}
        if TRADES_FILE.exists():
            data = json.loads(TRADES_FILE.read_text())
        data.setdefault("closed_trades", []).append(trade)
        data["open_trades"] = self.open_trades
        TRADES_FILE.write_text(json.dumps(data, indent=2))

    # ── Price feed ─────────────────────────────────────────────────────────────

    def _get_current_price(self, ticker: str) -> Optional[float]:
        try:
            hist = yf.Ticker(ticker).history(period="2d", interval="1d")
            if hist.empty:
                return None
            return float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.warning(f"Price fetch failed for {ticker}: {e}")
            return None

    # ── Position sizing ─────────────────────────────────────────────────────────

    def _shares_to_buy(self, entry: float, stop: float) -> int:
        """Risk 2% of portfolio on this trade; cap position at 20% of portfolio."""
        portfolio_value = self.paper.cash + sum(
            self.open_trades[t]["entry_price"] * self.open_trades[t]["shares"]
            for t in self.open_trades
        )
        risk_per_share = entry - stop
        if risk_per_share <= 0:
            return 0
        risk_amount = portfolio_value * PORTFOLIO_RISK_PCT
        shares = int(risk_amount / risk_per_share)
        max_shares = int((portfolio_value * 0.20) / entry)
        return max(1, min(shares, max_shares))

    # ── Scan ────────────────────────────────────────────────────────────────────

    def scan_for_opportunities(self) -> List[Dict]:
        """Run daily-chart AI scan; return qualifying BUY setups sorted by score."""
        from ultimate_market_scanner import analyze_stock

        opportunities = []
        already_open = set(self.open_trades.keys())

        for ticker in SWING_UNIVERSE:
            if ticker in already_open:
                continue

            try:
                result = analyze_stock(
                    ticker,
                    period="90d",
                    interval="1d",
                    swing_mode=True,
                )
            except Exception as e:
                logger.warning(f"Scan error for {ticker}: {e}")
                continue

            if not result or result.get("error"):
                continue

            decision = result.get("decision", {})
            if decision.get("decision") != "BUY":
                continue

            confidence = float(decision.get("confidence", 0))
            price = float(result.get("features", {}).get("latest_price") or 0)
            target = decision.get("price_target")
            stop = decision.get("stop_loss")

            if not price or not target or not stop:
                continue
            if confidence < CONFIDENCE_THRESHOLD:
                continue
            upside = (target - price) / price
            if upside < MIN_UPSIDE_PCT:
                continue
            # Reject if stop is farther than 8% away (too wide for a swing trade)
            if (price - stop) / price > 0.08:
                continue

            opportunities.append({
                "ticker": ticker,
                "price": round(price, 2),
                "target": round(float(target), 2),
                "stop": round(float(stop), 2),
                "confidence": round(confidence, 3),
                "upside_pct": round(upside * 100, 1),
                "reasoning": decision.get("reasoning", ""),
                "risk_level": decision.get("risk_level", "medium"),
                "key_factors": decision.get("key_factors", []),
            })
            time.sleep(0.5)  # be polite to rate limits

        # Rank: confidence × upside
        opportunities.sort(
            key=lambda x: x["confidence"] * x["upside_pct"],
            reverse=True,
        )
        logger.info(f"Scan found {len(opportunities)} qualifying swing setups")
        return opportunities

    # ── Enter trade ─────────────────────────────────────────────────────────────

    def enter_trade(self, opp: Dict) -> bool:
        """Place paper buy + record swing bracket."""
        ticker = opp["ticker"]
        entry = opp["price"]
        stop = opp["stop"]
        target = opp["target"]

        shares = self._shares_to_buy(entry, stop)
        if shares < 1:
            logger.warning(f"[{ticker}] Position size is 0 — skipping")
            return False

        if entry * shares > self.paper.cash:
            logger.warning(f"[{ticker}] Not enough cash (need ${entry*shares:.0f}, have ${self.paper.cash:.0f})")
            return False

        result = self.paper.buy(ticker, shares, entry)
        if not result["success"]:
            logger.warning(f"[{ticker}] Paper buy failed: {result.get('error')}")
            return False

        today = date.today().isoformat()
        trade = {
            "ticker": ticker,
            "entry_price": entry,
            "target_price": target,
            "stop_price": stop,
            "shares": shares,
            "entry_date": today,
            "max_exit_date": (date.today() + timedelta(days=MAX_HOLD_DAYS)).isoformat(),
            "confidence": opp["confidence"],
            "upside_pct": opp["upside_pct"],
            "reasoning": opp["reasoning"],
            "risk_level": opp["risk_level"],
            "key_factors": opp["key_factors"],
        }
        self.open_trades[ticker] = trade
        self._save_trades()

        self._discord_entry(trade)
        logger.info(
            f"ENTERED {ticker}: {shares} shares @ ${entry:.2f} | "
            f"target ${target:.2f} (+{opp['upside_pct']:.1f}%) | stop ${stop:.2f}"
        )
        return True

    # ── Monitor / exit ──────────────────────────────────────────────────────────

    def monitor_positions(self) -> List[Dict]:
        """Check all open positions; exit on target / stop / time expiry."""
        exits = []
        today = date.today().isoformat()

        for ticker, trade in list(self.open_trades.items()):
            price = self._get_current_price(ticker)
            if price is None:
                continue

            reason = None
            if price >= trade["target_price"]:
                reason = "TARGET_HIT"
            elif price <= trade["stop_price"]:
                reason = "STOP_HIT"
            elif today >= trade["max_exit_date"]:
                reason = "TIME_EXPIRED"

            if reason:
                result = self.paper.sell(ticker, trade["shares"], price)
                if result["success"]:
                    closed = {
                        **trade,
                        "exit_price": round(price, 2),
                        "exit_date": today,
                        "exit_reason": reason,
                        "pnl": round(result["trade"]["profit_loss"], 2),
                        "pnl_pct": round(result["trade"]["profit_loss_pct"], 2),
                    }
                    exits.append(closed)
                    del self.open_trades[ticker]
                    self._record_closed_trade(closed)
                    self._discord_exit(closed)
                    logger.info(
                        f"EXITED {ticker} [{reason}] @ ${price:.2f} | "
                        f"P/L: ${closed['pnl']:+.2f} ({closed['pnl_pct']:+.1f}%)"
                    )

        self._save_trades()
        return exits

    # ── Main run loop ───────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """One full cycle: monitor existing positions, then scan for new entries."""
        logger.info("=== Swing Trader: Starting cycle ===")

        exits = self.monitor_positions()

        slots = MAX_POSITIONS - len(self.open_trades)
        entered = []

        if slots > 0:
            opportunities = self.scan_for_opportunities()
            for opp in opportunities[:slots]:
                if self.enter_trade(opp):
                    entered.append(opp["ticker"])
        else:
            logger.info(f"Max positions ({MAX_POSITIONS}) reached — skipping scan")

        summary = {
            "exits": [(t["ticker"], t["exit_reason"], t["pnl_pct"]) for t in exits],
            "entered": entered,
            "open_positions": len(self.open_trades),
            "portfolio_cash": round(self.paper.cash, 2),
        }
        logger.info(f"=== Cycle done: {summary} ===")

        self._discord_summary(exits, entered)
        return summary

    # ── Discord helpers ─────────────────────────────────────────────────────────

    def _send_discord(self, title: str, description: str, color: int = 0x00CC66):
        webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not webhook:
            return
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": "Swing Trader • Paper Account"},
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            }]
        }
        try:
            requests.post(webhook, json=payload, timeout=10)
        except Exception as e:
            logger.warning(f"Discord send failed: {e}")

    def _discord_entry(self, trade: Dict):
        upside = ((trade["target_price"] - trade["entry_price"]) / trade["entry_price"]) * 100
        downside = ((trade["entry_price"] - trade["stop_price"]) / trade["entry_price"]) * 100
        rr = upside / downside if downside > 0 else 0
        msg = (
            f"**{trade['ticker']}** — {trade['shares']} shares @ **${trade['entry_price']:.2f}**\n"
            f"🎯 Target: **${trade['target_price']:.2f}** (+{upside:.1f}%)\n"
            f"🛑 Stop:   **${trade['stop_price']:.2f}** (-{downside:.1f}%)\n"
            f"📊 R/R: {rr:.1f}:1 | Confidence: {trade['confidence']*100:.0f}%\n"
            f"⏳ Max hold: {trade['max_exit_date']}\n\n"
            f"_{trade['reasoning']}_"
        )
        self._send_discord("🟢 SWING ENTRY", msg, color=0x00CC66)

    def _discord_exit(self, trade: Dict):
        emoji = "✅" if trade["pnl"] >= 0 else "❌"
        reason_map = {
            "TARGET_HIT": "🎯 Target reached",
            "STOP_HIT": "🛑 Stop triggered",
            "TIME_EXPIRED": "⏰ 10-day time limit",
        }
        reason_text = reason_map.get(trade["exit_reason"], trade["exit_reason"])
        color = 0x00CC66 if trade["pnl"] >= 0 else 0xFF3333
        msg = (
            f"**{trade['ticker']}** closed @ **${trade['exit_price']:.2f}**\n"
            f"{reason_text}\n"
            f"{emoji} P/L: **${trade['pnl']:+.2f}** ({trade['pnl_pct']:+.1f}%)\n"
            f"Entry: ${trade['entry_price']:.2f} | {trade['entry_date']} → {trade['exit_date']}"
        )
        self._send_discord("SWING EXIT", msg, color=color)

    def _discord_summary(self, exits: List[Dict], entered: List[str]):
        if not exits and not entered:
            return
        lines = []
        if entered:
            lines.append(f"**New entries:** {', '.join(entered)}")
        if exits:
            for t in exits:
                sign = "+" if t["pnl"] >= 0 else ""
                lines.append(f"**Closed {t['ticker']}:** {sign}{t['pnl_pct']:.1f}% [{t['exit_reason']}]")
        lines.append(f"Open positions: {len(self.open_trades)}/{MAX_POSITIONS} | Cash: ${self.paper.cash:.0f}")
        self._send_discord("📊 Swing Trader Update", "\n".join(lines), color=0x5865F2)

    # ── CLI helpers ─────────────────────────────────────────────────────────────

    def print_status(self):
        print(f"\n{'='*60}")
        print(f"  SWING TRADER — Paper Account Status")
        print(f"{'='*60}")
        print(f"  Cash available: ${self.paper.cash:,.2f}")
        print(f"  Open positions: {len(self.open_trades)}/{MAX_POSITIONS}")

        if not self.open_trades:
            print("  No open positions.")
        else:
            print(f"\n  {'Ticker':<8} {'Entry':>8} {'Target':>8} {'Stop':>7} {'Shares':>6} {'Max Exit':<12} {'Conf':>6}")
            print(f"  {'-'*62}")
            for t in self.open_trades.values():
                upside = ((t['target_price'] - t['entry_price']) / t['entry_price']) * 100
                print(
                    f"  {t['ticker']:<8} ${t['entry_price']:>7.2f} ${t['target_price']:>7.2f} "
                    f"${t['stop_price']:>6.2f} {t['shares']:>6} {t['max_exit_date']:<12} "
                    f"{t['confidence']*100:>5.0f}%  (+{upside:.1f}%)"
                )
        print()

    def print_history(self, limit: int = 20):
        data = {}
        if TRADES_FILE.exists():
            data = json.loads(TRADES_FILE.read_text())
        closed = data.get("closed_trades", [])[-limit:]

        print(f"\n{'='*70}")
        print(f"  SWING TRADER — Last {len(closed)} Closed Trades")
        print(f"{'='*70}")
        if not closed:
            print("  No closed trades yet.")
        else:
            wins = [t for t in closed if t["pnl"] >= 0]
            total_pnl = sum(t["pnl"] for t in closed)
            print(f"  Win rate: {len(wins)}/{len(closed)} ({len(wins)/len(closed)*100:.0f}%)  |  Total P/L: ${total_pnl:+.2f}")
            print(f"\n  {'Ticker':<8} {'Entry':>8} {'Exit':>8} {'P/L%':>7} {'Reason':<15} {'Date'}")
            print(f"  {'-'*62}")
            for t in reversed(closed):
                sign = "✓" if t["pnl"] >= 0 else "✗"
                print(
                    f"  {sign} {t['ticker']:<6} ${t['entry_price']:>7.2f} ${t['exit_price']:>7.2f} "
                    f"{t['pnl_pct']:>+6.1f}%  {t['exit_reason']:<15} {t['exit_date']}"
                )
        print()


def main():
    parser = argparse.ArgumentParser(description="AI-powered swing trading engine (paper account)")
    parser.add_argument("--status",       action="store_true", help="Show open positions")
    parser.add_argument("--history",      action="store_true", help="Show closed trade history")
    parser.add_argument("--reset",        action="store_true", help="Reset paper account to starting balance")
    parser.add_argument("--scan-only",    action="store_true", help="Scan for opportunities without entering trades")
    parser.add_argument("--monitor-only", action="store_true", help="Only check open positions (fast, no AI scan)")
    args = parser.parse_args()

    engine = SwingTradingEngine()

    if args.reset:
        confirm = input(f"Reset paper account to ${STARTING_PORTFOLIO:,}? This clears all trades. [y/N]: ")
        if confirm.lower() == "y":
            engine.paper.reset_account()
            if TRADES_FILE.exists():
                TRADES_FILE.write_text(json.dumps({"open_trades": {}, "closed_trades": []}, indent=2))
            engine.open_trades = {}
            print("Paper account reset.")
        return

    if args.status:
        engine.print_status()
        return

    if args.history:
        engine.print_history()
        return

    if args.scan_only:
        print("Scanning for swing opportunities (no trades will be placed)...")
        opps = engine.scan_for_opportunities()
        if not opps:
            print("No qualifying opportunities found.")
            return
        print(f"\n{'Ticker':<8} {'Price':>8} {'Target':>8} {'Stop':>7} {'Upside':>8} {'Conf':>6}")
        print("-" * 50)
        for o in opps:
            print(
                f"{o['ticker']:<8} ${o['price']:>7.2f} ${o['target']:>7.2f} "
                f"${o['stop']:>6.2f} {o['upside_pct']:>+7.1f}%  {o['confidence']*100:>5.0f}%"
            )
        return

    if args.monitor_only:
        # Fast path: just check prices on open positions, no AI scan
        exits = engine.monitor_positions()
        if exits:
            logger.info(f"Closed {len(exits)} position(s) this check")
        else:
            logger.info("No exits triggered — all positions within range")
        return

    # Default: full cycle (monitor + AI scan for new entries)
    engine.run()
    engine.print_status()


if __name__ == "__main__":
    main()