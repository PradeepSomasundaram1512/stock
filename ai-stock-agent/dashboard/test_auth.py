"""Security tests for the dashboard's sign-in. Run:  python -m unittest dashboard.test_auth -v  (or python dashboard/test_auth.py)"""
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
TMP = tempfile.mkdtemp()
Path(f"{TMP}/market_snapshot.json").write_text(json.dumps({"asof": "2099-01-01T00:00:00+00:00", "n": 2, "missing": [], "stocks": {
    "AAPL": {"p": 1.0, "c": 0.01, "c5": 0.02, "rsi": 55.0, "dv": 1e9, "d": "2026-09-25"}, "ZZZZ": {"p": 2.0, "c": -0.02, "c5": 0.0, "rsi": None, "dv": 1e6, "d": "2026-09-25"}}}))
_con = sqlite3.connect(f"{TMP}/backtest.db")
_con.executescript("""
create table llm_decisions(scan_id text, decided_at text, ticker text, llm_status text, raw_decision text, raw_confidence real, in_signal_list int,
  final_decision text, price real, rsi real, trend text, risk_level text, price_target real, stop_loss real, reasoning text);
create table shadow_decisions(scan_id text, decided_at text, ticker text, llm_status text, decision text, confidence real, shadow_model text, est_cost_usd real);
create table recommendations(recommendation_date text, ticker text, decision text, confidence real, entry_price real, price_target real, stop_loss real,
  outcome text, exit_date text, exit_price real, profit_loss_pct real, exit_reason text, scan_type text, market_trend text, rsi real, trend text);
-- an OLDER scan (AAA buy, BBB hold) and the LATEST scan (BBB sell, CCC buy, AAPL hold)
insert into llm_decisions values ('old','2026-09-24T19:00:00','AAA','ok','BUY',0.9,1,'BUY',10,50,'up','low',12,9,'old reason');
insert into llm_decisions values ('old','2026-09-24T19:00:01','BBB','ok','HOLD',0.5,0,null,20,50,'up','low',null,null,'old hold');
insert into llm_decisions values ('new','2026-09-25T19:00:00','BBB','ok','SELL',0.7,1,'WATCH SELL',21,60,'down','high',null,null,'new sell');
insert into llm_decisions values ('new','2026-09-25T19:00:01','CCC','ok','BUY',0.8,1,'BUY',30,40,'up','low',33,28,'new buy');
insert into llm_decisions values ('new','2026-09-25T19:00:02','AAPL','ok','HOLD',0.5,0,null,1,50,'flat','low',null,null,'hold');
insert into shadow_decisions values ('old','2026-09-24T19:00:00','AAA','ok','HOLD',0.5,'m',0.01);
insert into shadow_decisions values ('old','2026-09-24T19:00:01','BBB','ok','HOLD',0.5,'m',0.01);
insert into shadow_decisions values ('new','2026-09-25T19:00:00','BBB','ok','SELL',0.6,'m',0.01);
insert into shadow_decisions values ('new','2026-09-25T19:00:01','CCC','ok','HOLD',0.5,'m',0.01);
insert into shadow_decisions values ('new','2026-09-25T19:00:02','AAPL','ok','HOLD',0.5,'m',0.01);
""")
# closed BUY history for the "similar calls" cohorts: 30 at RSI ~45 / uptrend (18 wins), 30 at RSI 80 / downtrend (3 wins), 5 still open
for i in range(30):
    _con.execute("insert into recommendations values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("2026-03-01", "H", "BUY", 0.8, 1, 1, 1, "WIN" if i < 18 else "LOSS", None, None, 1.0 if i < 18 else -1.0, None, None, None, 45.0, "up"))
    _con.execute("insert into recommendations values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("2026-03-02", "H", "BUY", 0.8, 1, 1, 1, "WIN" if i < 3 else "LOSS", None, None, 1.0 if i < 3 else -1.0, None, None, None, 80.0, "down"))
for i in range(5):
    _con.execute("insert into recommendations values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("2026-09-01", "H", "BUY", 0.8, 1, 1, 1, None, None, None, None, None, None, None, 45.0, "up"))
_con.commit()
_con.close()
os.environ.update(SESSION_SECRET="x" * 40, ALLOWED_EMAILS="alice@example.com,bob@example.com", GOOGLE_CLIENT_ID="test-client",
                  DATA_DIR=TMP)
os.environ.pop("DASHBOARD_DEV_NO_AUTH", None)
import auth      # noqa: E402
import server    # noqa: E402


def call(base, path, cookie=None, method="GET", body=None):
    req = urllib.request.Request(base + path, method=method, data=body, headers={"Cookie": cookie} if cookie else {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers


class SessionTests(unittest.TestCase):
    allowed = {"alice@example.com"}

    def test_roundtrip(self):
        self.assertEqual(auth.read_session(auth.sign_session("Alice@Example.com"), self.allowed), "alice@example.com")

    def test_tampered_body_and_signature(self):
        t = auth.sign_session("alice@example.com")
        body, sig = t.rsplit(".", 1)
        forged = auth._b64(json.dumps({"e": "mallory@evil.com", "x": 9999999999}).encode())
        self.assertIsNone(auth.read_session(forged + "." + sig, {"mallory@evil.com"}))
        self.assertIsNone(auth.read_session(body + "." + "0" * 64, self.allowed))

    def test_expired(self):
        t = auth.sign_session("alice@example.com", now=1000)
        self.assertIsNone(auth.read_session(t, self.allowed, now=1000 + auth.SESSION_TTL + 1))

    def test_revoked_after_issue(self):
        self.assertIsNone(auth.read_session(auth.sign_session("alice@example.com"), {"bob@example.com"}))

    def test_garbage(self):
        for bad in ("", "abc", "a.b", "....", "\x00", "e30.zz"):
            self.assertIsNone(auth.read_session(bad, self.allowed))

    def test_fails_closed_without_secret(self):
        old = os.environ["SESSION_SECRET"]
        os.environ["SESSION_SECRET"] = "short"
        try:
            with self.assertRaises(RuntimeError):
                auth.sign_session("alice@example.com")
            self.assertIsNone(auth.read_session("a.b", self.allowed))
        finally:
            os.environ["SESSION_SECRET"] = old

    def test_google_verify_rejects_junk_and_missing_client(self):
        self.assertIsNone(auth.verify_google("not-a-token"))
        self.assertIsNone(auth.verify_google(""))
        old = os.environ.pop("GOOGLE_CLIENT_ID")
        try:
            self.assertIsNone(auth.verify_google("anything"))
        finally:
            os.environ["GOOGLE_CLIENT_ID"] = old


class RateLimitTests(unittest.TestCase):
    def test_limits_per_key_and_recovers(self):
        rl = auth.RateLimiter(limit=3, window=60)
        self.assertEqual([rl.allow("a", now=t) for t in (0, 1, 2, 3)], [True, True, True, False])
        self.assertTrue(rl.allow("b", now=3))                                   # another address is unaffected
        self.assertFalse(rl.allow("a", now=59))
        self.assertTrue(rl.allow("a", now=61))                                  # the oldest attempt has aged out

    def test_memory_stays_bounded_under_a_flood_of_addresses(self):
        rl = auth.RateLimiter(limit=1, window=10)
        for i in range(12000):
            rl.allow(f"ip{i}", now=i * 0.01)
        self.assertLess(len(rl.hits), 12000)

    def test_only_the_last_forwarded_address_is_trusted(self):
        self.assertEqual(auth.client_ip("6.6.6.6, 1.2.3.4", "10.0.0.1"), "1.2.3.4")   # attacker-supplied prefix is ignored
        self.assertEqual(auth.client_ip("", "10.0.0.1"), "10.0.0.1")


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def cookie(self, email):
        return f"{auth.COOKIE}={auth.sign_session(email)}"

    def test_health_is_open(self):
        self.assertEqual(call(self.base, "/healthz")[0], 200)

    def test_signed_out_gets_login_page_only(self):
        code, body, _ = call(self.base, "/")
        self.assertEqual(code, 200)
        self.assertIn("Invite-only", body)
        self.assertNotIn("api/summary", body)            # none of the dashboard's code is served
        self.assertIn("test-client", body)               # the public client ID is injected

    def test_every_api_route_needs_a_session(self):
        for p in list(server.ROUTES) + ["/api/me"]:
            self.assertEqual(call(self.base, p)[0], 401, p)

    def test_forged_and_revoked_cookies_rejected(self):
        self.assertEqual(call(self.base, "/api/me", f"{auth.COOKIE}=forged.value")[0], 401)
        self.assertEqual(call(self.base, "/api/me", self.cookie("mallory@evil.com"))[0], 401)

    def test_invited_session_works(self):
        code, body, _ = call(self.base, "/api/me", self.cookie("alice@example.com"))
        self.assertEqual((code, json.loads(body)["email"]), (200, "alice@example.com"))
        self.assertEqual(call(self.base, "/api/summary", self.cookie("alice@example.com"))[0], 200)
        code, body, _ = call(self.base, "/", self.cookie("alice@example.com"))
        self.assertIn("api/summary", body)               # the dashboard itself

    def test_login_rejects_bad_tokens_and_sets_no_cookie(self):
        code, _, h = call(self.base, "/auth/login", method="POST", body=json.dumps({"credential": "junk"}).encode())
        self.assertEqual(code, 401)
        self.assertIsNone(h.get("Set-Cookie"))
        self.assertEqual(call(self.base, "/auth/login", method="POST", body=b"{not json")[0], 400)
        self.assertEqual(call(self.base, "/auth/login", method="POST", body=b"x" * 9000)[0], 400)

    def test_public_routes_need_no_session_and_expose_no_signals(self):
        for path in ("/public", "/api/public", "/charts.js"):
            self.assertEqual(call(self.base, path)[0], 200, path)
        code, body, _ = call(self.base, "/api/public")
        d = json.loads(body)
        self.assertEqual(set(d), {"audit", "forward", "forward_needs", "chain", "revealed_rows"})
        self.assertNotIn('"ticker"', body)                       # aggregates only: no per-stock rows
        self.assertNotIn("email", body)
        self.assertIn("Not investment advice", call(self.base, "/public")[1])

    def test_public_allowlist_is_exact(self):
        # near-misses of public paths must not become public
        for path in ("/public/../api/summary", "/api/public/x", "/publicx", "/api/scoreboard", "/api/arena", "/api/ticker?t=AAPL"):
            self.assertNotEqual(call(self.base, path)[0], 200, path)
        self.assertEqual(call(self.base, "/api/summary")[0], 401)
        self.assertEqual(call(self.base, "/api/latest")[0], 401)

    def test_ticker_input_is_validated_before_it_reaches_an_outbound_url(self):
        bad = "AAPL,../../etc/passwd,a b,AAPL?x=1,<script>,,TOOLONGTICKER1,MSFT,AAPL"
        self.assertEqual(server._clean_tickers(bad), ["AAPL", "MSFT"])                   # deduped, junk dropped
        self.assertEqual(len(server._clean_tickers(",".join(f"T{i}" for i in range(100)))), 40)
        self.assertEqual(server._clean_tickers("^VIX,BRK-B"), ["^VIX", "BRK-B"])

    def test_chart_rejects_bad_ticker_and_range(self):
        c = self.cookie("alice@example.com")
        self.assertIn("error", json.loads(call(self.base, "/api/chart?t=../x", c)[1]))
        self.assertIn("error", json.loads(call(self.base, "/api/chart?t=AAPL&range=99y", c)[1]))

    def test_heatmap_joins_sectors_and_marks_unknown_as_other(self):
        code, body, _ = call(self.base, "/api/heatmap", self.cookie("alice@example.com"))
        d = json.loads(body)
        self.assertEqual(code, 200)
        by = {x["t"]: x for x in d["stocks"]}
        self.assertNotEqual(by["AAPL"]["sector"], "Other")                              # real sector from sectors.json
        self.assertEqual(by["ZZZZ"]["sector"], "Other")
        self.assertTrue(by["AAPL"]["analysed"])                                                    # in the latest scan
        self.assertFalse(by["ZZZZ"]["analysed"])
        self.assertEqual({s["name"] for s in d["sectors"]}, {by["AAPL"]["sector"], "Other"})

    def test_redirect_login_requires_matching_csrf_token_and_a_valid_google_token(self):
        def post(form, cookie=None):
            req = urllib.request.Request(self.base + "/auth/google", data=form.encode(), method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded", **({"Cookie": cookie} if cookie else {})})
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k):
                    return None
            try:
                r = urllib.request.build_opener(NoRedirect).open(req)
                return r.status, r.headers
            except urllib.error.HTTPError as e:
                return e.code, e.headers
        self.assertEqual(post("credential=x")[0], 400)                                           # no CSRF token at all
        self.assertEqual(post("credential=x&g_csrf_token=abc", "g_csrf_token=different")[0], 400)   # mismatch
        code, h = post("credential=junk&g_csrf_token=abc", "g_csrf_token=abc")                      # CSRF ok, token invalid
        self.assertEqual((code, h.get("Location")), (303, "/?denied=1"))
        self.assertIsNone(h.get("Set-Cookie"))

    def test_app_install_assets_are_public(self):
        self.assertIn(call(self.base, "/manifest.webmanifest")[0], (200, 404))                   # 404 only if not generated yet

    def test_overview_describes_only_the_latest_scan(self):
        c = self.cookie("alice@example.com")
        d = json.loads(call(self.base, "/api/summary", c)[1])
        self.assertNotIn("today", d)                                            # no whole-day roll-up
        self.assertEqual((d["scan_id"], d["scan"]["decisions"], d["scan"]["buys"]), ("new", 3, 1))   # not the old scan's rows
        self.assertEqual(d["shadow_scan"]["n"], 3)
        l = json.loads(call(self.base, "/api/latest", c)[1])
        self.assertEqual({x["ticker"] for x in l["candidates"]}, {"BBB", "CCC", "AAPL"})           # AAA (old scan only) is absent
        self.assertEqual(json.loads(call(self.base, "/api/latest?scan=old", c)[1])["scan_id"], "old")   # older scans stay reachable on request

    def test_ticker_latest_call_says_whether_it_is_from_the_latest_scan(self):
        c = self.cookie("alice@example.com")
        bbb = json.loads(call(self.base, "/api/ticker?t=BBB", c)[1])["latest_call"]
        self.assertEqual((bbb["decision"], bbb["in_latest_scan"]), ("SELL", True))                 # newest, not the earlier HOLD
        aaa = json.loads(call(self.base, "/api/ticker?t=AAA", c)[1])["latest_call"]
        self.assertEqual((aaa["decision"], aaa["in_latest_scan"]), ("BUY", False))                 # honest: not in the latest scan
        self.assertIsNone(json.loads(call(self.base, "/api/ticker?t=NOPE", c)[1])["latest_call"])

    def test_arena_defaults_to_the_latest_scan(self):
        c = self.cookie("alice@example.com")
        latest = json.loads(call(self.base, "/api/arena", c)[1])
        self.assertEqual((latest["scope"], latest["n"], latest["scan_id"]), ("latest", 3, "new"))
        self.assertEqual(latest["n_disagree"], 1)                                                  # CCC only; the old scan's are excluded
        everything = json.loads(call(self.base, "/api/arena?scope=all", c)[1])
        self.assertEqual((everything["scope"], everything["n"]), ("all", 5))

    def test_login_endpoints_are_rate_limited_and_headers_present(self):
        old = server.LOGIN_LIMIT
        server.LOGIN_LIMIT = auth.RateLimiter(limit=3, window=300)
        try:
            codes = [call(self.base, "/auth/login", method="POST", body=json.dumps({"credential": "junk"}).encode())[0] for _ in range(5)]
            self.assertEqual(codes, [401, 401, 401, 429, 429])
            code, _, h = call(self.base, "/auth/login", method="POST", body=b"{}")
            self.assertEqual((code, h.get("Retry-After")), (429, "300"))
        finally:
            server.LOGIN_LIMIT = old
        h = call(self.base, "/")[2]
        self.assertIn("max-age", h.get("Strict-Transport-Security", ""))
        self.assertIn("camera=()", h.get("Permissions-Policy", ""))

    def test_similar_calls_use_closed_history_and_report_honest_intervals(self):
        c = self.cookie("alice@example.com")
        # CCC's latest call in the fixture is BUY with no RSI-40..50 match by design; give it one via the ticker's own row
        d = json.loads(call(self.base, "/api/similar?t=CCC", c)[1])
        self.assertTrue(d["available"])
        self.assertEqual(d["decision"], "BUY")
        self.assertEqual(d["all_same_decision"]["n"], 60)                                          # the 5 open calls are excluded
        self.assertAlmostEqual(d["all_same_decision"]["win_rate"], 21 / 60)
        self.assertEqual(d["similar"]["n"], 30)                                                    # RSI 40 +/- 8 and 'up' -> the 45/up cohort
        self.assertAlmostEqual(d["similar"]["win_rate"], 0.6)
        self.assertTrue(d["similar"]["lo"] < 0.6 < d["similar"]["hi"])                              # a real interval, not a point claim
        self.assertFalse(json.loads(call(self.base, "/api/similar?t=NOPE", c)[1])["available"])
        self.assertEqual(call(self.base, "/api/similar?t=CCC")[0], 401)                            # signed-out: refused

    def test_wilson_interval_behaves(self):
        lo, hi = server._wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertTrue(0.25 < hi < 0.35)                                                          # 0/10 is NOT "0% for sure"
        lo, hi = server._wilson(50, 100)
        self.assertTrue(0.40 < lo < 0.42 and 0.58 < hi < 0.60)
        self.assertIsNone(server._wilson(0, 0))

    def test_dev_bypass_is_off(self):
        self.assertFalse(server.DEV_NO_AUTH)

    def test_security_headers(self):
        h = call(self.base, "/")[2]
        self.assertEqual(h.get("X-Frame-Options"), "DENY")
        self.assertEqual(h.get("Cache-Control"), "no-store")

    def test_cookie_flags(self):
        c = auth.cookie_header("t")
        for flag in ("HttpOnly", "Secure", "SameSite=Lax"):
            self.assertIn(flag, c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
