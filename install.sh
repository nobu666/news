#!/bin/bash
set -e

# 既定では daily-news（ニュース収集）だけをインストールする。
# blog-idea-scout（個人ブログ向けのネタ提案）はオプトイン: ./install.sh --with-blog-idea-scout
# Gmail 要対応メールは ~/.config/news/env の GMAIL_ENABLED=1 で有効化（別途 SETUP.md）。

REPO_DIR="${INSTALL_DIR:-$HOME/repos}/news"
TASKS_DIR="$HOME/.claude/scheduled-tasks"

WITH_SCOUT=0
for arg in "$@"; do
  case "$arg" in
    --with-blog-idea-scout) WITH_SCOUT=1 ;;
    *) echo "不明な引数: $arg" >&2; exit 1 ;;
  esac
done

echo "=== news scheduled task インストール ==="

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

# 何をインストールするか
TASKS="daily-news"
[ "$WITH_SCOUT" = 1 ] && TASKS="$TASKS blog-idea-scout"

# シンボリックリンク（リポジトリを編集すれば即反映される）
echo ""
echo "--- シンボリックリンク ---"
mkdir -p "$TASKS_DIR"
for task in $TASKS; do
  mkdir -p "$TASKS_DIR/$task"
  ln -sf "$REPO_DIR/$task/SKILL.md" "$TASKS_DIR/$task/SKILL.md"
  echo "  $TASKS_DIR/$task/SKILL.md -> $REPO_DIR/$task/SKILL.md"
done
[ "$WITH_SCOUT" = 0 ] && echo "  （blog-idea-scout は未インストール。使うなら: ./install.sh --with-blog-idea-scout）"

# 設定ファイル（出力先などはここで変える。無ければ雛形をコピー）
echo ""
echo "--- 設定ファイル ---"
NEWS_CONFIG_DIR="$HOME/.config/news"
mkdir -p "$NEWS_CONFIG_DIR"
if [ ! -f "$NEWS_CONFIG_DIR/env" ]; then
  cp "$REPO_DIR/.env.example" "$NEWS_CONFIG_DIR/env"
  echo "  作成: $NEWS_CONFIG_DIR/env （出力先・カテゴリ等をここで編集）"
else
  echo "  既存: $NEWS_CONFIG_DIR/env （上書きしない）"
fi

echo ""
echo "=== 完了 ==="
echo "- daily-news: 1日2回（朝・夕）。実行時刻で朝刊/夕刊を出し分け。cron 例: 0 8,18 * * *"
[ "$WITH_SCOUT" = 1 ] && echo "- blog-idea-scout: 週1。ニュース蓄積からブログネタを提案。cron 例: 0 19 * * 0"
echo "設定は $NEWS_CONFIG_DIR/env を編集。Gmail 要対応メールを使うなら GMAIL_ENABLED=1 ＋ daily-news/gmail/SETUP.md。"
echo "リポジトリ側の SKILL.md を編集すると、そのまま反映されます。"
echo ""
echo "※ cron 登録自体はアプリの scheduled-task 機能で別途行う（このスクリプトは symlink のみ）。"
