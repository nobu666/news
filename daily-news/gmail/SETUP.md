# Gmail "needs action" mail — setup (one time)

How to set up read-only Gmail access so the daily-news morning digest can add a "needs action" section.
The scripts use the standard library only (no dependencies to install). Credentials live **outside this
repository**, in `~/.config/news-gmail/`.

## 1. Create an OAuth client in Google Cloud

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project (or reuse one)
2. "APIs & Services" -> "Library" -> enable the **Gmail API**
3. Configure the "OAuth consent screen" (User type: External; you can add your own Gmail as a test user)
4. "Credentials" -> "Create credentials" -> "OAuth client ID" -> **Application type: Desktop app**
   - Desktop apps allow loopback (`http://127.0.0.1`) redirects, so no redirect URI registration is needed
5. After creating it, note the **client ID** and **client secret**

## 2. Place the credentials file

You can drop in the **OAuth client JSON downloaded from the Console as-is** (the `{"installed": {...}}` form is supported):

```bash
mkdir -p ~/.config/news-gmail
mv ~/Downloads/client_secret_*.json ~/.config/news-gmail/credentials.json
chmod 600 ~/.config/news-gmail/credentials.json
```

Or write just the client_id / client_secret in a flat form:

```bash
cat > ~/.config/news-gmail/credentials.json <<'JSON'
{ "client_id": "YOUR_CLIENT_ID", "client_secret": "YOUR_SECRET" }
JSON
chmod 600 ~/.config/news-gmail/credentials.json
```

## 3. Consent once to mint a token

```bash
python3 ~/repos/news/daily-news/gmail/auth.py
```

A browser opens -> consent with your Gmail -> `~/.config/news-gmail/token.json` (with the refresh_token) is saved.
After this, the token is refreshed headlessly, so no re-consent is needed (unless you revoke access).

If your consent screen is still in "Testing", add your Gmail as a test user. For unattended use, **publish the app
to "Production"** so the refresh token does not expire after 7 days.

## 4. Verify

```bash
python3 ~/repos/news/daily-news/gmail/fetch.py --check   # are the credential files present?
GMAIL_ENABLED=1 python3 ~/repos/news/daily-news/gmail/fetch.py | head   # do unread candidates print as JSON?
```

Also set `GMAIL_ENABLED=1` in `~/.config/news/env` so the morning digest actually runs this.

## Notes

- Scope is `gmail.readonly`. It never marks as read, replies, or deletes (unread stays unread).
- It only reads From / Subject / Date / snippet (first ~100 chars) / a Gmail link. It never fetches the full body.
- Filtering is `GMAIL_QUERY` (default `is:unread -category:promotions -category:social newer_than:14d`),
  overridable via `~/.config/news/env`.
- `credentials.json` and `token.json` are secrets. Never commit them (kept under `~/.config/news-gmail/`, and `.gitignore` blocks them too).
