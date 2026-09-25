import json
import sys

import numpy as np
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))
import ablation as ab
import input_log as il

TEMPLATE = ("{ticker} trend={trend} rsi_signal={rsi_signal} macd={macd_signal} vol={volume_signal} volat={volatility_level} sr={support_resistance} "
            "tech={technical_summary} | pe={pe_ratio} health={health_score} rg={revenue_growth} eg={earnings_growth} tgt={analyst_target_price} n={analyst_count} | "
            "news={news_count} {news_sentiment} {news_topics} {news_summary} | mkt={market_trend} vix={market_vix} sec={sector_performance} idx={indices_performance}")


class StubAgent:
    """Just enough of AutonomousReasoningAgent for replay(): builds prompts from a fixed template and answers from a script."""
    decision_prompt = TEMPLATE

    def __init__(self, answers=None):
        self.prompts, self.answers = [], answers or {}
        self.llm = SimpleNamespace(invoke=self._invoke)

    def _prepare_inputs(self, ticker, technical, fundamental, news, market):
        f = technical.get("features") or {}
        return {"ticker": ticker, "trend": f.get("trend", "neutral"), "rsi_signal": "oversold", "macd_signal": "bullish", "volume_signal": "high",
                "volatility_level": "high", "support_resistance": "S:10", "technical_summary": "TECHSUM", "pe_ratio": "21.00", "health_score": "0.80",
                "revenue_growth": "+9.0%", "earnings_growth": "+5.0%", "analyst_target_price": "150", "analyst_count": 30, "news_count": news.get("news_count", 0),
                "news_sentiment": "POSITIVE", "news_topics": "buyback", "news_summary": "NEWSSUM", "market_trend": "BULLISH", "market_vix": "14.00",
                "sector_performance": "SECTORPERF", "sector": "Tech", "indices_performance": "  - SPY: +1%"}

    def _format_sector_perf(self, sector, perf):
        return "no sector data"

    def _invoke(self, msgs):
        self.prompts.append(msgs[0].content)
        n = len(self.prompts)
        d = self.answers.get(n, "BUY")
        return SimpleNamespace(content=json.dumps({"decision": d, "confidence": 0.8}), usage_metadata={"input_tokens": 1000, "output_tokens": 200})

    def _parse_response(self, text):
        return json.loads(text)

    def _validate_decision(self, d, inputs):
        return d


ROW = {"scan_id": "s1", "ticker": "AAA", "inputs": {"features": {"trend": "up"}, "rag_context": "x", "fundamentals": {}, "news_analysis": {"news_count": 4}, "market_context": {}}}


class NeutraliseTests(unittest.TestCase):
    def prompt(self, variant):
        a = StubAgent()
        ab.replay(a, ROW, variant)
        return a.prompts[0]

    def test_control_keeps_everything(self):
        p = self.prompt("control_1")
        for needle in ("TECHSUM", "NEWSSUM", "SECTORPERF", "pe=21.00", "vix=14.00", "buyback"):
            self.assertIn(needle, p)

    def test_each_variant_removes_only_its_group(self):
        checks = {"no_news": (["NEWSSUM", "buyback", "POSITIVE"], ["TECHSUM", "pe=21.00", "SECTORPERF"]),
                  "no_fundamentals": (["pe=21.00", "+9.0%", "tgt=150"], ["NEWSSUM", "TECHSUM", "SECTORPERF"]),
                  "no_market": (["SECTORPERF", "vix=14.00", "BULLISH", "SPY"], ["NEWSSUM", "TECHSUM", "pe=21.00"]),
                  "no_technical": (["TECHSUM", "oversold", "bullish", "S:10"], ["NEWSSUM", "pe=21.00", "SECTORPERF"]),
                  "technical_only": (["NEWSSUM", "pe=21.00", "SECTORPERF", "vix=14.00"], ["TECHSUM", "oversold"])}
        for v, (gone, kept) in checks.items():
            p = self.prompt(v)
            for g in gone:
                self.assertNotIn(g, p, f"{v} should remove {g}")
            for k in kept:
                self.assertIn(k, p, f"{v} should keep {k}")
        self.assertIn("no sector data", self.prompt("no_market"))

    def test_alternative_wording_removes_the_same_information_with_different_words(self):
        for base, alt in (("no_news", "no_news_alt"), ("no_technical", "no_technical_alt")):
            pb, pa = self.prompt(base), self.prompt(alt)
            for needle in ("NEWSSUM", "buyback", "TECHSUM", "oversold"):
                self.assertEqual(needle in pb, needle in pa)                        # the same facts are gone
            self.assertIn("not provided", pa.lower())
            self.assertNotEqual(pb, pa)                                              # but the replacement wording differs

    def test_sampling_is_deterministic_and_roughly_the_right_size(self):
        picks = [ab.sampled("scan", f"T{i}", 0.25) for i in range(4000)]
        self.assertEqual(picks, [ab.sampled("scan", f"T{i}", 0.25) for i in range(4000)])
        self.assertTrue(0.21 < sum(picks) / 4000 < 0.29)
        self.assertTrue(all(ab.sampled("s", "X", 1.0) for _ in range(3)))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        il.append("s1", [{"ticker": "AAA", "features": {"trend": "up"}, "news_analysis": {"news_count": 4}}, {"ticker": "BBB", "features": {}}], self.d)

    def test_replays_every_variant_then_is_resumable(self):
        a = StubAgent()
        r = ab.run(fraction=1.0, data_dir=self.d, agent=a, workers=1)
        self.assertEqual((r["replayed"], r["errors"]), (2 * (3 + len(ab.ALL_VARIANTS)), 0))            # 2 candidates x (3 controls + 5 variants)
        again = ab.run(fraction=1.0, data_dir=self.d, agent=StubAgent(), workers=1)
        self.assertEqual(again["replayed"], 0)                                                     # nothing is replayed twice

    def test_budget_cap_stops_spending(self):
        r = ab.run(fraction=1.0, data_dir=self.d, agent=StubAgent(), workers=1, budget_usd=0.0)
        self.assertEqual((r["replayed"], r["stopped"]), (0, "budget"))

    def test_wall_clock_cap_stops_and_the_rest_resumes(self):
        r = ab.run(fraction=1.0, data_dir=self.d, agent=StubAgent(), workers=1, max_seconds=-1)
        self.assertEqual((r["replayed"], r["stopped"]), (0, "time"))
        again = ab.run(fraction=1.0, data_dir=self.d, agent=StubAgent(), workers=1)
        self.assertEqual(again["replayed"], 2 * (3 + len(ab.ALL_VARIANTS)))                            # nothing was lost by stopping early

    def test_errors_are_recorded_not_fatal(self):
        a = StubAgent()
        a.llm = SimpleNamespace(invoke=lambda m: (_ for _ in ()).throw(RuntimeError("quota")))
        r = ab.run(fraction=1.0, data_dir=self.d, agent=a, workers=1)
        self.assertEqual((r["replayed"], r["errors"]), (0, 2 * (3 + len(ab.ALL_VARIANTS))))


