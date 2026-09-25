"""
Input ablation: which parts of the model's input actually change its decisions?

Every analysed candidate's exact inputs are logged (input_log.py). Here each is replayed through the SAME production prompt and model with
one group of inputs replaced by the neutral text the prompt already uses when that data is missing:

    control x3          unchanged inputs, three independent runs: the model's own run-to-run randomness (the NOISE FLOOR)
    no_news             news count/sentiment/topics/summary neutralised
    no_fundamentals     P/E, health, growth, analyst fields neutralised
    no_market           market trend, VIX, sector and index moves neutralised
    no_technical        trend/RSI-signal/MACD/volume/volatility/support/summary neutralised
    technical_only      news + fundamentals + market neutralised (only the technical block remains)

The LLM is stochastic (temperature 0.3), so a variant only matters if it changes decisions MORE than a repeat of the control does.
Note: the RAG context is not an ablation group because it never reaches the prompt (agents/autonomous_reasoning_agent.py::_prepare_inputs
does not read it, and the template has no such placeholder).

    python ablation.py run [--sample 0.25] [--limit N] [--budget-usd 1.5]   replay logged inputs (needs OPENAI_API_KEY)
    python ablation.py analyze [--out paper_results/ablation.json]           decision-sensitivity table with intervals
    python ablation.py weekly [--discord]                                    what the weekly cloud job runs: replay a 15% sample within a cap, then summarise
    python ablation.py outcomes                                              once 10-day returns have matured: did removing an input change WHICH BUYs did well?
Results are appended to data/ablation/YYYY-MM-DD.jsonl.gz (one line per candidate x variant x replicate).
"""
import gzip
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
DATA = HERE / "data"
PRICE_IN, PRICE_OUT = 0.15, 0.60           # gpt-4o-mini, USD per 1M tokens (the production model)
CONTROLS = ("control_1", "control_2", "control_3")

NEUTRAL = {
    "news": {"news_count": 0, "news_sentiment": "NEUTRAL", "news_topics": "None", "news_summary": "No recent news available"},
    "fundamentals": {"pe_ratio": "N/A", "health_score": "0.50", "revenue_growth": "N/A", "earnings_growth": "N/A",
                     "analyst_target_price": "N/A", "analyst_count": 0},
    "market": {"market_trend": "NEUTRAL", "market_vix": "N/A", "indices_performance": "  - No data available"},   # sector_performance: see neutralise()
    "technical": {"trend": "neutral", "rsi_signal": "neutral", "macd_signal": "neutral", "volume_signal": "normal", "volatility_level": "unknown",
                  "support_resistance": "N/A", "technical_summary": "No technical summary available"},
}
VARIANTS = {"no_news": ["news"], "no_fundamentals": ["fundamentals"], "no_market": ["market"], "no_technical": ["technical"],
            "technical_only": ["news", "fundamentals", "market"]}
# Robustness: the neutral text above ("neutral", "N/A") is not information-free, so a shift could be an artifact of the wording. These two re-run the
# key ablations with different wording ("Not provided"); an effect that survives both is about the missing input, not the words.
ALT = {"no_news_alt": ["news"], "no_technical_alt": ["technical"]}
ALL_VARIANTS = {**VARIANTS, **ALT}
NOT_PROVIDED = {
    "news": {"news_count": "not provided", "news_sentiment": "NOT PROVIDED", "news_topics": "not provided", "news_summary": "Not provided"},
    "technical": {"trend": "not provided", "rsi_signal": "not provided", "macd_signal": "not provided", "volume_signal": "not provided",
                  "volatility_level": "not provided", "support_resistance": "not provided", "technical_summary": "Not provided"},
}


def neutralise(prompt_inputs: dict, groups: list, sector_default: str = "No sector data available", alt: bool = False) -> dict:
    """Copy of the prompt inputs with the given groups replaced by the neutral text used for missing data (or the alternative wording)."""
    out = dict(prompt_inputs)
    for g in groups:
        out.update((NOT_PROVIDED if alt else NEUTRAL)[g])
        if g == "market":
            out["sector_performance"] = sector_default
    return out


