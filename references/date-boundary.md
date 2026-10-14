# 境界日の取りこぼし

## 求める材料

| 材料 | 種類 | 必須 | 形 | 無いとき |
|---|---|---|---|---|
| 取りたい期間（開始日・終了日） | 対象の属性 | ○ | YYYY-MM-DD | 判断できない |

## 答え

1. **対象期間ちょうど（`start_date == end_date == 対象日` など）で問い合わせない。** 前後1日を足した範囲で取る。
2. **取ったあと、レコードの日付が対象日と一致するものだけを拾う。** 余分に取れても、拾う段階で落ちるので実害はない。
3. **レコードの日付の項目はエンドポイントで違う。** `enhanced_tag` は `start_day`、`heartrate` は `timestamp` の先頭10文字、それ以外は `day`。

## 道具

- 答え1は `oura_records.padded_range(start, end)`。取得範囲の組を返す。
- 答え2・3は `oura_records.records_on_day(response, endpoint_key, day)` と `find_by_day(...)`。日付の項目の違いを吸収する。

## 値

作成者が決めた値。`oura_records.PADDING_DAYS` の定数が正（多くのスキルがimportする道具なので、表を読まない）。

| 名前 | 値 | 単位 |
|---|---|---|
| 前後に足す日数 | 1 | 日 |

## 理由

1. 実機で、`start_date == end_date == 対象日` で問い合わせると、`daily_activity`・`vo2max`・`sleep_time`・`sleep`・`session`・`workout`・`enhanced_tag`・`tag` が対象日のレコードを返さないことがあった。
- 足す日数を1日にした理由は、記録が無い（1日で取りこぼしが止まった、という以上の検証は残っていない）。

## 却下した案

記録なし。

## 当てはまる範囲と限界

- 睡眠区間の `day` は、Ouraがつけた日付で、寝始めた日とは限らない。日付で引くときの扱いは [睡眠区間の読み方](sleep-periods.md)。
