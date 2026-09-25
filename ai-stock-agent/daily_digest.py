"""
End-of-day health digest posted to Discord: did today's scans run, did the model calls
actually work, what did they decide, and what did the shadow model cost.

Exists because this system once ran for months with every model call failing and every
job exiting 0; a positive daily "N of N calls answered" line makes that visible.

Usage:  python daily_digest.py [YYYY-MM-DD]   (default: today, UTC)
        python daily_digest.py --print        (print instead of posting)
"""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ICON = {"ok": "✅", "warn": "⚠️", "none": "ℹ️"}
COLOR = {"ok": 0x2ECC71, "warn": 0xFF9900, "none": 0x95A5A6}
DB = Path(__file__).parent / "data" / "backtest.db"


def summarize(day: str, db: Path = DB) -> dict:
    con = sqlite3.connect(db)
    q = lambda sql, *a: con.execute(sql, a).fetchone()
    like = f"{day}%"
    scans, total, ok, fb, buys, in_list = q(
        "select count(distinct scan_id), count(*), sum(llm_status='ok'), sum(llm_status='fallback_error'), "
        "sum(raw_decision='BUY' and llm_status='ok'), sum(in_signal_list=1) "
        "from llm_decisions where decided_at like ?", like)
    out = {"day": day, "scans": scans or 0, "decisions": total or 0, "ok": ok or 0, "fallbacks": fb or 0,
           "buys": buys or 0, "signals": in_list or 0}
    top = con.execute(
        "select ticker, max(raw_confidence) c from llm_decisions where decided_at like ? and in_signal_list=1 "
        "and raw_confidence is not null group by ticker order by c desc limit 5", (like,)).fetchall()
    out["top"] = [f"{t} {c:.0%}" for t, c in top]
    try:
        n, sok, cost, agree, both = q(
            "select count(*), sum(s.llm_status='ok'), sum(s.est_cost_usd), "
            "sum(s.llm_status='ok' and p.llm_status='ok' and s.decision=p.raw_decision), "
            "sum(s.llm_status='ok' and p.llm_status='ok') "
            "from shadow_decisions s left join llm_decisions p on p.scan_id=s.scan_id and p.ticker=s.ticker "
            "where s.decided_at like ?", like)
        out["shadow"] = {"n": n or 0, "ok": sok or 0, "cost": cost or 0.0, "agree": agree or 0, "both": both or 0}
    except sqlite3.OperationalError:
        out["shadow"] = None
    return out


def render(s: dict) -> tuple[str, str]:
    """Returns (text, status) with status one of ok / warn / none."""
    if s["decisions"] == 0:
        return f"No model decisions were logged on {s['day']} (market holiday, or the scans did not run).", "none"
    rate = s["fallbacks"] / s["decisions"]
    status = "ok" if rate < 0.10 else "warn"
    lines = [
        f"**{s['scans']} scans** analysed **{s['decisions']}** candidates: {s['ok']} answered by the model, "
        f"{s['fallbacks']} fell back to HOLD ({rate:.0%})",
        f"{s['buys']} BUY calls, {s['signals']} reached the ranked signal lists"
        + (f" (top: {', '.join(s['top'])})" if s["top"] else ""),
    ]
    sh = s.get("shadow")
    if sh and sh["n"]:
        lines.append(f"Shadow model: {sh['ok']}/{sh['n']} answered, agreed with production on "
                     f"{sh['agree']}/{sh['both']}, cost ${sh['cost']:.3f} today")
    if status == "warn":
        lines.append("⚠️ Fallback rate is high: model calls are failing (quota or outage), so these are not real decisions.")
    return "\n".join(lines), status


def chain_update() -> tuple:
    """Commit completed days to the public tamper-evident chain (track_record.py); (line, problem?)."""
    try:
        import track_record as tr
        d = DB.parent
        r = tr.update(DB, d / "track_record_chain.json", d / "public_revealed.csv")
        if not r["days"]:
            return "Track record: the first day is committed once it is complete (tomorrow)", False
        return (f"Track record: {r['days']} days committed, chain head `{r['head'][:16]}`"
                + (f" (+{r['new_days']} new)" if r["new_days"] else "")), False
    except Exception as e:      # noqa: BLE001 - reported loudly, but must not fail the digest
        return f"⚠️ Track-record chain problem: {type(e).__name__}: {e}", True


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = args[0] if args else datetime.utcnow().strftime("%Y-%m-%d")
    text, status = render(summarize(day))
    if "--print" not in sys.argv:
        line, problem = chain_update()
        text += "\n" + line
        if problem:
            status = "warn"
    if "--print" in sys.argv:
        print(text)
        return 0
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print(text)
        return 0
    import requests
    body = {"embeds": [{"title": f"{ICON[status]} Daily health digest, {day}",
                        "description": text, "color": COLOR[status]}]}
    try:
        requests.post(webhook, json=body, timeout=10)
    except Exception as exc:  # noqa: BLE001 - a failed digest must not fail the job
        print(f"digest: could not post to Discord: {exc}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
