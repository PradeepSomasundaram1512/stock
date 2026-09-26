"""H7 (addendum 4): shadow-answer matching and the Sol-BUY minus not-BUY test (synthetic data; needs numpy/pandas and audit_core's imports)."""
import sqlite3
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import forward_test as ft


def _db(rows):
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    con = sqlite3.connect(f)
    con.execute("create table shadow_decisions (ticker text, decided_at text, shadow_model text, llm_status text, decision text)")
    con.executemany("insert into shadow_decisions values (?,?,?,?,?)", rows)
    con.commit()
    return f


def test_first_ok_answer_per_day_and_model():
    db = _db([("AAA", "2026-10-01T15:00:00", "gpt-6-sol", "ok", "HOLD"), ("AAA", "2026-10-01T18:00:00", "gpt-6-sol", "ok", "BUY"),
              ("AAA", "2026-10-01T14:00:00", "gpt-6-sol", "fallback_error", "BUY"), ("AAA", "2026-10-01T15:00:00", "gpt-6-luna", "ok", "BUY")])
    a = ft.shadow_answers(db, "gpt-6-sol")
    assert len(a) == 1 and a.iloc[0].s_decision == "HOLD"
    assert ft.shadow_answers(db, "nope").empty and ft.shadow_answers("/nonexistent/x.db", "gpt-6-sol").empty


def _frame(n, effect, seed=0):
    r = np.random.default_rng(seed)
    i = np.arange(n) // 2
    buy = r.random(n) < 0.5
    car = r.normal(0, 0.03, n) + np.where(buy, effect, 0.0)
    return pd.DataFrame({"i": i, "day": [f"d{k}" for k in range(n)], "ticker": ["T"] * n, "car": car, "match": 0.0}), \
        pd.DataFrame({"day": [f"d{k}" for k in range(n)], "ticker": ["T"] * n, "s_decision": np.where(buy, "BUY", "HOLD")})


def test_minimum_sample_gives_no_verdict():
    df, ans = _frame(60, 0.05)
    o = ft.h7(df, ans, "gpt-6-sol")
    assert "insufficient" in o["verdict"] and "est" not in o


def test_detects_a_real_filter_and_not_a_null():
    df, ans = _frame(1200, 0.06)
    e = ft.h7(df, ans, "gpt-6-sol")["est"]
    assert e["detectable"] and e["est"] > 0.03
    df0, ans0 = _frame(1200, 0.0, seed=1)
    assert not ft.h7(df0, ans0, "gpt-6-sol")["est"]["detectable"]


def test_untestable_when_model_never_varies_and_luna_needs_no_minimum():
    df, ans = _frame(1200, 0.0)
    ans["s_decision"] = "BUY"
    assert "untestable" in ft.h7(df, ans, "gpt-6-sol")["verdict"]
    df, ans = _frame(60, 0.05)
    assert "est" in ft.h7(df, ans, "gpt-6-luna", verdict=False)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
