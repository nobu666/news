#!/usr/bin/env python3
"""Run once: get read-only Gmail consent in the browser and save token.json.

No dependencies. Put credentials.json {"client_id": "...", "client_secret": "..."}
into GMAIL_CONFIG_DIR (default ~/.config/news-gmail) first. Create the OAuth client
as a "Desktop app" in Google Cloud Console (loopback http://127.0.0.1 redirects are
allowed for that type, so no redirect URI registration is needed).
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.request
import urllib.parse
import webbrowser
import http.server
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("GMAIL_CONFIG_DIR", Path.home() / ".config" / "news-gmail"))
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}"

_received = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _received["code"] = params.get("code", [None])[0]
        _received["state"] = params.get("state", [None])[0]
        _received["error"] = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Authentication complete. You can return to the terminal.".encode())

    def log_message(self, *a):  # silence the server log
        pass


def _harden_perms():
    """Defensively tighten permissions on the secret dir/files (idempotent)."""
    try:
        CONFIG_DIR.chmod(0o700)
        for f in ("credentials.json", "token.json"):
            p = CONFIG_DIR / f
            if p.exists():
                p.chmod(0o600)
    except OSError:
        pass


def load_creds():
    _harden_perms()
    raw = json.loads((CONFIG_DIR / "credentials.json").read_text())
    c = raw.get("installed") or raw.get("web") or raw  # accept Google's download form ({"installed":..}) and a flat form
    return {"client_id": c["client_id"], "client_secret": c["client_secret"]}


def main():
    creds = load_creds()
    # PKCE (S256) + state to prevent authorization-code injection / CSRF
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    url = f"{AUTH_URL}?{params}"
    httpd = http.server.HTTPServer(("127.0.0.1", PORT), _Handler)
    httpd.timeout = 180  # give up if no redirect arrives (avoid hanging)
    print("Consent in the browser. If it does not open, visit this URL manually:\n" + url + "\n")
    webbrowser.open(url)
    httpd.handle_request()  # receive the single redirect

    if _received.get("error"):
        print(f"Auth error: {_received['error']}", file=sys.stderr)
        sys.exit(1)
    if _received.get("state") != state:
        print("State mismatch. Aborting (possible authorization-code injection).", file=sys.stderr)
        sys.exit(1)
    code = _received.get("code")
    if not code:
        print("Could not obtain an authorization code (possibly timed out).", file=sys.stderr)
        sys.exit(1)

    body = urllib.parse.urlencode({
        "code": code,
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)

    if "refresh_token" not in tok:
        print("No refresh_token returned. Revoke this app's access in your Google account and re-run.", file=sys.stderr)
        sys.exit(1)

    out = CONFIG_DIR / "token.json"
    out.write_text(json.dumps(tok, ensure_ascii=False, indent=2))
    out.chmod(0o600)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
