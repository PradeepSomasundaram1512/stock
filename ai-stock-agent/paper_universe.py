"""
Fixed S&P 500 universe for the paper's placebo, as of the start of the study.

The original placebo pool was "tickers that appear anywhere in the log", which can
include stocks that only entered the index (or the log) after a signal date, i.e. it
peeks ahead. This script reconstructs the constituent list on AS_OF instead:

  membership(AS_OF) = current constituents
                      - names added after AS_OF        (undo the additions)
                      + names removed after AS_OF      (undo the removals)

Sources (fetched once; the result is saved so the analysis is reproducible offline):
  * Wikipedia "List of S&P 500 companies" -- current constituents;
  * historyofmarket.com/sp500/changes    -- dated additions and removals.
Set operations make the reversal safe even if one source lags the other.

Run:    venv/bin/python paper_universe.py
Output: paper_results/sp500_universe.csv  (symbol, in_universe_at_start)
"""

import io
import re
import sys
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).parent
RES = HERE / "paper_results"
AS_OF = pd.Timestamp("2026-01-01")
UA = {"User-Agent": "Mozilla/5.0 (academic research script)"}
WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CHANGES = "https://historyofmarket.com/sp500/changes/"


def norm(sym: str) -> str:
    """Yahoo Finance style (BRK.B -> BRK-B)."""
    return str(sym).strip().upper().replace(".", "-")


def get_tables(url):
    html = requests.get(url, headers=UA, timeout=60).text
    return pd.read_html(io.StringIO(html))


def main():
    cur = get_tables(WIKI)[0]
    current = {norm(s) for s in cur["Symbol"]}

    ch = get_tables(CHANGES)[0]
    ch["Effective"] = pd.to_datetime(ch["Effective"])
    sym = lambda cell: None if not isinstance(cell, str) or cell.strip() in ("—", "-", "") else norm(re.match(r"\s*([A-Za-z.\-]+)", cell).group(1))
    ch["add"], ch["rem"] = ch["Added"].map(sym), ch["Removed"].map(sym)
    if ch["Effective"].min() > AS_OF:
        sys.exit(f"change log starts {ch['Effective'].min().date()}, after AS_OF; cannot reconstruct")

    after = ch[ch["Effective"] > AS_OF].sort_values("Effective", ascending=False)
    members = set(current)
    added_back, removed_out = [], []
    for r in after.itertuples():
        if isinstance(r.add, str) and r.add in members:
            members.discard(r.add)
            removed_out.append(r.add)
        if isinstance(r.rem, str) and r.rem not in members:
            members.add(r.rem)
            added_back.append(r.rem)

    print(f"current constituents (Wikipedia): {len(current)}")
    print(f"changes effective after {AS_OF.date()}: {len(after)} rows")
    print(f"  undone additions (not members at start): {sorted(removed_out)}")
    print(f"  undone removals  (members at start):     {sorted(added_back)}")
    print(f"reconstructed membership on {AS_OF.date()}: {len(members)}")
    if not 490 <= len(members) <= 515:
        sys.exit("implausible universe size")

    out = pd.DataFrame({"symbol": sorted(members | current)})
    out["in_universe_at_start"] = out.symbol.isin(members)
    out.to_csv(RES / "sp500_universe.csv", index=False)
    print(f"saved {RES / 'sp500_universe.csv'} ({int(out.in_universe_at_start.sum())} at start, {len(out)} rows)")


if __name__ == "__main__":
    main()
