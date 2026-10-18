"""oura-api-generic-logic: Oura認証情報の .env 形式読み書き(標準ライブラリのみ)。

保存先は起動フォルダ(作業ディレクトリ)の `.env`(KEY=VALUE形式)。プロジェクトのスキルは
この1つを共有するので、書き込むときは OURA_* の行だけを書き換え、他の行はそのまま残す。
同じキーの環境変数があれば、読むときはそちらを優先する(references/auth.md)。
"""
import os

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
    """使う .env のパス。引数 → 起動フォルダの `.env` の順で決める。"""
    return path or os.path.join(os.getcwd(), ".env")


def _read(path):
    values = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    return values


def _write(path, updates):
    """`.env` のうち `updates` のキーの行だけを書き換え、無いキーは末尾に足す。

    `.env` は他のスキルの認証情報も持つので、他の行(値・コメント)は一切変えない。
    書きかけで落ちても元のファイルが壊れないよう、一時ファイルに書いてから置き換える。
    """
    lines = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    done = set()
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            key = s.split("=", 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}"
                done.add(key)
    rest = [f"{k}={v}" for k, v in updates.items() if k not in done]
    if rest:
        if lines and lines[-1].strip():
            lines.append("")
        lines += rest
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)
    # 認証情報ファイルなので、作成できる環境では所有者のみ読み書きに絞る
    # (Windowsでは無視されるが、macOS/Ubuntuで流用したときに効く)。
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load(path=None):
    """.env を読み、同じキーの環境変数で上書きして、oura_auth/oura_api内部で使うキー名のdictを返す。"""
    values = {k: v for k, v in _read(env_path(path)).items() if k in _KEYS}
    values.update({k: os.environ[k] for k in _KEYS if k in os.environ})
    return {
        "client_id": values.get("OURA_CLIENT_ID") or None,
        "client_secret": values.get("OURA_CLIENT_SECRET") or None,
        "redirect_uri": values.get("OURA_REDIRECT_URI") or DEFAULT_REDIRECT_URI,
        "access_token": values.get("OURA_ACCESS_TOKEN") or None,
        "refresh_token": values.get("OURA_REFRESH_TOKEN") or None,
        "expires_at": values.get("OURA_EXPIRES_AT") or None,
    }


def save(creds, path=None):
    """oura_auth/oura_api内部で使うキー名のdictを、.env の OURA_* の行に書き出す(初回セットアップ用)。"""
    _write(env_path(path), {
        "OURA_CLIENT_ID": creds.get("client_id") or "",
        "OURA_CLIENT_SECRET": creds.get("client_secret") or "",
        "OURA_REDIRECT_URI": creds.get("redirect_uri") or DEFAULT_REDIRECT_URI,
        "OURA_ACCESS_TOKEN": creds.get("access_token") or "",
        "OURA_REFRESH_TOKEN": creds.get("refresh_token") or "",
        "OURA_EXPIRES_AT": creds.get("expires_at") or "",
    })


def save_tokens(creds, path=None):
    """トークンの3行だけを書き換える。client_id・client_secret は読み書きせず現状のまま残す
    (環境変数で渡した値を .env に書き写さないため)。"""
    _write(env_path(path), {
        "OURA_ACCESS_TOKEN": creds.get("access_token") or "",
        "OURA_REFRESH_TOKEN": creds.get("refresh_token") or "",
        "OURA_EXPIRES_AT": creds.get("expires_at") or "",
    })
