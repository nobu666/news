# Google Calendar "today's schedule" — setup (one time)

How to set up read-only Google Calendar access so the daily-news morning digest can add a "today's schedule" section.
Standard library only (no dependencies). Credentials live **outside this repository**, in `~/.config/news-gcal/`.

## 1. Create an OAuth client in Google Cloud

You can reuse the project you set up for Gmail. Just enable the Calendar API and create a separate Desktop OAuth client.

1. In the [Google Cloud Console](https://console.cloud.google.com/), pick your project
2. "APIs & Services" → "Library" → enable the **Google Calendar API**
3. "Credentials" → "Create credentials" → "OAuth client ID" → **Application type: Desktop app**
   - Desktop apps allow loopback (`http://127.0.0.1`) redirects; no redirect URI registration needed
4. Note the **client ID** and **client secret**

## 2. Place the credentials file

```bash
mkdir -p ~/.config/news-gcal
mv ~/Downloads/client_secret_*.json ~/.config/news-gcal/credentials.json
chmod 600 ~/.config/news-gcal/credentials.json
```

Or write a flat form:

```bash
cat > ~/.config/news-gcal/credentials.json <<'JSON'
{ "client_id": "YOUR_CLIENT_ID", "client_secret": "YOUR_SECRET" }
JSON
chmod 600 ~/.config/news-gcal/credentials.json
```

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

## Notes

- Scope is `calendar.readonly`. It never creates/edits/deletes events.
- It reads start/end, summary, location, and a Calendar link. Description/attendees are not fetched.
- Window: today 00:00 (local tz) → (today + `CALENDAR_DAYS_AHEAD` + 1) 00:00. Default `1` = today + tomorrow.
- Calendars: `CALENDAR_IDS` (`;`-separated; default `primary`). Use additional calendar IDs from "Calendar settings → Integrate calendar → Calendar ID".
- `credentials.json` / `token.json` are secrets. `.gitignore` already covers `~/.config/news-*/`, and they live outside the repo anyway.
