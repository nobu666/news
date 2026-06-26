# Gmail 要対応メール — セットアップ（初回だけ）

daily-news の朝刊に「要対応メール」セクションを足すための、Gmail 読み取り専用アクセスの初期設定。
スクリプトは標準ライブラリのみ（依存インストール不要）。認証情報は **このリポジトリの外**（`~/.config/news-gmail/`）に置く。

## 1. Google Cloud で OAuth クライアントを作る

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作る（既存でも可）
2. 「API とサービス」→「ライブラリ」→ **Gmail API** を有効化
3. 「OAuth 同意画面」を構成（User type: 外部、テストユーザーに自分の Gmail アドレスを追加でよい）
4. 「認証情報」→「認証情報を作成」→「OAuth クライアント ID」→ **アプリの種類: デスクトップ アプリ**
   - デスクトップアプリはループバック（`http://127.0.0.1`）へのリダイレクトが許可されるので、リダイレクト URI の登録は不要
5. 作成後、**クライアント ID** と **クライアント シークレット** を控える

## 2. 認証情報ファイルを置く

Console から**ダウンロードした OAuth クライアントの JSON をそのまま置いてよい**（`{"installed": {...}}` 形式に対応済み）:

```bash
mkdir -p ~/.config/news-gmail
mv ~/Downloads/client_secret_*.json ~/.config/news-gmail/credentials.json
chmod 600 ~/.config/news-gmail/credentials.json
```

または、client_id / client_secret だけを素の形で書いてもよい:

```bash
cat > ~/.config/news-gmail/credentials.json <<'JSON'
{ "client_id": "ここにクライアントID", "client_secret": "ここにシークレット" }
JSON
chmod 600 ~/.config/news-gmail/credentials.json
```

## 3. 一度だけ同意してトークンを発行

```bash
python3 ~/repos/news/daily-news/gmail/auth.py
```

ブラウザが開く → 自分の Gmail で同意 → `~/.config/news-gmail/token.json`（refresh_token 入り）が保存される。
以降はこの token で無人更新するので、再同意は不要（アクセス権を解除しない限り）。

## 4. 動作確認

```bash
python3 ~/repos/news/daily-news/gmail/fetch.py --check   # 認証ファイルの有無
python3 ~/repos/news/daily-news/gmail/fetch.py | head    # 実際に未読候補が JSON で出るか
```

## メモ

- スコープは `gmail.readonly`。既読化・返信・削除は一切しない（未読は未読のまま）。
- 取得は「差出人・件名・日付・スニペット（冒頭〜100字）・Gmailリンク」だけ。本文全体は取らない。
- 絞り込みは `fetch.py` の `QUERY`（既定 `is:unread -category:promotions -category:social newer_than:14d`）。
  環境変数 `GMAIL_QUERY` / `GMAIL_MAX` で上書き可。
- `credentials.json` と `token.json` は秘密。リポジトリには絶対に入れない（`~/.config/news-gmail/` に隔離済み）。
