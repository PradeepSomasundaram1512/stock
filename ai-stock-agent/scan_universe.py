"""
The scanner's ticker universe, kept in step with the S&P 500.

The scan list used to be typed by hand and drifted: 83 real members were missing and 49 non-members remained.
This module keeps a refreshed copy in data/scan_universe.json (synced to the bucket like other state):

  * refresh():  fetch the current constituents (Wikipedia's list), validate, and rewrite the file. Existing tickers
                keep their position (the scanner's "quick" scan uses the first 100 names, which are the largest
                companies), leavers are dropped, joiners are appended alphabetically. Every change is appended to
                data/universe_changes.jsonl. Any doubt (wrong count, odd symbols, layout change) aborts and keeps the
                old file: a bad fetch can never shrink or corrupt the universe.
  * load_universe(default):  what the scanner and the market snapshot call. Returns the refreshed list when the file
                is present, recent and valid, else `default` (the list built into ultimate_market_scanner.py).

    python scan_universe.py refresh [--discord]      (weekly job:  entrypoint.sh --refresh-universe)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
FILE_NAME, LOG_NAME = "scan_universe.json", "universe_changes.jsonl"
WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9\-]{0,5}$")
INDEX_MIN, INDEX_MAX = 480, 530  # the index holds ~503 names; a parse far outside that is a bad fetch
MIN_N, MAX_N = 480, 600          # size bounds of the written file (index plus any extras)
EXTRAS_FILE = HERE / "audit" / "scan_extras.txt"
MAX_AGE_DAYS = 45                # a file older than this is ignored (the refresh job has stopped)
MAX_CHANGE = 60                  # refuse to add/remove more than this many names in one refresh


def normalize(sym: str) -> str:
    """Yahoo Finance style: BRK.B -> BRK-B."""
    return str(sym).strip().upper().replace(".", "-")


class _Table(HTMLParser):
    """Collects the rows of <table id="constituents"> as lists of cell texts."""

    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell, self._in_table, self._depth = [], None, None, False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            if a.get("id") == "constituents":
                self._in_table, self._depth = True, 1
            elif self._in_table:
                self._depth += 1
        elif self._in_table and tag == "tr":
            self._row = []
        elif self._in_table and tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self._in_table:
            self._depth -= 1
            if self._depth == 0:
                self._in_table = False
        elif self._in_table and tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif self._in_table and tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_constituents(html: str) -> dict:
    """{symbol: GICS sector} from the constituents table. Raises if the layout is not what we expect."""
    p = _Table()
    p.feed(html)
    if not p.rows:
        raise ValueError("constituents table not found")
    head = [h.lower() for h in p.rows[0]]
    try:
        i_sym, i_sec = head.index("symbol"), head.index("gics sector")
    except ValueError:
        raise ValueError(f"unexpected table header: {p.rows[0][:5]}")
    out = {}
    for r in p.rows[1:]:
        if len(r) > max(i_sym, i_sec):
            sym = normalize(r[i_sym])
            if SYMBOL_RE.match(sym):
                out[sym] = r[i_sec] or "Other"
    return out


def merge(previous: list, current: dict) -> list:
    """Existing tickers keep their order, leavers drop out, joiners are appended alphabetically."""
    kept = [t for t in dict.fromkeys(previous) if t in current]
    return kept + sorted(t for t in current if t not in set(kept))


def _read(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:            # noqa: BLE001
        return None


def _valid(d) -> bool:
    return (isinstance(d, dict) and isinstance(d.get("tickers"), list) and MIN_N <= len(d["tickers"]) <= MAX_N
            and all(isinstance(t, str) and SYMBOL_RE.match(t) for t in d["tickers"]))


def load_universe(default: list, data_dir: Path = DATA, now: datetime = None) -> list:
    """The refreshed universe if data/scan_universe.json is present, valid and recent; otherwise `default`."""
    d = _read(Path(data_dir) / FILE_NAME)
    if not _valid(d):
        return list(default)
    try:
        age = ((now or datetime.now(timezone.utc)) - datetime.fromisoformat(d["asof"])).days
    except Exception:            # noqa: BLE001
        return list(default)
    return list(dict.fromkeys(d["tickers"])) if age <= MAX_AGE_DAYS else list(default)


def load_sectors(data_dir: Path = DATA) -> dict:
    d = _read(Path(data_dir) / FILE_NAME)
    return d.get("sectors", {}) if _valid(d) else {}


def builtin_default() -> list:
    """The list typed into ultimate_market_scanner.py (read from source: importing the scanner takes ~20 s)."""
    src = (HERE / "ultimate_market_scanner.py").read_text()
    body = re.search(r"SP500_ALL = \[(.*?)\n\]", src, re.S).group(1)
    return list(dict.fromkeys(re.findall(r"'([A-Z][A-Z0-9.\-]*)'", body)))


def read_extras(path: Path = None) -> list:
    """Tickers to scan in addition to the index (one per line, # comments): a deliberate, reviewable list."""
    path = path or EXTRAS_FILE
    try:
        lines = [ln.split("#")[0].strip() for ln in path.read_text().splitlines()]
    except OSError:
        return []
    return [normalize(x) for x in lines if x and SYMBOL_RE.match(normalize(x))]


def refresh(html: str = None, data_dir: Path = DATA, now: datetime = None, extras: list = None) -> dict:
    """Rewrite data/scan_universe.json from the live index. Returns {n, added, removed, ...}; raises (and changes nothing) on doubt."""
    data_dir = Path(data_dir)
    if html is None:
        import requests
        html = requests.get(WIKI, headers={"User-Agent": "Mozilla/5.0 (universe refresh)"}, timeout=60).text
    current = parse_constituents(html)
    if not INDEX_MIN <= len(current) <= INDEX_MAX:
        raise ValueError(f"parsed {len(current)} constituents, expected {INDEX_MIN}-{INDEX_MAX}: refusing to update")
    for x in (read_extras() if extras is None else extras):
        current.setdefault(x, "Other")                      # extras are scanned too; the index sector wins if they join it
    prev_doc = _read(data_dir / FILE_NAME)
    previous = prev_doc["tickers"] if _valid(prev_doc) else builtin_default()
    tickers = merge(previous, current)
    added, removed = [t for t in tickers if t not in set(previous)], [t for t in previous if t not in current]
    if len(added) > MAX_CHANGE or len(removed) > MAX_CHANGE:
        if prev_doc is not None and _valid(prev_doc):
            raise ValueError(f"change too large (+{len(added)} / -{len(removed)}) for a routine refresh: refusing, review by hand")
    asof = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    doc = {"asof": asof, "source": WIKI, "n": len(tickers), "tickers": tickers, "sectors": {t: current[t] for t in tickers}}
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp = data_dir / (FILE_NAME + ".part")
    tmp.write_text(json.dumps(doc, separators=(",", ":")))
    tmp.replace(data_dir / FILE_NAME)                       # never leave a half-written file
    if added or removed or prev_doc is None:
        with (data_dir / LOG_NAME).open("a") as f:
            f.write(json.dumps({"at": asof, "n": len(tickers), "added": added, "removed": removed, "first_refresh": prev_doc is None}) + "\n")
    return {"n": len(tickers), "added": added, "removed": removed, "asof": asof}


def main() -> int:
    r = refresh()
    msg = f"Scan universe: {r['n']} tickers (+{len(r['added'])} added, -{len(r['removed'])} removed)"
    print(msg)
    if r["added"]:
        print("added:", " ".join(r["added"]))
    if r["removed"]:
        print("removed:", " ".join(r["removed"]))
    if "--discord" in sys.argv and (r["added"] or r["removed"]) and os.environ.get("DISCORD_WEBHOOK_URL"):
        import requests
        body = {"embeds": [{"title": "Scan universe updated", "description": msg + ("\nAdded: " + ", ".join(r["added"][:40]) if r["added"] else "")
                            + ("\nRemoved: " + ", ".join(r["removed"][:40]) if r["removed"] else ""), "color": 0x5865F2}]}
        try:
            requests.post(os.environ["DISCORD_WEBHOOK_URL"], json=body, timeout=10)
        except Exception as exc:  # noqa: BLE001
            print(f"discord post failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() if len(sys.argv) > 1 and sys.argv[1] == "refresh" else print(__doc__) or 1)
