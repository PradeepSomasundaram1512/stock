"""
Shadow model: a second LLM answers the same prompt, on the same stored inputs, as the
production model for every candidate of the hourly scan. Its answers are only logged
(shadow_decisions table); they never reach alerts, rankings or trading. This gives a
clean, forward, model-only comparison ("does a newer/stronger model choose better?").

It shares an OpenAI account with production, which has already run out of quota once
(71% of a whole deployment's decisions were silent fallbacks). So it is built to be
unable to hurt production and to stay cheap:

  * OFF unless SHADOW_MODEL is set; cost is unbounded for an unknown model, so a model
    without a known price is refused;
  * hard daily budget (SHADOW_DAILY_BUDGET_USD, default $0.25) from actual token usage
    already logged today -- persisted, so it holds across separate job executions;
  * runs AFTER the production alert has been sent, so it can never delay it;
  * skipped entirely if this scan's production model calls were failing (an unhealthy
    account is not the moment to spend more of it);
  * stops for the scan after 3 consecutive failures (circuit breaker);
  * everything is wrapped so an error here can only ever be logged.

Config (env):  SHADOW_MODEL  SHADOW_DAILY_BUDGET_USD  SHADOW_PRICE_IN  SHADOW_PRICE_OUT
               (USD per 1M tokens; the last two override the built-in price table)

SHADOW_MODEL takes one or several models, comma separated. "name:buys" restricts that model to the candidates production called BUY (about 10x
cheaper, and it is the only slice a forward test scores), e.g.  SHADOW_MODEL="gpt-6-luna,gpt-6-sol:buys". The daily budget applies to each model separately.
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# USD per 1M tokens (input, output), from OpenAI's published API pricing, Sept 2026.
PRICES: Dict[str, Tuple[float, float]] = {
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6-sol": (2.00, 10.00),
    "gpt-6-astra": (10.00, 50.00),
    "gpt-4o-mini": (0.15, 0.60),
}
DEFAULT_BUDGET_USD = 0.25
UNHEALTHY_FALLBACK_SHARE = 0.10   # skip the scan if >=10% of production calls failed
MAX_CONSECUTIVE_ERRORS = 3
WORKERS = 4
EST_TOKENS_IN, EST_TOKENS_OUT = 1300, 500   # measured: ~1,296 in / ~450 out incl. hidden reasoning

_agents: Dict[str, Any] = {}


def _configs() -> List[Dict[str, Any]]:
    """One config per usable model in SHADOW_MODEL; empty when disabled. Never raises."""
    out = []
    for part in os.getenv("SHADOW_MODEL", "").split(","):
        model, _, flag = part.strip().partition(":")
        if not model:
            continue
        try:
            price_in = float(os.getenv("SHADOW_PRICE_IN") or PRICES[model][0])
            price_out = float(os.getenv("SHADOW_PRICE_OUT") or PRICES[model][1])
            budget = float(os.getenv("SHADOW_DAILY_BUDGET_USD") or DEFAULT_BUDGET_USD)
        except (KeyError, ValueError):
            logger.warning(f"Shadow model '{model}' skipped: no known price (set SHADOW_PRICE_IN/OUT) or bad budget")
            continue
        out.append({"model": model, "price_in": price_in, "price_out": price_out, "budget": budget, "buys_only": flag == "buys"})
    return out


def _cost(cfg: Dict[str, Any], tokens_in: Optional[int], tokens_out: Optional[int]) -> float:
    ti = tokens_in if tokens_in is not None else EST_TOKENS_IN
    to = tokens_out if tokens_out is not None else EST_TOKENS_OUT
    return ti * cfg["price_in"] / 1e6 + to * cfg["price_out"] / 1e6


def _get_agent(model: str):
    if model not in _agents:
        from agents.autonomous_reasoning_agent import AutonomousReasoningAgent
        # temperature=None: the GPT-6 family rejects any non-default value
        _agents[model] = AutonomousReasoningAgent(model_type="openai", model_name=model, temperature=None)
    return _agents[model]


def _one(agent, r: Dict[str, Any]) -> Dict[str, Any]:
    return agent.analyze(
        ticker=r["ticker"],
        technical_data={"features": r.get("features"), "rag_context": r.get("rag_context")},
        fundamental_data=r.get("fundamentals"),
        news_data=r.get("news_analysis"),
        market_context=r.get("market_context"),
    )


def run_shadow(scan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Run the shadow model over one scan's candidates. Returns a small status dict."""
    try:
        return _run(scan)
    except Exception as e:                       # must never break the scan
        logger.warning(f"Shadow run failed (ignored): {e}")
        return {"status": "error", "error": str(e)}


