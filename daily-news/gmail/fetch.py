#!/usr/bin/env python3
"""Gmail の未読から「要対応かもしれない」候補を JSON で出す（読み取り専用）。

依存なし（標準ライブラリのみ）。認証情報は GMAIL_CONFIG_DIR（既定 ~/.config/news-gmail）に置く:
  credentials.json : {"client_id": "...", "client_secret": "..."}   ← 手動で作成
  token.json       : auth.py が生成（refresh_token を含む）

出力: stdout に [{from, subject, date, snippet, link}] の JSON 配列。
      取得に失敗したら {"error": "..."} を出して exit 1（呼び出し側は本文を続行できる）。
スコープは gmail.readonly。既読化も削除もしない。
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path


def _load_env_file():
    """~/.config/news/env (.env形式) を環境変数の不足分に流す（既存のenvが優先）。"""
    p = Path(os.environ.get("NEWS_ENV", Path.home() / ".config" / "news" / "env")).expanduser()
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env_file()

CONFIG_DIR = Path(
    os.environ.get("GMAIL_CONFIG_DIR", str(Path.home() / ".config" / "news-gmail"))
).expanduser()
# 要対応になりうる未読だけに絞る。プロモ/SNSは除外。
# ノイズが多ければ -category:updates を足す。取りこぼすなら newer_than を伸ばす。
QUERY = os.environ.get("GMAIL_QUERY", "is:unread -category:promotions -category:social newer_than:14d")
MAX_RESULTS = int(os.environ.get("GMAIL_MAX", "40"))
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


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


def access_token():
    creds = load_creds()
    tok = json.loads((CONFIG_DIR / "token.json").read_text())
    resp = _post(TOKEN_URL, {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    })
    return resp["access_token"]


def fetch():
    token = access_token()
    q = urllib.parse.urlencode({"q": QUERY, "maxResults": MAX_RESULTS})
    listing = _get(f"{API}?{q}", token)
    out = []
    for m in listing.get("messages", []):
        meta = urllib.parse.urlencode(
            {"format": "metadata"},
        ) + "&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
        msg = _get(f"{API}/{m['id']}?{meta}", token)
        h = {x["name"].lower(): x["value"] for x in msg.get("payload", {}).get("headers", [])}
        out.append({
            "from": h.get("from", ""),
            "subject": h.get("subject", "(件名なし)"),
            "date": h.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "link": f"https://mail.google.com/mail/u/0/#all/{m['id']}",
        })
    return out


def main():
    if "--check" in sys.argv:
        ok = (CONFIG_DIR / "credentials.json").exists() and (CONFIG_DIR / "token.json").exists()
        print("OK" if ok else f"FAIL: 認証ファイルが無い ({CONFIG_DIR})")
        sys.exit(0 if ok else 1)
    if os.environ.get("GMAIL_ENABLED", "0").strip().lower() not in ("1", "true", "yes", "on"):
        print("[]")  # 機能オフ（既定）。使うなら ~/.config/news/env で GMAIL_ENABLED=1
        return
    try:
        json.dump(fetch(), sys.stdout, ensure_ascii=False, indent=2)
        print()
    except Exception as e:  # noqa: BLE001 — 無人実行: クラッシュさせず error を返す
        # 例外文字列にURL等が混じりうるので stdout には種別名だけ（Vaultに書かれる前提で最小化）。詳細は stderr。
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        json.dump({"error": type(e).__name__}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
