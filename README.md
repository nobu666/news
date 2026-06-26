# news

毎日のニュースを Web 検索で収集して日本語要約にまとめ、朝刊では任意で Gmail の未読から「対応が必要そうなもの」を拾う Claude Code の scheduled task 一式。

**個人設定（出力先・カテゴリ・天気・ブログの性格など）はすべて `~/.config/news/env`（`.env` 形式・リポジトリ外）に置く。** クローンした人は自分の env を書くだけで使える。タスク本体（`SKILL.md`）には個人情報を書かない設計。

## 構成

**既定では「ニュース収集」だけが動く。** Gmail 要対応メールと blog-idea-scout は、明示的に有効化したときだけ動く任意の追加機能。

| タスク | 区分 | 頻度 | 内容 | 出力 |
|---|---|---|---|---|
| [`daily-news`](daily-news/SKILL.md) | コア | 1日2回（朝・夕） | 設定カテゴリのニュース収集 | `$NEWS_DIR/YYYY-MM-DD-{morning,evening}.md` |
| └ Gmail 要対応メール | 任意 | 朝刊のみ | `GMAIL_ENABLED=1` のとき未読から要対応を抽出 | 朝刊内のセクション |
| [`blog-idea-scout`](blog-idea-scout/SKILL.md) | 任意 | 週1 | ニュース蓄積×自分のメモからブログネタ提案 | `$BLOG_IDEA_FILE` |

daily-news は**実行時刻で朝刊/夕刊を出し分ける**（12時より前なら朝刊、以降なら夕刊）。cron は `0 8,18 * * *` のように1タスクで朝夕2回発火させる。

## クイックスタート

```bash
git clone https://github.com/nobu666/news.git ~/repos/news
cd ~/repos/news
./install.sh                 # daily-news（ニュース）だけを symlink ＋ ~/.config/news/env を雛形から作成
$EDITOR ~/.config/news/env   # 自分用に編集（下表）
```

これだけでニュース収集が動く。追加機能は任意:
- **blog-idea-scout も使う**: `./install.sh --with-blog-idea-scout`
- **Gmail 要対応メールも使う**: `~/.config/news/env` で `GMAIL_ENABLED=1` ＋ [`daily-news/gmail/SETUP.md`](daily-news/gmail/SETUP.md)

`install.sh` がやること:
- `daily-news`（と `--with-blog-idea-scout` 指定時は blog-idea-scout）の `SKILL.md` を `~/.claude/scheduled-tasks/<task>/SKILL.md` に **symlink**（リポを編集すれば次回実行に即反映）
- `~/.config/news/env` が無ければ [`.env.example`](.env.example) からコピー

cron 登録自体はアプリの scheduled-task 機能で別途行う（install.sh は symlink と設定雛形のみ）。

## 設定（`~/.config/news/env`）

`.env` 形式・**リポジトリ外**。無いキーは既定値。パス先頭の `~` はホームに展開。

| キー | 用途 |
|---|---|
| `NEWS_DIR` | daily-news の出力先（blog-idea-scout の入力でもある） |
| `BLOG_IDEA_FILE` | blog-idea-scout の提案出力先 |
| `BACKLOG_FILE` | （任意）既存ネタ在庫。あれば重複判定に使う |
| `VAULT_SEARCH` | （任意）過去メモ検索コマンドのパス。あれば関連メモ掘りに使う |
| `WEATHER_LOCATION` | 天気の対象地域。空なら天気セクション省略 |
| `NEWS_CATEGORIES` | 収集カテゴリ。`;` 区切り、各項目 `名前: 補足` 可 |
| `NEWS_SOURCES` | （任意）優先ソース。`;` 区切り。空ならエージェントが選ぶ |
| `BLOG_PROFILE` | ブログの性格と「良いネタ」の判断基準を一言で |
| `GMAIL_ENABLED` | `1` で朝刊の要対応メールを有効化（既定 `0`） |
| `GMAIL_QUERY` / `GMAIL_MAX` | 要対応メール抽出の Gmail 検索クエリ・最大件数 |

## Gmail 要対応メール（任意）

`GMAIL_ENABLED=1` のとき、朝刊で未読から「返信・対応・期限がありそうなもの」を拾う。**読み取り専用**（`gmail.readonly`）で、既読化も返信もしない。差出人・件名・スニペットだけを見て本文全体は取らない。

セットアップは [`daily-news/gmail/SETUP.md`](daily-news/gmail/SETUP.md) 参照（Gmail API の OAuth クライアント作成 → 一度だけ同意 → トークン保存）。認証情報は `~/.config/news-gmail/` に置き、**このリポジトリには絶対に入れない**。

無人実行で `fetch.py` を権限ダイアログ無しに走らせるには、`~/.claude/settings.json` の `permissions.allow` に次を加える（クローン先が違えばパスを読み替え）:

```
"Bash(python3 ~/repos/news/daily-news/gmail/fetch.py)"
```

## セキュリティ上の注意

- **scheduled task は無人で自律実行される。** `install.sh` の `git pull` で上流が変わると、無人エージェントの指示（SKILL.md）もそのまま変わる。**pull 後は SKILL.md の差分を、無人実行前に確認する**こと。
- ニュースやメールは**攻撃者が中身を選べる untrusted データ**として扱う設計（各 SKILL.md 冒頭の「取り扱い注意」参照）。本文中の命令や URL 誘導には従わせない。
- 秘密情報（Gmail 認証情報・トークン）は `~/.config/` 配下に隔離し、リポジトリには置かない。`.gitignore` でも二重に弾く。

## 編集方針

- 個人の値は `~/.config/news/env` に。`SKILL.md` には個人情報・固有のパスを書かない
- リンクは実在する**個別記事の URL**を貼る（月次インデックスやニュース一覧ページは不可）

## ライセンス

[MIT](LICENSE)
