"""
DB Manager — Recommendation tracking for day-trading performance.
All reads/writes go through this module so the schema stays consistent.
"""

import sqlite3
import os
import logging
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "backtest.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def migrate_schema():
    """
    Idempotent schema migration — adds new columns and tables needed for
    day-trading tracking. Safe to call on every startup.
    """
    conn = get_connection()
    try:
        new_columns = [
            ("atr",              "REAL"),
            ("atr_stop_pct",     "REAL"),
            ("position_shares",  "INTEGER"),
            ("position_value",   "REAL"),
            ("account_size",     "REAL"),
            ("earnings_days",    "INTEGER"),
            ("earnings_warning", "BOOLEAN DEFAULT 0"),
            ("scan_type",        "TEXT DEFAULT 'hourly'"),
            ("scan_interval",    "TEXT DEFAULT '60m'"),
        ]
        existing = {row[1] for row in conn.execute("PRAGMA table_info(recommendations)")}
        for col_name, col_def in new_columns:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE recommendations ADD COLUMN {col_name} {col_def}")
                logger.info(f"Added column recommendations.{col_name}")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_recap (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                recap_date      DATE NOT NULL,
                ticker          TEXT NOT NULL,
                decision        TEXT NOT NULL,
                entry_price     REAL,
                exit_price      REAL,
                stop_loss       REAL,
                price_target    REAL,
                hit_target      BOOLEAN DEFAULT 0,
                hit_stop        BOOLEAN DEFAULT 0,
                profit_loss_pct REAL,
                outcome         TEXT,
                rec_id          INTEGER REFERENCES recommendations(id),
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Candidate-level log of EVERY analysis the LLM stage handled (BUY/SELL/HOLD and
        # exception fallbacks), with the inputs it saw. `recommendations` only keeps the
        # signals that survived ranking, so it cannot show what the model rejected, which
        # decisions were fallbacks, or what news/fundamentals it was given.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_decisions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id          TEXT NOT NULL,
                decided_at       TEXT NOT NULL,
                ticker           TEXT NOT NULL,
                llm_status       TEXT,
                model            TEXT,
                latency_s        REAL,
                error            TEXT,
                raw_decision     TEXT,
                raw_confidence   REAL,
                price_target     REAL,
                stop_loss        REAL,
                risk_level       TEXT,
                time_horizon     TEXT,
                key_factors      TEXT,
                reasoning        TEXT,
                price            REAL,
                rsi              REAL,
                trend            TEXT,
                atr              REAL,
                pre_rsi          REAL,
                pre_vol_ratio    REAL,
                pre_momentum_5h  REAL,
                pre_interest     REAL,
                pe_ratio         REAL,
                valuation_score  REAL,
                health_score     REAL,
                growth_score     REAL,
                news_sentiment   TEXT,
                news_score       REAL,
                news_count       INTEGER,
                market_trend     TEXT,
                tokens_in        INTEGER,
                tokens_out       INTEGER,
                final_decision   TEXT,
                final_confidence REAL,
                in_signal_list   INTEGER DEFAULT 0
            )
        """)
        existing_ld = {row[1] for row in conn.execute("PRAGMA table_info(llm_decisions)")}
        for col_name, col_def in (("tokens_in", "INTEGER"), ("tokens_out", "INTEGER")):
            if col_name not in existing_ld:
                conn.execute(f"ALTER TABLE llm_decisions ADD COLUMN {col_name} {col_def}")

        # Shadow model: a second model answers the SAME prompt with the SAME stored inputs as
        # the production model, logged here only. It never touches alerts or trading.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shadow_decisions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id          TEXT NOT NULL,
                decided_at       TEXT NOT NULL,
                ticker           TEXT NOT NULL,
                shadow_model     TEXT NOT NULL,
                llm_status       TEXT,
                latency_s        REAL,
                error            TEXT,
                decision         TEXT,
                confidence       REAL,
                price_target     REAL,
                stop_loss        REAL,
                risk_level       TEXT,
                time_horizon     TEXT,
                key_factors      TEXT,
                reasoning        TEXT,
                tokens_in        INTEGER,
                tokens_out       INTEGER,
                est_cost_usd     REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_scan ON shadow_decisions(scan_id, ticker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_time ON shadow_decisions(decided_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_dec_scan ON llm_decisions(scan_id, ticker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_dec_time ON llm_decisions(decided_at)")

        conn.commit()
        logger.info("Schema migration complete")
    except Exception as e:
        logger.error(f"Schema migration error: {e}")
        conn.rollback()
    finally:
        conn.close()


_LLM_DECISION_COLS = (
    "scan_id", "decided_at", "ticker", "llm_status", "model", "latency_s", "error", "raw_decision",
    "raw_confidence", "price_target", "stop_loss", "risk_level", "time_horizon", "key_factors",
    "reasoning", "price", "rsi", "trend", "atr", "pre_rsi", "pre_vol_ratio", "pre_momentum_5h",
    "pre_interest", "pe_ratio", "valuation_score", "health_score", "growth_score", "news_sentiment",
    "news_score", "news_count", "market_trend", "tokens_in", "tokens_out",
)


def save_llm_decisions(rows: List[Dict[str, Any]]) -> int:
    """Insert one row per analysed candidate. Never raises: logging must not break a scan."""
    if not rows:
        return 0
    conn = get_connection()
    try:
        conn.executemany(
            f"INSERT INTO llm_decisions ({','.join(_LLM_DECISION_COLS)}) VALUES ({','.join('?' * len(_LLM_DECISION_COLS))})",
            [tuple(r.get(c) for c in _LLM_DECISION_COLS) for r in rows],
        )
        conn.commit()
        return len(rows)
    except Exception as e:
        logger.error(f"save_llm_decisions failed: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


_SHADOW_COLS = (
    "scan_id", "decided_at", "ticker", "shadow_model", "llm_status", "latency_s", "error", "decision",
    "confidence", "price_target", "stop_loss", "risk_level", "time_horizon", "key_factors", "reasoning",
    "tokens_in", "tokens_out", "est_cost_usd",
)


def save_shadow_decisions(rows: List[Dict[str, Any]]) -> int:
    """Insert shadow-model rows. Never raises."""
    if not rows:
        return 0
    conn = get_connection()
    try:
        conn.executemany(
            f"INSERT INTO shadow_decisions ({','.join(_SHADOW_COLS)}) VALUES ({','.join('?' * len(_SHADOW_COLS))})",
            [tuple(r.get(c) for c in _SHADOW_COLS) for r in rows],
        )
        conn.commit()
        return len(rows)
    except Exception as e:
        logger.error(f"save_shadow_decisions failed: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def shadow_spent_today_usd() -> float:
    """Estimated shadow spend so far today (UTC), summed from what was actually logged."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(est_cost_usd), 0) FROM shadow_decisions WHERE date(decided_at) = date('now')"
        ).fetchone()
        return float(row[0] or 0.0)
    except Exception as e:
        logger.error(f"shadow_spent_today_usd failed: {e}")
        return float("inf")     # unknown spend -> behave as if the budget is gone
    finally:
        conn.close()


