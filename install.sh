#!/bin/bash
set -e

# By default this installs only daily-news (news collection).
# blog-idea-scout (personal blog idea suggestions) is opt-in: ./install.sh --with-blog-idea-scout
# Gmail "needs action" mail is enabled via GMAIL_ENABLED=1 in ~/.config/news/env (see SETUP.md).

REPO_DIR="${INSTALL_DIR:-$HOME/repos}/news"
TASKS_DIR="$HOME/.claude/scheduled-tasks"

WITH_SCOUT=0
for arg in "$@"; do
  case "$arg" in
    --with-blog-idea-scout) WITH_SCOUT=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

echo "=== Installing news scheduled task ==="

# Repository
echo ""
echo "--- Repository ---"
if [ -d "$REPO_DIR/.git" ]; then
  echo "Updating existing repository..."
  git -C "$REPO_DIR" pull
else
  echo "Cloning..."
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone https://github.com/nobu666/news.git "$REPO_DIR"
fi

# What to install
TASKS="daily-news"
[ "$WITH_SCOUT" = 1 ] && TASKS="$TASKS blog-idea-scout"

# Symlinks (editing the repo is reflected on the next run)
echo ""
echo "--- Symlinks ---"
mkdir -p "$TASKS_DIR"
for task in $TASKS; do
  mkdir -p "$TASKS_DIR/$task"
  ln -sf "$REPO_DIR/$task/SKILL.md" "$TASKS_DIR/$task/SKILL.md"
  echo "  $TASKS_DIR/$task/SKILL.md -> $REPO_DIR/$task/SKILL.md"
done
[ "$WITH_SCOUT" = 0 ] && echo "  (blog-idea-scout not installed. To add it: ./install.sh --with-blog-idea-scout)"

# Config file (change output paths etc. here. Seeded from the template if missing)
echo ""
echo "--- Config file ---"
NEWS_CONFIG_DIR="$HOME/.config/news"
mkdir -p "$NEWS_CONFIG_DIR"
if [ ! -f "$NEWS_CONFIG_DIR/env" ]; then
  cp "$REPO_DIR/.env.example" "$NEWS_CONFIG_DIR/env"
  echo "  Created: $NEWS_CONFIG_DIR/env (edit output dir, categories, etc.)"
else
  echo "  Exists: $NEWS_CONFIG_DIR/env (not overwritten)"
fi

echo ""
echo "=== Done ==="
echo "- daily-news: runs twice a day (morning/evening). Splits editions by run time. cron e.g. 0 8,18 * * *"
[ "$WITH_SCOUT" = 1 ] && echo "- blog-idea-scout: weekly. Suggests blog ideas from accumulated news. cron e.g. 0 19 * * 0"
echo "Edit $NEWS_CONFIG_DIR/env to configure. For Gmail mail, set GMAIL_ENABLED=1 and see daily-news/gmail/SETUP.md."
echo "Editing the repo's SKILL.md is reflected directly on the next run."
echo ""
echo "Note: registering the cron itself is done separately via your app's scheduled-task feature (this script only symlinks)."
