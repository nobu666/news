#!/usr/bin/env python3
"""Delete daily-news digests older than NEWS_RETENTION_DAYS, as JSON (best-effort).

No dependencies (standard library only). Reads NEWS_DIR and NEWS_RETENTION_DAYS
from ~/.config/news/env (existing env wins). NEWS_RETENTION_DAYS unset or 0
disables pruning entirely.

Only files named exactly YYYY-MM-DD-morning.md / YYYY-MM-DD-evening.md are
considered, and age is judged by the filename date (not mtime, which file-sync
tools may touch). Anything else in NEWS_DIR is never deleted.

Output: {"deleted": [...], "kept": N} on stdout. Always exits 0 so the digest
run never fails because of pruning.
"""
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

FILENAME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(morning|evening)\.md$")


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


def prune(news_dir: Path, retention_days: int, today: date) -> dict:
    """Delete matching digests dated before today - retention_days. Pure logic, testable."""
    deleted, kept = [], 0
    cutoff = today - timedelta(days=retention_days)
    for f in sorted(news_dir.iterdir()):
        m = FILENAME.match(f.name)
        if not m or not f.is_file():
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue  # e.g. 2026-13-40: not a real date, leave it alone
        if d < cutoff:
            f.unlink()
            deleted.append(f.name)
        else:
            kept += 1
    return {"deleted": deleted, "kept": kept}


def main():
    _load_env_file()
    try:
        days = int(os.environ.get("NEWS_RETENTION_DAYS", "0") or "0")
    except ValueError:
        days = 0
    if days < 1:
        print(json.dumps({"deleted": [], "kept": 0, "disabled": True}))
        return
    news_dir = Path(os.environ.get("NEWS_DIR", "~/news")).expanduser()
    if not news_dir.is_dir():
        print(json.dumps({"deleted": [], "kept": 0}))
        return
    try:
        print(json.dumps(prune(news_dir, days, date.today())))
    except Exception as e:  # best-effort: never break the digest run
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()
