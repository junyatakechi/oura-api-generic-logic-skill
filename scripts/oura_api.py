#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""oura-api-generic-logic-skill: Oura API v2 usercollection の取得(標準ライブラリのみ使用)。

このモジュールは**他スキルから直接importして使う公開モジュール**(references/client-usage.md)。

    from oura_auth import ensure_access_token
    from oura_api import OuraError, fetch, fetch_many
    data = fetch("sleep", ensure_access_token(), "2026-07-21", "2026-07-23")

シェルからの単発の確認:
  uv run scripts/oura_api.py <endpoint> [start_date] [end_date] [--summarize]

  endpoint: daily_sleep / daily_activity / daily_readiness / daily_resilience /
            daily_cardiovascular_age / daily_spo2 / daily_stress / vo2max /
            sleep / sleep_time / heartrate / session / workout / enhanced_tag /
            tag / rest_mode_period / ring_configuration / personal_info
  start_date/end_date: YYYY-MM-DD (省略時はstart_date=前日, end_date=当日)
  --summarize: 心拍・睡眠段階等の長大な時系列配列を、件数と先頭の数件に要約して出力する

このモジュールが引き受けるもの(呼び出し側で再実装しないこと):
  - next_token のページ送り
  - heartrate だけ日時で範囲を指定し、29日以内に分割して結合する(references/heartrate.md)
  - 長大な時系列配列の要約。full=False を渡したときだけ行う(references/raw-data.md)
アクセストークンの更新はしない。`oura_auth.ensure_access_token()` で取ったものを渡す。

ここにある定数(エンドポイントのパス・範囲の上限)は、どれもOura APIという共有する環境の
仕様で、人が決めた値ではない。要約の閾値だけは作成者が決めた値で、理由は references/raw-data.md。
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API_URL = "https://api.ouraring.com/v2/usercollection"
REQUEST_TIMEOUT_SEC = 30

# キー: このモジュールで使う名前 / 値: 実際のAPIパス
# (vO2_max等、大文字小文字が特殊なものがあるため、404になる場合は
#  https://cloud.ouraring.com/v2/docs で正式なパス名を確認すること)
ENDPOINTS = {
    "daily_sleep": "daily_sleep",
    "daily_activity": "daily_activity",
    "daily_readiness": "daily_readiness",
    "daily_resilience": "daily_resilience",
    "daily_cardiovascular_age": "daily_cardiovascular_age",
    "daily_spo2": "daily_spo2",
    "daily_stress": "daily_stress",
    "vo2max": "vO2_max",
    "sleep": "sleep",
    "sleep_time": "sleep_time",
    "heartrate": "heartrate",
    "session": "session",
    "workout": "workout",
    "enhanced_tag": "enhanced_tag",
    "tag": "tag",
    "rest_mode_period": "rest_mode_period",
    "ring_configuration": "ring_configuration",
    "personal_info": "personal_info",
}

# 日付範囲を取らないエンドポイント(単一オブジェクト or 設定情報)
NO_DATE_RANGE = {"personal_info", "ring_configuration"}

# 他のusercollectionエンドポイントは start_date/end_date (日付のみ)だが、
# heartrateだけは start_datetime/end_datetime (日時)でないと範囲指定が無視され、
# 常に直近のレコードだけが返ってくる(実機検証済み)。
DATETIME_RANGE = {"heartrate"}

# heartrateは「start〜endが30日以内」でないと400エラーになる(実機検証済み)。
# この日数を超える場合はfetch()が自動的に分割して複数回リクエストし、結果を結合する。
MAX_RANGE_DAYS = {"heartrate": 29}

# 長大な時系列配列を持つフィールド。full=Falseを渡されたら要約する(references/raw-data.md)。
LONG_ARRAY_FIELDS = [
    ("class_5_min",),
    ("movement_30_sec",),
    ("sleep_phase_5_min",),
    ("met", "items"),
    ("heart_rate", "items"),
    ("hrv", "items"),
]
# 要約の閾値(作成者が決めた値。references/raw-data.md)
SUMMARIZE_STR_CHARS = 200
SUMMARIZE_LIST_ITEMS = 20
SUMMARY_HEAD_ITEMS = 5


class OuraError(RuntimeError):
    """このモジュールが送出する例外の基底。スクリプトはこれを捕まえて exit する。"""


class OuraAPIError(OuraError):
    """Oura APIがエラーを返した。`status` にHTTPステータスが入る。"""

    def __init__(self, status, url, detail):
        super().__init__(f"Oura API error {status} ({url}): {detail}")
        self.status = status
        self.url = url