def sampled(scan_id: str, ticker: str, fraction: float) -> bool:
    """Deterministic pseudo-random sample, so a re-run replays the same candidates and never drifts."""
    h = int(hashlib.sha1(f"{scan_id}|{ticker}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return h < fraction


def replay(agent, row: dict, variant: str) -> dict:
    """One replay of a logged candidate through the production prompt. Returns the raw model decision (and the validated one)."""
    try:
        from langchain_core.messages import HumanMessage
    except ImportError:                     # tests and CI run without langchain; a stub model only needs `.content`
        from types import SimpleNamespace as HumanMessage
    inp, groups = row["inputs"], ([] if variant.startswith("control") else ALL_VARIANTS[variant])
    prepared = agent._prepare_inputs(row["ticker"], {"features": inp.get("features") or {}, "rag_context": inp.get("rag_context")},
                                     inp.get("fundamentals") or {}, inp.get("news_analysis") or {}, inp.get("market_context") or {})
    sector_default = agent._format_sector_perf(prepared.get("sector", "Unknown"), {})
    prompt = agent.decision_prompt.format(**neutralise(prepared, groups, sector_default, alt=variant.endswith("_alt")))
    t0 = time.time()
    resp = agent.llm.invoke([HumanMessage(content=prompt)])
    raw = agent._parse_response(resp.content)
    usage = getattr(resp, "usage_metadata", None) or {}
    try:
        validated = agent._validate_decision(dict(raw), prepared)
    except Exception:                    # noqa: BLE001
        validated = raw
    return {"decision": raw.get("decision"), "confidence": raw.get("confidence"), "validated_decision": validated.get("decision"),
            "validated_confidence": validated.get("confidence"), "tokens_in": usage.get("input_tokens"), "tokens_out": usage.get("output_tokens"),
            "latency_s": round(time.time() - t0, 2)}


def _cost(r: dict) -> float:
    return (r.get("tokens_in") or 1400) * PRICE_IN / 1e6 + (r.get("tokens_out") or 250) * PRICE_OUT / 1e6


def done_keys(data_dir: Path = DATA) -> set:
    keys = set()
    for p in (Path(data_dir) / "ablation").glob("*.jsonl.gz"):
        with gzip.open(p, "rb") as f:
            for line in f:
                r = json.loads(line)
                if r.get("status") == "ok":
                    keys.add((r["scan_id"], r["ticker"], r["variant"]))
    return keys


def run(fraction: float = 0.25, limit: int = None, budget_usd: float = 1.5, data_dir: Path = DATA, agent=None, workers: int = 4, max_seconds: float = 1200) -> dict:
    """Replay a deterministic sample of the logged candidates that have not been replayed yet, within a spend cap."""
    import input_log
    if agent is None:
        from agents.autonomous_reasoning_agent import get_autonomous_reasoning_agent
        agent = get_autonomous_reasoning_agent()
    rows = [r for r in input_log.read_all(data_dir) if sampled(r["scan_id"], r["ticker"], fraction)]
    done = done_keys(data_dir)
    todo = [(r, v) for r in rows for v in (*CONTROLS, *ALL_VARIANTS) if (r["scan_id"], r["ticker"], v) not in done]
    if limit:
        todo = todo[:limit]
    out_path = Path(data_dir) / "ablation" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl.gz"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    spent, n_ok, n_err, stopped, t_start = 0.0, 0, 0, None, time.time()

    def one(rv):
        r, v = rv
        try:
            return r, v, {"status": "ok", **replay(agent, r, v)}
        except Exception as e:           # noqa: BLE001
            return r, v, {"status": "error", "error": str(e)[:200]}

    with ThreadPoolExecutor(max_workers=workers) as pool, gzip.open(out_path, "ab") as f:
        for i in range(0, len(todo), workers * 4):
            if spent >= budget_usd:
                stopped = "budget"
                break
            if time.time() - t_start > max_seconds:          # stay well inside the job's task timeout; the rest resumes next week
                stopped = "time"
                break
            for r, v, res in pool.map(one, todo[i:i + workers * 4]):
                f.write((json.dumps({"scan_id": r["scan_id"], "ticker": r["ticker"], "variant": v, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **res}) + "\n").encode())
                spent += _cost(res) if res["status"] == "ok" else 0
                n_ok += res["status"] == "ok"
                n_err += res["status"] != "ok"
    return {"replayed": n_ok, "errors": n_err, "spent_usd": round(spent, 4), "candidates_sampled": len(rows), "stopped": stopped}


# ── analysis ──────────────────────────────────────────────────────────────────

def load_results(data_dir: Path = DATA) -> dict:
    """{(scan_id, ticker): {variant: decision}} for successful replays."""
    out = {}
    for p in sorted((Path(data_dir) / "ablation").glob("*.jsonl.gz")):
        with gzip.open(p, "rb") as f:
            for line in f:
                r = json.loads(line)
                if r.get("status") == "ok" and r.get("decision"):
                    out.setdefault((r["scan_id"], r["ticker"]), {})[r["variant"]] = {"d": r["decision"], "c": r.get("confidence")}
    return out


def _boot(vals: np.ndarray, n: int = 4000, seed: int = 7):
    rng = np.random.default_rng(seed)
    draws = np.array([vals[rng.integers(0, len(vals), len(vals))].mean() for _ in range(n)])
    return float(vals.mean()), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def analyze(results: dict) -> dict:
    """Agreement with control_1, BUY rate and confidence per variant, against the run-to-run noise floor (control_2/3 vs control_1)."""
    full = {k: v for k, v in results.items() if all(c in v for c in CONTROLS) and all(x in v for x in VARIANTS)}
    keys = sorted(full)
    out = {"n_candidates": len(keys), "note": "agreement = share of candidates whose decision equals control_1's; the noise floor is the same "
                                              "quantity for two more identical control runs", "variants": {}}
    if not keys:
        return out
    dec = lambda v: [full[k][v]["d"] for k in keys]
    base = np.array(dec("control_1"))
    present_alt = [v for v in ALT if all(v in full[k] for k in keys)]
    for v in (*CONTROLS[1:], *VARIANTS, *present_alt):
        arr = np.array(dec(v))
        agree = (arr == base).astype(float)
        m, lo, hi = _boot(agree)
        conf = np.array([(full[k][v]["c"] or 0) - (full[k]["control_1"]["c"] or 0) for k in keys], float)
        out["variants"][v] = {"agree": m, "lo": lo, "hi": hi, "buy_rate": float((arr == "BUY").mean()), "buy_rate_control": float((base == "BUY").mean()),
                              "mean_conf_shift": float(conf.mean()),
                              "flips_to_buy": int(((arr == "BUY") & (base != "BUY")).sum()), "flips_from_buy": int(((arr != "BUY") & (base == "BUY")).sum())}
    noise = np.mean([out["variants"][c]["agree"] for c in CONTROLS[1:]])
    out["noise_floor_agree"] = float(noise)
    for v in (*VARIANTS, *present_alt):     # a variant matters only if its agreement interval lies BELOW the noise floor
        out["variants"][v]["beyond_noise"] = bool(out["variants"][v]["hi"] < noise)
    return out


def show(a: dict):
    print(f"{a['n_candidates']} candidates with all replays.   noise floor (two identical control runs agree): {a.get('noise_floor_agree', float('nan')) * 100:.1f}%")
    print(f"{'variant':16} {'agree w/ control':>17}  {'95% CI':>13} {'BUY rate':>9} {'to BUY':>7} {'from BUY':>9}  beyond noise?")
    for v, r in a["variants"].items():
        print(f"{v:16} {r['agree'] * 100:16.1f}%  [{r['lo'] * 100:4.0f},{r['hi'] * 100:4.0f}] {r['buy_rate'] * 100:8.1f}% {r['flips_to_buy']:7d} {r['flips_from_buy']:9d}  {r.get('beyond_noise', '(control)')}")


# ── outcomes: does an input matter for the QUALITY of the BUYs, not just their number? ───────────────

def outcome_table(results: dict, when: dict, car: dict, min_signals: int = 30) -> dict:
    """results: {(scan_id,ticker): {variant: {"d":..}}}; when: {(scan_id,ticker): day index}; car: {(scan_id,ticker): 10-day CAR or None if unmatured}.
    For each variant: the mean CAR of the BUYs it makes, and the mean CAR of the BUYs that REMOVING that input drops (control BUY, variant not BUY) or adds.
    Also: does the control's vote share of BUY across its three runs (a self-consistency confidence) predict CAR?"""
    keys = [k for k in results if k in car and car[k] is not None and all(c in results[k] for c in CONTROLS)]
    out = {"n_matured": len(keys), "min_signals": min_signals, "variants": {}}
    if len(keys) < min_signals:
        out["verdict"] = f"insufficient data ({len(keys)} matured candidates; need {min_signals})"
    ctl = lambda k: results[k]["control_1"]["d"] == "BUY"
    frame = lambda ks: np.array([car[k] for k in ks], float)
    boot = lambda a: _boot(a) if len(a) >= 5 else (float(a.mean()) if len(a) else float("nan"), float("nan"), float("nan"))
    for v in VARIANTS:
        if not all(v in results[k] for k in keys):
            continue
        dropped = [k for k in keys if ctl(k) and results[k][v]["d"] != "BUY"]     # BUYs that only exist because of the removed input
        added = [k for k in keys if not ctl(k) and results[k][v]["d"] == "BUY"]
        kept = [k for k in keys if ctl(k) and results[k][v]["d"] == "BUY"]
        out["variants"][v] = {"n_dropped": len(dropped), "n_added": len(added), "n_kept": len(kept),
                              "car_dropped": dict(zip(("mean", "lo", "hi"), boot(frame(dropped)))), "car_added": dict(zip(("mean", "lo", "hi"), boot(frame(added)))),
                              "car_kept": dict(zip(("mean", "lo", "hi"), boot(frame(kept))))}
    votes = np.array([sum(results[k][c]["d"] == "BUY" for c in CONTROLS) / len(CONTROLS) for k in keys])
    y = frame(keys)
    if len(keys) >= 10 and votes.std() > 0:
        out["vote_share_vs_car_spearman"] = float(np.corrcoef(pd_rank(votes), pd_rank(y))[0, 1])
    return out


def pd_rank(a: np.ndarray) -> np.ndarray:
    """Average ranks (ties share the mean rank): Spearman = Pearson on these."""
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    i = 0
    sa = np.asarray(a)[order]
    while i < len(a):
        j = i
        while j + 1 < len(a) and sa[j + 1] == sa[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def weekly(discord: bool = False, data_dir: Path = DATA) -> dict:
    r = run(fraction=0.15, budget_usd=1.5, data_dir=data_dir, workers=6)
    a = analyze(load_results(data_dir))
    (Path(data_dir) / "ablation_summary.json").write_text(json.dumps({"replay": r, "analysis": a}, indent=1))
    show(a)
    if discord:
        import os
        import requests
        url = os.environ.get("DISCORD_WEBHOOK_URL")
        if url and a.get("n_candidates"):
            lines = [f"{a['n_candidates']} candidates replayed; noise floor {a['noise_floor_agree'] * 100:.0f}% agreement between identical runs; spent ${r['spent_usd']:.2f} this week"]
            for v, x in a["variants"].items():
                if v in ALL_VARIANTS:
                    lines.append(f"{v}: {x['agree'] * 100:.0f}% agree, BUY rate {x['buy_rate'] * 100:.0f}% vs {x['buy_rate_control'] * 100:.0f}%" + (" **beyond noise**" if x.get("beyond_noise") else ""))
            try:
                requests.post(url, json={"embeds": [{"title": "Weekly input ablation", "description": "\n".join(lines), "color": 0x5865F2}]}, timeout=10)
            except Exception as exc:        # noqa: BLE001
                print(f"discord post failed: {exc}", file=sys.stderr)
    return r


def write_tex(a: dict):
    """LaTeX for the paper (paper/results_ablation.tex) from the analysis, so numbers cannot drift from the code."""
    names = {"no_news": "No news", "no_news_alt": "No news (other wording)", "no_fundamentals": "No fundamentals", "no_market": "No market context",
             "no_technical": "No technicals", "no_technical_alt": "No technicals (other wording)", "technical_only": "Technicals only"}
    rows = []
    for v, n in names.items():
        if v not in a["variants"]:
            continue
        r = a["variants"][v]
        rows.append(f"{n} & {r['agree'] * 100:.0f} [{r['lo'] * 100:.0f},{r['hi'] * 100:.0f}] & {r['buy_rate'] * 100:.0f} & {r['flips_to_buy']} / {r['flips_from_buy']} \\\\ ")
    ctl = a["variants"]["control_2"]["buy_rate_control"]
    tex = ("% generated by ablation.py analyze --tex; do not edit\n"
           f"\\newcommand{{\\ablN}}{{{a['n_candidates']}}}\n\\newcommand{{\\ablNoise}}{{{a['noise_floor_agree'] * 100:.1f}}}\n"
           f"\\newcommand{{\\ablBuyCtl}}{{{ctl * 100:.0f}}}\n"
           "\\newcommand{\\ablRows}{%\n" + "\n".join(rows) + "}\n")
    (Path(__file__).parent.parent / "paper" / "results_ablation.tex").write_text(tex)


def outcomes_cli():
    """Join replayed decisions to matured 10-day abnormal returns (same definition as the paper) and print the outcome table."""
    import input_log
    import audit_core as core
    import pandas as pd
    res = load_results()
    rows = {(r["scan_id"], r["ticker"]): r for r in input_log.read_all()}
    days = {k: pd.Timestamp(rows[k]["decided_at"][:10]) for k in res if k in rows}
    tickers = sorted({k[1] for k in days})
    if not days:
        print("no replayed candidates yet")
        return
    P = core.load_panel(tickers, min(days.values()) - pd.Timedelta(days=140), pd.Timestamp.today().normalize() + pd.Timedelta(days=1))
    idx = P["C"].index
    car = {}
    for k, d in days.items():
        i = idx.searchsorted(d, side="right") - 1
        car[k] = float(core.car_path(P, i, k[1])[0][core.H]) if core.valid(P, i, k[1]) else None
    o = outcome_table({k: res[k] for k in days}, days, car)
    print(json.dumps(o, indent=1, default=float))
    (HERE / "paper_results" / "ablation_outcomes.json").write_text(json.dumps(o, indent=1, default=float))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    arg = lambda name, cast, default: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
    if cmd == "run":
        print(json.dumps(run(arg("--sample", float, 0.25), arg("--limit", int, None), arg("--budget-usd", float, 1.5)), indent=1))
    elif cmd == "weekly":
        weekly("--discord" in sys.argv)
    elif cmd == "outcomes":
        outcomes_cli()
    elif cmd == "analyze":
        a = analyze(load_results(Path(arg("--data", str, DATA))))
        if "--tex" in sys.argv:
            write_tex(a)
        show(a)
        out = Path(arg("--out", str, HERE / "paper_results" / "ablation.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(a, indent=1))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
