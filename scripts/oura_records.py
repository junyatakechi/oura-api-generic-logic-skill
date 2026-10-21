"""oura-api-generic-logic-skill: Ouraのレスポンスから、対象日のレコードを正しく取り出す(値の変換だけ)。

通信はしない。`oura_api.fetch()` が返した {"data": [...]} を受け取り、Oura API側の事情
(日付の持ち方がエンドポイントで違う・境界日の取りこぼし・タグの2形式・睡眠区間の種別)を
吸収した値を返す。**どの列に書くかは持たない。** 列名への対応付けは呼び出し側(導入先の環境)が持つ。

ここにある判断と、その理由:
  - 境界日の取りこぼしと、対象日の取り出し方   → references/date-boundary.md
  - 心拍の時系列の扱い                        → references/heartrate.md
  - タグの2形式と、終了時刻の有無             → references/tags.md
  - 睡眠区間の種別と、日付のずれ              → references/sleep-periods.md
"""
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

# 対象期間の前後に足して取る日数(references/date-boundary.md)。
PADDING_DAYS = 1

# 夜間の主睡眠を表す睡眠区間の種別(references/sleep-periods.md)。
NIGHT_SLEEP_TYPE = "long_sleep"


# ---------------------------------------------------------------- 期間・日付

def padded_range(start, end):
    """対象期間(date か YYYY-MM-DD)を、取りこぼさない取得範囲(YYYY-MM-DDの組)にする。"""
    s = start if isinstance(start, date) else date.fromisoformat(start)
    e = end if isinstance(end, date) else date.fromisoformat(end)
    return ((s - timedelta(days=PADDING_DAYS)).isoformat(),
            (e + timedelta(days=PADDING_DAYS)).isoformat())


def day_of(record, endpoint_key):
    """そのレコードがOura上で何日に属するか(YYYY-MM-DD)。

    日付を持つ項目がエンドポイントで違う。enhanced_tag は start_day、
    heartrate は timestamp の先頭10文字、それ以外は day。
    """
    if endpoint_key == "enhanced_tag":
        return record.get("start_day")
    if endpoint_key == "heartrate":
        return (record.get("timestamp") or "")[:10] or None
    return record.get("day")


def records_on_day(response, endpoint_key, day):
    """レスポンスから、対象日に属するレコードだけを返す。"""
    return [r for r in (response or {}).get("data", []) if day_of(r, endpoint_key) == day]


def find_by_day(response, endpoint_key, day):
    """日次のエンドポイントから、対象日のレコードを1件返す。無ければ空のdict。"""
    found = records_on_day(response, endpoint_key, day)
    return found[0] if found else {}


def g(record, *path, default=None):
    """ネストしたdictから安全に値を取り出す。無ければdefaultを返す。"""
    node = record
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def jst_date(iso):
    """ISO日時の実日付(JST, YYYY-MM-DD)。解釈できなければNone。"""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).astimezone(JST).date().isoformat()
    except ValueError:
        return None


# ---------------------------------------------------------------- 心拍

def heart_rate_min_avg(heartrate_response, day):
    """heartrateの時系列から、対象日のbpmの最低と平均(小数1桁)を返す。無ければ(None, None)。"""
    bpms = [r["bpm"] for r in records_on_day(heartrate_response, "heartrate", day)
            if isinstance(r.get("bpm"), (int, float))]
    if not bpms:
        return None, None
    return min(bpms), round(sum(bpms) / len(bpms), 1)


# ---------------------------------------------------------------- タグ

def normalize_tag(record, kind):
    """タグの2形式を、共通の形にそろえる。kind は "enhanced_tag" か "tag"(旧)。

    戻り値: {"day", "start", "end", "codes", "content", "kind"}
      end は期間タグにだけ入る。瞬間タグと旧tagでは None(欠測ではなく仕様)。
    """
    if kind == "enhanced_tag":
        codes = [record["tag_type_code"]] if record.get("tag_type_code") else []
        return {
            "day": record.get("start_day"),
            "start": record.get("start_time"),
            "end": record.get("end_time"),
            "codes": codes,
            "content": record.get("comment") or record.get("custom_name") or "",
            "kind": kind,
        }
    return {
        "day": record.get("day"),
        "start": record.get("timestamp"),
        "end": None,  # 旧tagはtimestampのみで、終了に相当するフィールドを持たない
        "codes": record.get("tags") or [],
        "content": record.get("text") or "",
        "kind": kind,
    }


# ---------------------------------------------------------------- 睡眠区間

def is_night_sleep(sleep_record):
    """夜間の主睡眠(long_sleep)か。昼寝などは False。"""
    return sleep_record.get("type") == NIGHT_SLEEP_TYPE


def bedtime_day(sleep_record):
    """寝始めた実日付。Ouraの day は late_nap などを翌日にするので、日付で引く側はこちらを使う。"""
    return jst_date(sleep_record.get("bedtime_start")) or sleep_record.get("day")


def wake_day(sleep_record):
    """目覚めた実日付。「その日に目覚めた主睡眠」で引く側が使う。"""
    return jst_date(sleep_record.get("bedtime_end"))
