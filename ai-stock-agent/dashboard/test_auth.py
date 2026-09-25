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
sqlite3.connect(f"{TMP}/backtest.db").executescript(
    "create table llm_decisions(decided_at text, scan_id text, llm_status text, raw_decision text, in_signal_list int, ticker text);"
    "create table recommendations(recommendation_date text, decision text, ticker text, market_trend text);")
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