def _summarize_long_arrays(record):
    if not isinstance(record, dict):
        return record
    record = json.loads(json.dumps(record))  # 入れ子まで複製し、呼び出し側の値を壊さない
    for path in LONG_ARRAY_FIELDS:
        node = record
        ok = True
        for key in path[:-1]:
            if not isinstance(node, dict) or key not in node:
                ok = False
                break
            node = node[key]
        if not ok or not isinstance(node, dict):
            continue
        last_key = path[-1]
        value = node.get(last_key)
        if isinstance(value, str) and len(value) > SUMMARIZE_STR_CHARS:
            node[last_key] = f"<{len(value)}文字を省略。full=Trueで全体取得可能>"
        elif isinstance(value, list) and len(value) > SUMMARIZE_LIST_ITEMS:
            node[last_key] = {
                "件数": len(value),
                f"先頭{SUMMARY_HEAD_ITEMS}件": value[:SUMMARY_HEAD_ITEMS],
                "備考": "full=Trueで全件取得可能",
            }
    return record


def _fetch_page(url, access_token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OuraAPIError(e.code, url, e.read().decode("utf-8", errors="replace")) from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise OuraError(f"Oura API に接続できない ({url}): {e}") from None


def fetch(endpoint_key, access_token, start_date=None, end_date=None, full=True):
    """指定エンドポイントのレコードを取得する。戻り値は {"data": [...], ...}。

    MAX_RANGE_DAYS に該当するエンドポイント(heartrate)は、指定範囲が上限日数を
    超える場合、上限日数以内のチャンクに自動分割して複数回リクエストし、結果を結合する。
    """
    if endpoint_key not in ENDPOINTS:
        raise OuraError(f"unknown endpoint: {endpoint_key}. choices: {', '.join(ENDPOINTS)}")
    max_days = MAX_RANGE_DAYS.get(endpoint_key)
    if max_days and start_date and end_date:
        chunks = list(_split_date_range(start_date, end_date, max_days))
        if len(chunks) > 1:
            merged = []
            last = None
            for chunk_start, chunk_end in chunks:
                part = _fetch_single_range(endpoint_key, access_token, chunk_start, chunk_end, full=True)
                last = part
                merged.extend(part.get("data", []))
            result = dict(last or {"data": []})
            result["data"] = merged
            if not full:
                result["data"] = [_summarize_long_arrays(r) for r in result["data"]]
            return result

    return _fetch_single_range(endpoint_key, access_token, start_date, end_date, full=full)


def fetch_many(endpoint_keys, access_token, start_date, end_date, full=True, on_error=None):
    """複数エンドポイントをまとめて取得する。{endpoint_key: response} を返す。

    1つのエンドポイントの失敗で全体を止めるかは呼び出し側が選ぶ。`on_error` を渡すと、
    失敗したエンドポイントは `on_error(key, exc)` を呼んで {"data": []} 扱いにする。
    渡さなければ例外をそのまま上げる。
    """
    out = {}
    for key in endpoint_keys:
        try:
            out[key] = fetch(key, access_token, start_date, end_date, full=full)
        except OuraError as e:
            if on_error is None:
                raise
            on_error(key, e)
            out[key] = {"data": []}
    return out


def _split_date_range(start_date, end_date, max_days):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=max_days - 1), end)
        yield cur.isoformat(), chunk_end.isoformat()
        cur = chunk_end + timedelta(days=1)


def _fetch_single_range(endpoint_key, access_token, start_date=None, end_date=None, full=True):
    """指定エンドポイントを1回の範囲リクエスト(next_tokenでのページ送りは含む)で取得する。"""
    path = ENDPOINTS[endpoint_key]
    url = f"{API_URL}/{path}"
    base_params = {}
    if endpoint_key in DATETIME_RANGE:
        if start_date:
            base_params["start_datetime"] = f"{start_date}T00:00:00"
        if end_date:
            base_params["end_datetime"] = f"{end_date}T23:59:59"
    elif endpoint_key not in NO_DATE_RANGE:
        if start_date:
            base_params["start_date"] = start_date
        if end_date:
            base_params["end_date"] = end_date

    all_records = []
    next_token = None
    last_data = None
    while True:
        params = dict(base_params)
        if next_token:
            params["next_token"] = next_token
        page_url = url + ("?" + urllib.parse.urlencode(params) if params else "")
        data = _fetch_page(page_url, access_token)
        last_data = data
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            # personal_info / ring_configuration 等、data配列を持たない単一オブジェクト応答
            return data
        all_records.extend(data["data"])
        next_token = data.get("next_token")
        if not next_token:
            break

    result = dict(last_data)
    result["data"] = all_records
    if not full:
        result["data"] = [_summarize_long_arrays(r) for r in result["data"]]
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from oura_auth import OuraAuthError, ensure_access_token

    full = "--summarize" not in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--summarize"]
    if len(args) < 1:
        print(__doc__)
        raise SystemExit(1)
    endpoint_key = args[0]
    today = date.today()
    start_date = args[1] if len(args) > 1 else (today - timedelta(days=1)).isoformat()
    end_date = args[2] if len(args) > 2 else today.isoformat()
    try:
        result = fetch(endpoint_key, ensure_access_token(), start_date, end_date, full=full)
    except (OuraError, OuraAuthError) as e:
        sys.exit(f"Error: {e}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
