#!/usr/bin/env python3
"""一度だけ実行: ブラウザで Gmail 読み取り専用の同意を取り、token.json を保存する。

依存なし。事前に GMAIL_CONFIG_DIR（既定 ~/.config/news-gmail）に
credentials.json {"client_id": "...", "client_secret": "..."} を置いておくこと。
OAuth クライアントは Google Cloud Console で「デスクトップ アプリ」種別で作る
（ループバック http://127.0.0.1 へのリダイレクトが許可されるため登録不要）。
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.request
import urllib.parse
import webbrowser
import http.server
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("GMAIL_CONFIG_DIR", Path.home() / ".config" / "news-gmail"))
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}"

_received = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _received["code"] = params.get("code", [None])[0]
        _received["state"] = params.get("state", [None])[0]
        _received["error"] = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("認証が完了しました。ターミナルに戻ってください。".encode())

    def log_message(self, *a):  # サーバログを黙らせる
        pass


def _harden_perms():
    """秘密ディレクトリ/ファイルのパーミッションを防御的に絞る（冪等）。"""
    try:
        CONFIG_DIR.chmod(0o700)
        for f in ("credentials.json", "token.json"):
            p = CONFIG_DIR / f
            if p.exists():
                p.chmod(0o600)
    except OSError:
        pass


def load_creds():
    _harden_perms()
    raw = json.loads((CONFIG_DIR / "credentials.json").read_text())
    c = raw.get("installed") or raw.get("web") or raw  # Google DL形式({"installed":..})と素の形式の両対応
    return {"client_id": c["client_id"], "client_secret": c["client_secret"]}


def main():
    creds = load_creds()
    # PKCE（S256）と state で認可コード注入/CSRF を防ぐ
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    url = f"{AUTH_URL}?{params}"
    httpd = http.server.HTTPServer(("127.0.0.1", PORT), _Handler)
    httpd.timeout = 180  # リダイレクトが来なければ諦める（ハング防止）
    print("ブラウザで同意してください。開かない場合は次のURLを手動で開く:\n" + url + "\n")
    webbrowser.open(url)
    httpd.handle_request()  # リダイレクト1回だけ受ける

    if _received.get("error"):
        print(f"認証エラー: {_received['error']}", file=sys.stderr)
        sys.exit(1)
    if _received.get("state") != state:
        print("state 不一致。認可コード注入の疑いがあるため中止します。", file=sys.stderr)
        sys.exit(1)
    code = _received.get("code")
    if not code:
        print("認証コードを取得できませんでした（タイムアウトの可能性）。", file=sys.stderr)
        sys.exit(1)

    body = urllib.parse.urlencode({
        "code": code,
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)

    if "refresh_token" not in tok:
        print("refresh_token が返りませんでした。Google アカウントのアクセス権を一度解除してから再実行してください。", file=sys.stderr)
        sys.exit(1)

    out = CONFIG_DIR / "token.json"
    out.write_text(json.dumps(tok, ensure_ascii=False, indent=2))
    out.chmod(0o600)
    print(f"保存しました: {out}")


if __name__ == "__main__":
    main()
