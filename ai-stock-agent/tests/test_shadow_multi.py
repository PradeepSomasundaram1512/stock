"""Multi-model shadow config and isolation (no network, no database)."""
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import shadow


def test_disabled_by_default():
    with mock.patch.dict(os.environ, {"SHADOW_MODEL": ""}):
        assert shadow._configs() == []
        assert shadow.run_shadow({"results": [{"ticker": "A"}], "scan_id": "s"})["status"] == "disabled"


def test_parses_list_and_buys_flag_and_skips_unpriced():
    with mock.patch.dict(os.environ, {"SHADOW_MODEL": "gpt-6-luna, gpt-6-sol:buys, mystery-model"}):
        c = shadow._configs()
    assert [x["model"] for x in c] == ["gpt-6-luna", "gpt-6-sol"]
    assert [x["buys_only"] for x in c] == [False, True]


def test_buys_only_gets_buys_and_one_failure_does_not_stop_the_other():
    scan = {"scan_id": "s", "results": [{"ticker": "A", "decision": {"decision": "BUY"}}, {"ticker": "B", "decision": {"decision": "HOLD"}}]}
    seen = {}

    def fake(scan_, cfg, results):
        seen[cfg["model"]] = [r["ticker"] for r in results]
        if cfg["model"] == "gpt-6-luna":
            raise RuntimeError("boom")
        return {"status": "ok"}

    with mock.patch.dict(os.environ, {"SHADOW_MODEL": "gpt-6-luna,gpt-6-sol:buys"}), mock.patch.object(shadow, "_run_model", fake):
        out = shadow.run_shadow(scan)
    assert seen == {"gpt-6-luna": ["A", "B"], "gpt-6-sol": ["A"]}
    assert out["models"]["gpt-6-luna"]["status"] == "error" and out["models"]["gpt-6-sol"]["status"] == "ok"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
