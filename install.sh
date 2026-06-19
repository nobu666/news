#!/bin/bash
set -e

REPO_DIR="${INSTALL_DIR:-$HOME/repos}/news"
TASKS_DIR="$HOME/.claude/scheduled-tasks"

echo "=== news (tech-news scheduled tasks) インストール ==="

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
for task in tech-news-morning tech-news-evening; do
  mkdir -p "$TASKS_DIR/$task"
  ln -sf "$REPO_DIR/$task/SKILL.md" "$TASKS_DIR/$task/SKILL.md"
  echo "  $TASKS_DIR/$task/SKILL.md -> $REPO_DIR/$task/SKILL.md"
done

echo ""
echo "=== 完了 ==="
echo "scheduled-tasks に morning / evening を symlink しました。"
echo "リポジトリ側の SKILL.md を編集すると、そのまま反映されます。"
