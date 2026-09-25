"""
Invite-only Google sign-in for the dashboard.

Flow: the browser gets a Google ID token (Google Identity Services button) and POSTs it to
/auth/login. We verify it with Google's public keys (signature, expiry, audience = our client
ID, email_verified), require the email to be on the invite list, then issue our own signed,
HttpOnly session cookie. Every request re-checks the invite list, so revoking someone takes
effect within ALLOW_TTL seconds even for a live session.

Fails closed: no client ID, no session secret, or an unreadable invite list means nobody gets in.

Env: GOOGLE_CLIENT_ID   OAuth "Web application" client ID (public value, not a secret)
     SESSION_SECRET     >= 32 random chars, signs session cookies (kept in Secret Manager)
     ACCESS_BUCKET      bucket holding allowed_emails.json (a JSON list of emails)
     ALLOWED_EMAILS     comma-separated list, for local development only
"""
import base64
import hashlib
import hmac
import json
import os
import time

SESSION_TTL = 12 * 3600
ALLOW_TTL = 60
COOKIE = "dash_session"

_allow = {"at": 0.0, "emails": frozenset()}


def _key() -> bytes:
    k = os.environ.get("SESSION_SECRET", "")
    if len(k) < 32:
        raise RuntimeError("SESSION_SECRET must be at least 32 characters")
    return k.encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_session(email: str, now: float = None) -> str:
    body = _b64(json.dumps({"e": email.lower(), "x": int((now or time.time()) + SESSION_TTL)}).encode())
    return body + "." + hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()


def read_session(token: str, allowed, now: float = None):
    """Email if the token is authentic, unexpired and the email is still invited; else None."""
    try:
        body, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()):
            return None
        data = json.loads(_unb64(body))
        email = str(data["e"]).lower()
        if data["x"] < (now or time.time()) or email not in allowed:
            return None
        return email
    except Exception:            # noqa: BLE001 - any malformed token is simply not a session
        return None


def allowed_emails() -> frozenset:
    """The invite list, cached ALLOW_TTL seconds. Fails closed (empty) if it cannot be read."""
    if time.time() - _allow["at"] < ALLOW_TTL:
        return _allow["emails"]
    emails = None
    try:
        if os.environ.get("ALLOWED_EMAILS"):
            emails = os.environ["ALLOWED_EMAILS"].split(",")
        elif os.environ.get("ACCESS_BUCKET"):
            from google.cloud import storage
            emails = json.loads(storage.Client().bucket(os.environ["ACCESS_BUCKET"]).blob("allowed_emails.json").download_as_text())
    except Exception as e:        # noqa: BLE001
        print(f"auth: could not read the invite list ({type(e).__name__}); denying until it can be read", flush=True)
    if emails is not None:
        _allow.update(at=time.time(), emails=frozenset(x.strip().lower() for x in emails if x.strip()))
    else:
        _allow["at"] = time.time() - ALLOW_TTL + 10        # retry soon, keep the last good list
    return _allow["emails"]


def verify_google(credential: str):
    """Email from a valid Google ID token for our client ID, else None."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id or not credential:
        return None
    try:
        from google.auth.transport import requests as greq
        from google.oauth2 import id_token
        info = id_token.verify_oauth2_token(credential, greq.Request(), client_id)
        return info["email"].lower() if info.get("email_verified") else None
    except Exception:            # noqa: BLE001 - bad signature, wrong audience, expired, network...
        return None


def cookie_header(token: str, max_age: int = SESSION_TTL) -> str:
    return f"{COOKIE}={token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={max_age}"


def token_from_cookie(header: str) -> str:
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE:
            return v
    return ""
