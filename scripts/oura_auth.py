#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""oura-api-generic-logic: Oura API v2 OAuth2 認証(標準ライブラリのみ使用)。

他スクリプトからは `ensure_access_token()` をimportして使う(references/auth.md)。

使い方:
  uv run scripts/oura_auth.py init <client_id> <client_secret> [redirect_uri]
  uv run scripts/oura_auth.py exchange <code>
  uv run scripts/oura_auth.py refresh
  uv run scripts/oura_auth.py ensure

  init:     初回セットアップ。環境ファイルを新規作成する。
  exchange: 認可コード(code)をアクセストークン・リフレッシュトークンに交換して保存する(初回のみ)。
  refresh:  refresh_tokenでaccess_tokenを更新して保存する(refresh_tokenは使い捨てのため
            新しい値で必ず上書きされる)。
  ensure:   expires_atを見て、期限切れ/5分以内に迫っていれば自動でrefreshし、
            有効期限を表示する。**トークンそのものは表示しない。**

環境ファイルは $HOME/.claude-skills-env/oura-api-generic-logic.env。
別のファイルを使うときは環境変数 OURA_ENV_FILE に絶対パスを渡す。
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oura_env import DEFAULT_REDIRECT_URI, env_path, load, save  # noqa: E402

TOKEN_URL = "https://api.ouraring.com/oauth/token"
JST = timezone(timedelta(hours=9))

# 期限のこれだけ前から更新する(分)。
REFRESH_MARGIN_MIN = 5


class OuraAuthError(RuntimeError):
    """認証情報が無い、またはトークンの発行・更新をOuraが拒否した。"""


def _post_token(payload):
    body = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OuraAuthError(f"Oura token endpoint error {e.code}: {e.read().decode('utf-8')}") from None


def cmd_init(path, client_id, client_secret, redirect_uri):
    creds = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri or DEFAULT_REDIRECT_URI,
        "access_token": None,
        "refresh_token": None,
        "expires_at": None,
    }
    save(creds, path)
    print(f"initialized: {path}")


def _apply_token_response(creds, token_resp):
    creds["access_token"] = token_resp["access_token"]
    creds["refresh_token"] = token_resp["refresh_token"]  # 使い捨てのため必ず新しい値で上書き
    expires_in = int(token_resp.get("expires_in", 0))
    creds["expires_at"] = (datetime.now(JST) + timedelta(seconds=expires_in)).isoformat()


def cmd_exchange(path, code):
    creds = load(path)
    if not creds.get("client_id") or not creds.get("client_secret"):
        raise OuraAuthError("client_id/client_secret is missing. run 'init' first.")
    token_resp = _post_token({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": creds["redirect_uri"],
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
    })
    _apply_token_response(creds, token_resp)
    save(creds, path)
    print("access_token acquired. expires_at =", creds["expires_at"])


def refresh(path=None):
    """refresh_tokenでaccess_tokenを更新し、新しいrefresh_tokenごと保存する。"""
    path = env_path(path)
    creds = load(path)
    if not creds.get("refresh_token"):
        raise OuraAuthError("refresh_token is missing. run 'exchange' first.")
    token_resp = _post_token({
        "grant_type": "refresh_token",
        "refresh_token": creds["refresh_token"],
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
    })
    _apply_token_response(creds, token_resp)
    save(creds, path)
    return creds


def ensure_access_token(path=None):
    """他スクリプトからimportして呼ぶ用。有効なaccess_tokenを返す(必要ならrefreshする)。"""
    path = env_path(path)
    creds = load(path)
    expires_at = creds.get("expires_at")
    needs_refresh = True
    if expires_at and creds.get("access_token"):
        try:
            exp = datetime.fromisoformat(expires_at)
            needs_refresh = datetime.now(JST) >= exp - timedelta(minutes=REFRESH_MARGIN_MIN)
        except ValueError:
            needs_refresh = True
    if needs_refresh:
        creds = refresh(path)
    return creds["access_token"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    path = env_path()

    if cmd == "init":
        if len(rest) < 2:
            raise SystemExit("usage: init <client_id> <client_secret> [redirect_uri]")
        cmd_init(path, rest[0], rest[1], rest[2] if len(rest) > 2 else None)
    elif cmd == "exchange":
        if len(rest) < 1:
            raise SystemExit("usage: exchange <code>")
        cmd_exchange(path, rest[0])
    elif cmd == "refresh":
        print("refreshed. expires_at =", refresh(path)["expires_at"])
    elif cmd == "ensure":
        ensure_access_token(path)
        print("access_token is valid. expires_at =", load(path)["expires_at"])
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    try:
        main()
    except OuraAuthError as e:
        sys.exit(f"Error: {e}")
