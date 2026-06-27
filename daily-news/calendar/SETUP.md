# Google Calendar "today's schedule" — setup (one time)

How to set up read-only Google Calendar access so the daily-news morning digest can add a "today's schedule" section.
Standard library only (no dependencies). Credentials live **outside this repository**, in `~/.config/news-gcal/`.

## 1. Enable the Calendar API (and reuse the existing OAuth client if you have one)

In the [Google Cloud Console](https://console.cloud.google.com/), pick the project where your existing OAuth client lives, then "APIs & Services" → "Library" → enable the **Google Calendar API**. That alone is the only required step here — **OAuth Desktop clients are not API-scoped**, so the `claude-news` (or whatever name) client you already set up for Gmail can authorize Calendar too. You don't need a second OAuth client.

If you don't already have a Desktop client, create one now:

- "Credentials" → "Create credentials" → "OAuth client ID" → **Application type: Desktop app** (loopback `http://127.0.0.1` redirects are allowed; no redirect URI registration needed)

## 2. Place the credentials file

**Reuse the Gmail credentials** (simplest — recommended):

```bash
mkdir -p ~/.config/news-gcal
cp ~/.config/news-gmail/credentials.json ~/.config/news-gcal/credentials.json
chmod 600 ~/.config/news-gcal/credentials.json
```

Or, if you created a fresh client just for this:

```bash
mkdir -p ~/.config/news-gcal
mv ~/Downloads/client_secret_*.json ~/.config/news-gcal/credentials.json
chmod 600 ~/.config/news-gcal/credentials.json
```

`token.json` is **not** reusable — it's bound to its OAuth scope. The next step mints a Calendar-scoped one.

## 3. Consent once to mint a token

```bash
python3 ~/repos/news/daily-news/calendar/auth.py
```

A browser opens → consent with your Google account → `~/.config/news-gcal/token.json` is saved.
Token refreshes headlessly after this. For unattended use, **publish the app to "Production"** so the refresh token does not expire after 7 days.

## 4. Verify

```bash
python3 ~/repos/news/daily-news/calendar/fetch.py --check
CALENDAR_ENABLED=1 python3 ~/repos/news/daily-news/calendar/fetch.py | head
```

Then set `CALENDAR_ENABLED=1` in `~/.config/news/env` so the morning digest actually runs this.

### Picking calendar IDs (TimeTree sync, secondary calendars, etc.)

If your events sit in a calendar other than `primary` (e.g. **TimeTree sync** publishes a separate Google calendar; shared/family calendars are also separate), `primary` won't see them. List every calendar with its ID:

```bash
python3 ~/repos/news/daily-news/calendar/fetch.py --list-calendars
```

Output is one calendar per line, tab-separated: `<calendar id>\t<name> [primary]`. Paste the IDs you want into `CALENDAR_IDS` in `~/.config/news/env` (`;`-separated):

```
CALENDAR_IDS=primary;abc123@group.calendar.google.com
```

## Notes

- Scope is `calendar.readonly`. It never creates/edits/deletes events.
- It reads start/end, summary, location, and a Calendar link. Description/attendees are not fetched.
- Window: today 00:00 (local tz) → (today + `CALENDAR_DAYS_AHEAD` + 1) 00:00. Default `1` = today + tomorrow.
- Calendars: `CALENDAR_IDS` (`;`-separated; default `primary`). Use additional calendar IDs from "Calendar settings → Integrate calendar → Calendar ID".
- `credentials.json` / `token.json` are secrets. `.gitignore` already covers `~/.config/news-*/`, and they live outside the repo anyway.
