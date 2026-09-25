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