class AnalyzeTests(unittest.TestCase):
    def build(self, flip):
        res = {}
        for i in range(60):
            base = "BUY" if i % 3 == 0 else "HOLD"
            v = {c: {"d": base, "c": 0.8} for c in ab.CONTROLS}
            for name in ab.VARIANTS:
                v[name] = {"d": ("HOLD" if base == "BUY" else "BUY") if name in flip else base, "c": 0.8}
            res[("s", f"T{i}")] = v
        return res

    def test_a_variant_that_changes_decisions_beyond_noise_is_flagged_and_others_are_not(self):
        a = ab.analyze(self.build(flip={"no_news"}))
        self.assertEqual(a["n_candidates"], 60)
        self.assertEqual(a["noise_floor_agree"], 1.0)
        self.assertTrue(a["variants"]["no_news"]["beyond_noise"])
        self.assertFalse(a["variants"]["no_market"]["beyond_noise"])
        self.assertEqual(a["variants"]["no_news"]["flips_from_buy"], 20)

    def test_noisy_controls_raise_the_bar(self):
        res = self.build(flip={"no_news"})
        for i, k in enumerate(sorted(res)):                       # controls disagree with control_1 on half the candidates
            if i % 2:
                res[k]["control_2"]["d"] = res[k]["control_3"]["d"] = "SELL"
        a = ab.analyze(res)
        self.assertLess(a["noise_floor_agree"], 0.6)
        self.assertFalse(a["variants"]["no_market"]["beyond_noise"])

    def test_incomplete_candidates_are_excluded(self):
        res = self.build(flip=set())
        del res[("s", "T0")]["no_news"]
        self.assertEqual(ab.analyze(res)["n_candidates"], 59)


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.res, self.car = {}, {}
        for i in range(40):
            k = ("s", f"T{i}")
            ctl = "BUY" if i % 2 == 0 else "HOLD"
            v = {c: {"d": ctl, "c": .8} for c in ab.CONTROLS}
            for name in ab.VARIANTS:
                v[name] = {"d": "HOLD" if (name == "no_news" and ctl == "BUY" and i % 4 == 0) else ctl, "c": .8}
            self.res[k] = v
            self.car[k] = 0.02 if (i % 4 == 0) else -0.01                # the BUYs that no_news drops (i % 4 == 0) are the GOOD ones
        self.car[("s", "T3")] = None                                         # unmatured: must be excluded

    def test_dropped_buys_are_separated_from_kept_ones(self):
        o = ab.outcome_table(self.res, {k: 0 for k in self.res}, self.car, min_signals=10)
        self.assertEqual(o["n_matured"], 39)
        nn = o["variants"]["no_news"]
        self.assertEqual((nn["n_dropped"], nn["n_kept"], nn["n_added"]), (10, 10, 0))
        self.assertAlmostEqual(nn["car_dropped"]["mean"], 0.02)
        self.assertAlmostEqual(nn["car_kept"]["mean"], -0.01)                 # removing news lost the good BUYs, not the bad ones
        self.assertEqual(o["variants"]["no_market"]["n_dropped"], 0)

    def test_too_few_matured_candidates_is_reported_as_insufficient(self):
        o = ab.outcome_table(self.res, {k: 0 for k in self.res}, self.car, min_signals=100)
        self.assertIn("insufficient data", o["verdict"])

    def test_average_ranks_handle_ties(self):
        self.assertEqual(list(ab.pd_rank(np.array([3.0, 1.0, 1.0, 2.0]))), [4.0, 1.5, 1.5, 3.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