def _run(scan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfgs = _configs()
    if not cfgs:
        return {"status": "disabled"}
    all_results = [r for r in ((scan or {}).get("results") or []) if r and r.get("ticker")]
    if not all_results:
        return {"status": "no_candidates"}

    n_fail = sum(1 for r in all_results if (r.get("decision") or {}).get("llm_status") == "fallback_error")
    if n_fail / len(all_results) >= UNHEALTHY_FALLBACK_SHARE:
        logger.warning(f"Shadow skipped: {n_fail}/{len(all_results)} production calls failed this scan")
        return {"status": "skipped_primary_unhealthy"}

    statuses = {}
    for cfg in cfgs:      # each model is isolated: one failing or over budget never stops the others
        try:
            results = [r for r in all_results if (r.get("decision") or {}).get("decision") == "BUY"] if cfg["buys_only"] else all_results
            statuses[cfg["model"]] = _run_model(scan, cfg, results) if results else {"status": "no_candidates"}
        except Exception as e:
            logger.warning(f"Shadow model {cfg['model']} failed (ignored): {e}")
            statuses[cfg["model"]] = {"status": "error", "error": str(e)}
    return statuses[cfgs[0]["model"]] if len(cfgs) == 1 else {"status": "ok", "models": statuses}


def _run_model(scan: Dict[str, Any], cfg: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    from tools.db_manager import save_shadow_decisions, shadow_spent_today_usd
    spent = shadow_spent_today_usd(cfg["model"])
    remaining = cfg["budget"] - spent
    per_call = _cost(cfg, None, None)
    if remaining < per_call:
        logger.info(f"Shadow skipped: daily budget ${cfg['budget']:.2f} used (${spent:.4f} spent)")
        return {"status": "budget_exhausted", "spent": spent}

    agent = _get_agent(cfg["model"])
    scan_id = scan["scan_id"]
    rows: List[Dict[str, Any]] = []
    consecutive_errors, stopped = 0, None

    def to_row(r, d):
        cost = _cost(cfg, d.get("tokens_in"), d.get("tokens_out")) if d.get("llm_status") == "ok" else 0.0
        return {
            "scan_id": scan_id, "decided_at": datetime.utcnow().isoformat(), "ticker": r["ticker"],
            "shadow_model": cfg["model"], "llm_status": d.get("llm_status", "unknown"),
            "latency_s": d.get("latency_s"), "error": d.get("error"), "decision": d.get("decision"),
            "confidence": d.get("confidence"), "price_target": d.get("price_target"), "stop_loss": d.get("stop_loss"),
            "risk_level": d.get("risk_level"), "time_horizon": d.get("time_horizon"),
            "key_factors": json.dumps(d.get("key_factors") or []), "reasoning": d.get("reasoning"),
            "tokens_in": d.get("tokens_in"), "tokens_out": d.get("tokens_out"), "est_cost_usd": cost,
        }

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i in range(0, len(results), WORKERS):
            chunk = results[i:i + WORKERS]
            if remaining < per_call * len(chunk):
                stopped = "budget"
                break
            for r, d in zip(chunk, pool.map(lambda x: _one(agent, x), chunk)):
                row = to_row(r, d)
                rows.append(row)
                remaining -= row["est_cost_usd"]
                consecutive_errors = consecutive_errors + 1 if row["llm_status"] != "ok" else 0
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                stopped = "circuit_breaker"
                break

    save_shadow_decisions(rows)
    ok = [x for x in rows if x["llm_status"] == "ok"]
    prim = {r["ticker"]: (r.get("decision") or {}).get("decision") for r in results}
    agree = sum(1 for x in ok if prim.get(x["ticker"]) == x["decision"])
    logger.info(
        f"Shadow ({cfg['model']}): {len(ok)}/{len(rows)} answered in {time.time() - t0:.0f}s, "
        f"{sum(1 for x in ok if x['decision'] == 'BUY')} BUY vs production "
        f"{sum(1 for x in ok if prim.get(x['ticker']) == 'BUY')}, agreement {agree}/{len(ok)}, "
        f"spent ${sum(x['est_cost_usd'] for x in rows):.4f} (${cfg['budget'] - remaining:.4f}/${cfg['budget']:.2f} today)"
        + (f", stopped: {stopped}" if stopped else "")
    )
    return {"status": "ok", "answered": len(ok), "rows": len(rows), "stopped": stopped}
