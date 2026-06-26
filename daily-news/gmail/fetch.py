#!/usr/bin/env python3
"""Print unread Gmail messages that may need a reply/action, as JSON (read-only).

No dependencies (standard library only). Credentials live in GMAIL_CONFIG_DIR
(default ~/.config/news-gmail):
  credentials.json : {"client_id": "...", "client_secret": "..."}   <- create by hand
  token.json       : produced by auth.py (contains the refresh_token)

Output: a JSON array of [{from, subject, date, snippet, link}] on stdout.
On failure it prints {"error": "..."} and exits 1 (the caller can still continue).
Scope is gmail.readonly: it never marks as read, replies, or deletes.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path


def _load_env_file():
    """Feed ~/.config/news/env (.env style) into missing env vars (existing env wins)."""
    p = Path(os.environ.get("NEWS_ENV", Path.home() / ".config" / "news" / "env")).expanduser()
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env_file()

CONFIG_DIR = Path(
    os.environ.get("GMAIL_CONFIG_DIR", str(Path.home() / ".config" / "news-gmail"))
).expanduser()
# Narrow to unread that might need action; drop promotions/social.
# Add -category:updates if it is too noisy; widen newer_than if it misses things.
QUERY = os.environ.get("GMAIL_QUERY", "is:unread -category:promotions -category:social newer_than:14d")
MAX_RESULTS = int(os.environ.get("GMAIL_MAX", "40"))
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


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


def access_token():
    creds = load_creds()
    tok = json.loads((CONFIG_DIR / "token.json").read_text())
    resp = _post(TOKEN_URL, {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    })
    return resp["access_token"]


def fetch():
    token = access_token()
    q = urllib.parse.urlencode({"q": QUERY, "maxResults": MAX_RESULTS})
    listing = _get(f"{API}?{q}", token)
    out = []
    for m in listing.get("messages", []):
        meta = urllib.parse.urlencode(
            {"format": "metadata"},
        ) + "&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
        msg = _get(f"{API}/{m['id']}?{meta}", token)
        h = {x["name"].lower(): x["value"] for x in msg.get("payload", {}).get("headers", [])}
        out.append({
            "from": h.get("from", ""),
            "subject": h.get("subject", "(no subject)"),
            "date": h.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "link": f"https://mail.google.com/mail/u/0/#all/{m['id']}",
        })
    return out


def main():
    if "--check" in sys.argv:
        ok = (CONFIG_DIR / "credentials.json").exists() and (CONFIG_DIR / "token.json").exists()
        print("OK" if ok else f"FAIL: credentials missing ({CONFIG_DIR})")
        sys.exit(0 if ok else 1)
    if os.environ.get("GMAIL_ENABLED", "0").strip().lower() not in ("1", "true", "yes", "on"):
        print("[]")  # disabled (default). Set GMAIL_ENABLED=1 in ~/.config/news/env to use it.
        return
    try:
        json.dump(fetch(), sys.stdout, ensure_ascii=False, indent=2)
        print()
    except Exception as e:  # noqa: BLE001 — unattended: don't crash, return an error instead
        # Exception text can leak a URL etc., so stdout gets only the type name (it ends up written to the digest). Details go to stderr.
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        json.dump({"error": type(e).__name__}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
