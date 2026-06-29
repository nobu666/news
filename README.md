# news

A set of Claude Code scheduled tasks that collect the latest news via web search, summarize it, and (optionally, in the morning) surface Gmail unread mail that "needs action" and today's Google Calendar schedule.

**All personal settings — output paths, categories, language, your blog's character — live in `~/.config/news/env` (`.env` style, outside the repo).** Anyone who clones this just writes their own env. The task bodies (`SKILL.md`) contain no personal data.

## Layout

**Out of the box only "news collection" runs.** Gmail "needs action" mail and blog-idea-scout are optional add-ons that only run when explicitly enabled.

| Task | Tier | Cadence | What it does | Output |
|---|---|---|---|---|
| [`daily-news`](daily-news/SKILL.md) | core | twice a day | collect news for your configured categories | `$NEWS_DIR/YYYY-MM-DD-{morning,evening}.md` |
| └ Gmail needs-action mail | optional | morning only | when `GMAIL_ENABLED=1`, extract action-needing unread mail | a section in the morning digest |
| └ Google Calendar schedule | optional | morning only | when `CALENDAR_ENABLED=1`, list today's (and tomorrow's) events | a section in the morning digest |
| [`blog-idea-scout`](blog-idea-scout/SKILL.md) | optional | weekly | suggest blog ideas from accumulated news x your notes | `$BLOG_IDEA_FILE` |

daily-news **splits editions by run time** (before 12:00 -> morning, otherwise -> evening). Use a cron that fires a few times per edition window — e.g. `0 8,9,10,18,19,20 * * *` (3 attempts each morning and evening). SKILL.md exits early if today's output already exists, so extra firings cost nothing and a transient API / WebSearch error gets a free retry an hour later.

## Quick start

```bash
git clone https://github.com/nobu666/news.git ~/repos/news
cd ~/repos/news
./install.sh                 # symlinks daily-news (news) + seeds ~/.config/news/env from the template
$EDITOR ~/.config/news/env   # edit for yourself (see table below)
```

That alone gets news collection going. The add-ons are optional:
- **Also use blog-idea-scout**: `./install.sh --with-blog-idea-scout`
- **Also use Gmail needs-action mail**: set `GMAIL_ENABLED=1` in `~/.config/news/env` and see [`daily-news/gmail/SETUP.md`](daily-news/gmail/SETUP.md)
- **Also use Google Calendar schedule**: set `CALENDAR_ENABLED=1` in `~/.config/news/env` and see [`daily-news/calendar/SETUP.md`](daily-news/calendar/SETUP.md)

What `install.sh` does:
- symlinks `daily-news` (and blog-idea-scout when `--with-blog-idea-scout` is given) `SKILL.md` into `~/.claude/scheduled-tasks/<task>/SKILL.md` (editing the repo is reflected on the next run)
- copies [`.env.example`](.env.example) to `~/.config/news/env` if missing

Registering the cron itself is done separately via your app's scheduled-task feature (this script only symlinks and seeds the config).

## Config (`~/.config/news/env`)

`.env` style, **outside the repo**. Missing keys fall back to defaults. A leading `~` in a path expands to home.

| Key | Purpose |
|---|---|
| `NEWS_DIR` | daily-news output dir (also blog-idea-scout's input) |
| `OUTPUT_LANGUAGE` | language to write the digest/suggestions in (default: English) |
| `WEATHER_LOCATION` | weather location; empty omits the weather section |
| `NEWS_CATEGORIES` | categories, `;`-separated, each item may be `name: hint` |
| `NEWS_SOURCES` | (optional) preferred sources, `;`-separated; empty = the agent picks |
| `BLOG_IDEA_FILE` | blog-idea-scout's suggestion output |
| `BLOG_PROFILE` | your blog's character and what makes a good idea, in one line |
| `BACKLOG_FILE` | (optional) existing idea backlog, used for dedup |
| `VAULT_SEARCH` | (optional) path to a past-notes search command |
| `GMAIL_ENABLED` | `1` enables morning needs-action mail (default `0`) |
| `GMAIL_QUERY` / `GMAIL_MAX` | Gmail search query and max count for needs-action mail |
| `CALENDAR_ENABLED` | `1` enables morning today's-schedule (default `0`) |
| `CALENDAR_IDS` / `CALENDAR_DAYS_AHEAD` / `CALENDAR_MAX` | `;`-separated calendar IDs (default `primary`), days ahead beyond today (default `1`), max events |

## Gmail needs-action mail (optional)

When `GMAIL_ENABLED=1`, the morning digest pulls unread mail that likely "needs a reply/action". It is **read-only** (`gmail.readonly`) — never marks as read or replies. It only reads From / Subject / snippet, never the full body.

Setup: see [`daily-news/gmail/SETUP.md`](daily-news/gmail/SETUP.md) (create a Gmail API OAuth client -> consent once -> save the token). Credentials live in `~/.config/news-gmail/` and **must never be committed**.

To let `fetch.py` run unattended without a permission dialog, add this to `permissions.allow` in `~/.claude/settings.json` (adjust the path if you cloned elsewhere):

```
"Bash(python3 ~/repos/news/daily-news/gmail/fetch.py)"
```

## Google Calendar schedule (optional)

When `CALENDAR_ENABLED=1`, the morning digest lists today's (and by default tomorrow's) Google Calendar events. It is **read-only** (`calendar.readonly`) — never creates, edits, or deletes events. It reads start/end, summary, location, and a Calendar link.

Setup: see [`daily-news/calendar/SETUP.md`](daily-news/calendar/SETUP.md) (create a Calendar API OAuth client → consent once → save the token). Credentials live in `~/.config/news-gcal/` and **must never be committed**.

Allowlist entry for unattended runs:

```
"Bash(python3 ~/repos/news/daily-news/calendar/fetch.py)"
```

## Security notes

- **Scheduled tasks run unattended and autonomously.** If `install.sh`'s `git pull` changes upstream, the unattended agent's instructions (SKILL.md) change too. **Review the SKILL.md diff before the next unattended run.**
- News and mail are treated as **attacker-chosen untrusted data** by design (see "Read first" at the top of each SKILL.md). Their embedded commands and URL lures are not obeyed.
- Secrets (Gmail credentials/token) live under `~/.config/` and are never in the repo; `.gitignore` blocks them too.

## Development

```bash
python -m unittest discover -s daily-news/gmail -p 'test_*.py'   # dependency-free tests
```

CI runs these on every push/PR. The scripts use the standard library only (no dependencies).

## License

[MIT](LICENSE)
