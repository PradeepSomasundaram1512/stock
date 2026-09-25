"""
Build dashboard/sectors.json: ticker -> GICS sector for every ticker the scanner covers, from the current
S&P 500 constituents table on Wikipedia. Tickers not in that table (the scan list has a few non-members)
are labelled "Other". Re-run occasionally; sectors change rarely.

    python dashboard/build_sectors.py
"""
import io
import json
import re
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).parent.parent
WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

src = (ROOT / "ultimate_market_scanner.py").read_text()
body = re.search(r"SP500_ALL = \[(.*?)\n\]", src, re.S).group(1)
scan = list(dict.fromkeys(re.findall(r"'([A-Z][A-Z0-9.\-]*)'", body)))

html = requests.get(WIKI, headers={"User-Agent": "Mozilla/5.0 (research script)"}, timeout=60).text
t = pd.read_html(io.StringIO(html))[0]
sector = {str(s).strip().upper().replace(".", "-"): g for s, g in zip(t["Symbol"], t["GICS Sector"])}
out = {s: sector.get(s, "Other") for s in scan}
(Path(__file__).parent / "sectors.json").write_text(json.dumps(out, indent=0, sort_keys=True))
counts = pd.Series(out).value_counts()
print(f"{len(out)} tickers")
print(counts.to_string())
