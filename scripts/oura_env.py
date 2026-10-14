"""oura-api-generic-logic: Oura認証情報の .env 形式読み書き(標準ライブラリのみ)。

保存先は `$HOME/.claude-skills-env/oura-api-generic-logic.env`(KEY=VALUE形式)。
認証情報は導入先の環境なので、スキルの外に置く。別のファイルを一時的に使いたいときは、
環境変数 `OURA_ENV_FILE` にファイルの絶対パスを渡す(references/auth.md)。
"""
import os

DEFAULT_ENV_FILE = os.path.join(
    os.path.expanduser("~"), ".claude-skills-env", "oura-api-generic-logic.env"
)
DEFAULT_REDIRECT_URI = "http://localhost:8765/callback"

_KEYS = (
    "OURA_CLIENT_ID",
    "OURA_CLIENT_SECRET",
    "OURA_REDIRECT_URI",
    "OURA_ACCESS_TOKEN",
    "OURA_REFRESH_TOKEN",
    "OURA_EXPIRES_AT",
)


def env_path(path=None):
    """使う環境ファイルのパス。引数 → 環境変数 `OURA_ENV_FILE` → 既定の順で決める。"""
    return path or os.environ.get("OURA_ENV_FILE") or DEFAULT_ENV_FILE


def load(path=None):
    """.envファイルを読み込み、oura_auth/oura_api内部で使うキー名のdictを返す。"""
    path = env_path(path)
    values = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key in _KEYS:
                    values[key] = value.strip()
    return {
        "client_id": values.get("OURA_CLIENT_ID") or None,
        "client_secret": values.get("OURA_CLIENT_SECRET") or None,
        "redirect_uri": values.get("OURA_REDIRECT_URI") or DEFAULT_REDIRECT_URI,
        "access_token": values.get("OURA_ACCESS_TOKEN") or None,
        "refresh_token": values.get("OURA_REFRESH_TOKEN") or None,
        "expires_at": values.get("OURA_EXPIRES_AT") or None,
    }


def save(creds, path=None):
    """oura_auth/oura_api内部で使うキー名のdictを .env 形式で書き出す。"""
    path = env_path(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"OURA_CLIENT_ID={creds.get('client_id') or ''}",
        f"OURA_CLIENT_SECRET={creds.get('client_secret') or ''}",
        f"OURA_REDIRECT_URI={creds.get('redirect_uri') or DEFAULT_REDIRECT_URI}",
        f"OURA_ACCESS_TOKEN={creds.get('access_token') or ''}",
        f"OURA_REFRESH_TOKEN={creds.get('refresh_token') or ''}",
        f"OURA_EXPIRES_AT={creds.get('expires_at') or ''}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # 認証情報ファイルなので、作成できる環境では所有者のみ読み書きに絞る
    # (Windowsでは無視されるが、macOS/Ubuntuで流用したときに効く)。
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
