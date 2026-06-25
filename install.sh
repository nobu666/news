#!/bin/bash
set -e

REPO_DIR="${INSTALL_DIR:-$HOME/repos}/news"
TASKS_DIR="$HOME/.claude/scheduled-tasks"

echo "=== news (daily-news scheduled task) インストール ==="

# リポジトリ
echo ""
echo "--- リポジトリ ---"
if [ -d "$REPO_DIR/.git" ]; then
  echo "既存のリポジトリを更新..."
  git -C "$REPO_DIR" pull
else
  echo "クローン中..."
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone https://github.com/nobu666/news.git "$REPO_DIR"
fi

# シンボリックリンク（リポジトリを編集すれば即反映される）
echo ""
echo "--- シンボリックリンク ---"
mkdir -p "$TASKS_DIR"
for task in daily-news blog-idea-scout; do
  mkdir -p "$TASKS_DIR/$task"
  ln -sf "$REPO_DIR/$task/SKILL.md" "$TASKS_DIR/$task/SKILL.md"
  echo "  $TASKS_DIR/$task/SKILL.md -> $REPO_DIR/$task/SKILL.md"
done

echo ""
echo "=== 完了 ==="
echo "scheduled-tasks に daily-news と blog-idea-scout を symlink しました。"
echo "- daily-news: 1日2回（朝・夕）。実行時刻で朝刊/夕刊を出し分け。cron 例: 0 8,18 * * *"
echo "- blog-idea-scout: 週1（日曜夜）。ニュース蓄積からブログネタを提案。cron 例: 0 19 * * 0"
echo "リポジトリ側の SKILL.md を編集すると、そのまま反映されます。"
echo ""
echo "※ cron 登録自体はアプリの scheduled-task 機能で別途行う（このスクリプトは symlink のみ）。"
