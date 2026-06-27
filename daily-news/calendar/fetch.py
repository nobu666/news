#!/usr/bin/env python3
"""Print today's (and tomorrow's, by default) Google Calendar events as JSON (read-only).

No dependencies (standard library only). Credentials live in CALENDAR_CONFIG_DIR
(default ~/.config/news-gcal):
  credentials.json : {"client_id": "...", "client_secret": "..."}   <- create by hand
  token.json       : produced by auth.py (contains the refresh_token)

Output: a JSON array of [{start, end, all_day, summary, location, link, calendar}] on stdout.
On failure it prints {"error": "..."} and exits 1 (the caller can still continue).
Scope is calendar.readonly: it never writes/modifies events.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_env_file():
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
    os.environ.get("CALENDAR_CONFIG_DIR", str(Path.home() / ".config" / "news-gcal"))
).expanduser()
CALENDAR_IDS = [c.strip() for c in os.environ.get("CALENDAR_IDS", "primary").split(";") if c.strip()]
DAYS_AHEAD = int(os.environ.get("CALENDAR_DAYS_AHEAD", "1"))  # 1 = today + tomorrow
MAX_RESULTS = int(os.environ.get("CALENDAR_MAX", "50"))
# Cap each text field to keep one bloated event from swelling the digest.
MAX_FIELD_LEN = int(os.environ.get("CALENDAR_MAX_FIELD_LEN", "200"))
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/calendar/v3/calendars"
LIST_API = "https://www.googleapis.com/calendar/v3/users/me/calendarList"


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
    c = raw.get("installed") or raw.get("web") or raw
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


def _truncate(s, limit=None):
    """Bound a free-form string from the API so one bloated event can't blow up the digest."""
    if not s:
        return ""
    n = limit if limit is not None else MAX_FIELD_LEN
    return s if len(s) <= n else s[: n - 1] + "…"  # ellipsis


def _window():
    # Local-midnight today .. local-midnight (today + DAYS_AHEAD + 1).
    # Use the system's local tz (datetime.now().astimezone() resolves the offset).
    now_local = datetime.now().astimezone()
    start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=DAYS_AHEAD + 1)
    return start.isoformat(), end.isoformat()


def fetch():
    token = access_token()
    time_min, time_max = _window()
    out = []
    for cal_id in CALENDAR_IDS:
        q = urllib.parse.urlencode({
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": MAX_RESULTS,
        })
        listing = _get(f"{API}/{urllib.parse.quote(cal_id, safe='')}/events?{q}", token)
        for e in listing.get("items", []):
            if e.get("status") == "cancelled":
                continue
            s = e.get("start", {})
            t = e.get("end", {})
            all_day = "date" in s
            out.append({
                "start": s.get("dateTime") or s.get("date") or "",
                "end": t.get("dateTime") or t.get("date") or "",
                "all_day": all_day,
                "summary": _truncate(e.get("summary", "")) or "(no title)",
                "location": _truncate(e.get("location", "")),
                "link": e.get("htmlLink", ""),
                "calendar": cal_id,
            })
    out.sort(key=lambda x: (x["start"], x["summary"]))
    return out


def list_calendars():
    """Print all calendars the user can see, with their IDs — useful when setting CALENDAR_IDS."""
    token = access_token()
    listing = _get(LIST_API, token)
    for c in listing.get("items", []):
        summary = c.get("summaryOverride") or c.get("summary", "(no name)")
        primary = " [primary]" if c.get("primary") else ""
        print(f"{c.get('id', '')}\t{summary}{primary}")


def main():
    if "--check" in sys.argv:
        ok = (CONFIG_DIR / "credentials.json").exists() and (CONFIG_DIR / "token.json").exists()
        print("OK" if ok else f"FAIL: credentials missing ({CONFIG_DIR})")
        sys.exit(0 if ok else 1)
    if "--list-calendars" in sys.argv:
        try:
            list_calendars()
        except Exception as e:  # noqa: BLE001
            print(f"{type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
        return
    if os.environ.get("CALENDAR_ENABLED", "0").strip().lower() not in ("1", "true", "yes", "on"):
        print("[]")  # disabled (default). Set CALENDAR_ENABLED=1 in ~/.config/news/env to use it.
        return
    try:
        json.dump(fetch(), sys.stdout, ensure_ascii=False, indent=2)
        print()
    except Exception as e:  # noqa: BLE001
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        json.dump({"error": type(e).__name__}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