def mark_final_signals(scan_id: str, finals: List[Dict[str, Any]]) -> None:
    """Record the post-gate label/confidence for candidates that reached the ranked lists."""
    if not finals:
        return
    conn = get_connection()
    try:
        conn.executemany(
            "UPDATE llm_decisions SET final_decision=?, final_confidence=?, in_signal_list=1 "
            "WHERE scan_id=? AND ticker=?",
            [(f.get("decision"), (f.get("confidence") or 0) / 100, scan_id, f.get("ticker")) for f in finals],
        )
        conn.commit()
    except Exception as e:
        logger.error(f"mark_final_signals failed: {e}")
        conn.rollback()
    finally:
        conn.close()


def save_recommendation(
    stock: Dict[str, Any],
    atr_data: Dict[str, Any],
    pos_data: Dict[str, Any],
    earnings_data: Dict[str, Any],
    scan_type: str = "hourly",
) -> Optional[int]:
    """
    Persist a single BUY or SELL recommendation.
    Returns the new row id, or None on failure.
    """
    conn = get_connection()
    try:
        row = conn.execute("""
            INSERT INTO recommendations (
                ticker, recommendation_date, decision, confidence,
                entry_price, price_target, stop_loss, risk_level, time_horizon,
                reasoning, key_factors, rsi, trend,
                atr, atr_stop_pct, position_shares, position_value, account_size,
                earnings_days, earnings_warning, scan_type, scan_interval,
                is_closed
            ) VALUES (
                ?,?,?,?,  ?,?,?,?,?,  ?,?,?,?,  ?,?,?,?,?,  ?,?,?,?,  0
            )
        """, (
            stock.get("ticker"),
            datetime.now().isoformat(),
            stock.get("decision"),
            stock.get("confidence", 0) / 100,   # stored 0-1

            stock.get("price"),
            atr_data.get("price_target") or stock.get("price_target"),
            atr_data.get("stop_loss") or stock.get("stop_loss"),
            stock.get("risk_level", "medium"),
            "intraday (today only)",

            ", ".join(stock.get("key_factors", [])),
            json.dumps(stock.get("key_factors", [])),
            stock.get("rsi"),
            stock.get("trend"),

            atr_data.get("atr"),
            atr_data.get("stop_pct"),
            pos_data.get("shares"),
            pos_data.get("position_value"),
            pos_data.get("account_size"),

            earnings_data.get("days_away"),
            1 if earnings_data.get("warning") else 0,
            scan_type,
            "60m",
        ))
        conn.commit()
        rec_id = row.lastrowid
        logger.info(f"Saved recommendation #{rec_id}: {stock.get('ticker')} {stock.get('decision')}")
        return rec_id
    except Exception as e:
        logger.error(f"Failed to save recommendation: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def close_todays_recs(current_prices: Dict[str, float]):
    """
    Mark all open recommendations from today as closed using current_prices.
    Computes P&L and outcome (WIN / LOSS / STOPPED_OUT).
    """
    conn = get_connection()
    try:
        today = date.today().isoformat()
        open_recs = conn.execute(
            "SELECT id, ticker, decision, entry_price, stop_loss, price_target "
            "FROM recommendations WHERE is_closed=0 AND date(recommendation_date)=?",
            (today,)
        ).fetchall()

        for rec in open_recs:
            rec_id, ticker, decision, entry, stop, target = (
                rec["id"], rec["ticker"], rec["decision"],
                rec["entry_price"], rec["stop_loss"], rec["price_target"]
            )
            exit_price = current_prices.get(ticker, entry)
            if not entry or entry == 0:
                continue

            pnl_pct = (exit_price - entry) / entry * 100
            is_sell = str(decision).upper() in ("SELL", "WATCH SELL")
            if is_sell:
                pnl_pct = -pnl_pct   # profit for SELL = price going down

            # Stop logic differs by direction:
            #   BUY  stopped out when price drops to/below stop (stop < entry)
            #   SELL stopped out when price rises to/above stop (stop > entry)
            if is_sell:
                stopped = stop and exit_price >= stop
                won     = target and exit_price <= target
            else:
                stopped = stop and exit_price <= stop
                won     = target and exit_price >= target

            if stopped:
                outcome = "STOPPED_OUT"
            elif won:
                outcome = "WIN"
            elif pnl_pct > 0:
                outcome = "WIN"
            elif pnl_pct < 0:
                outcome = "LOSS"
            else:
                outcome = "FLAT"

            conn.execute("""
                UPDATE recommendations
                SET is_closed=1, exit_date=?, exit_price=?, profit_loss_pct=?, outcome=?,
                    exit_reason='end_of_day'
                WHERE id=?
            """, (datetime.now().isoformat(), exit_price, round(pnl_pct, 2), outcome, rec_id))

        conn.commit()
        logger.info(f"Closed {len(open_recs)} recommendations for {today}")
    except Exception as e:
        logger.error(f"Failed to close recs: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_todays_recs() -> List[sqlite3.Row]:
    """Return all recommendations (open or closed) from today."""
    conn = get_connection()
    try:
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE date(recommendation_date)=? ORDER BY recommendation_date",
            (today,)
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_open_recs(since_days: int = 1) -> List[sqlite3.Row]:
    """Return all still-open recommendations within last N days."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE is_closed=0 "
            "AND recommendation_date >= datetime('now', ?) "
            "ORDER BY recommendation_date DESC",
            (f"-{int(since_days)} days",)
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_weekly_recs(days: int = 7) -> List[sqlite3.Row]:
    """Return all closed recommendations from the last N days — used for weekly performance report."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE is_closed=1 "
            "AND recommendation_date >= datetime('now', ?) "
            "ORDER BY recommendation_date DESC",
            (f"-{days} days",)
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_ticker_win_rates(min_trades: int = 5) -> Dict[str, float]:
    """
    Return historical win rate per ticker (only for tickers with >= min_trades closed trades).
    win_rate = wins / total  (0.0 – 1.0)
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT ticker,
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome IN ('WIN','STOPPED_OUT') AND profit_loss_pct > 0 THEN 1 ELSE 0 END) as wins
            FROM recommendations
            WHERE is_closed = 1 AND outcome IS NOT NULL
            GROUP BY ticker
            HAVING total >= ?
        """, (min_trades,)).fetchall()
        return {row['ticker']: round(row['wins'] / row['total'], 3) for row in rows}
    except Exception:
        return {}
    finally:
        conn.close()


def get_todays_recommended_tickers() -> set:
    """Return tickers already recommended today — used to avoid repeating same stock each hour."""
    conn = get_connection()
    try:
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM recommendations WHERE date(recommendation_date)=?",
            (today,)
        ).fetchall()
        return {row['ticker'] for row in rows}
    except Exception:
        return set()
    finally:
        conn.close()
