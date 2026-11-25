---
name: oura-api-generic-logic-skill
description: "文脈: Oura API。種類: 一般的な業務知識。使う場面: 名前で指名されたときだけ使い、会話の内容からは選ばない。"
metadata:
  skill-version: "0.3.7"
  design-name: "人の判断を切り出すAgent Skillsの設計"
  design-version: "6.0.1"
  design-url: "https://app.notion.com/p/3eaf2fd6925e8102b86fee3b6b3dd5a3"
---

# 索引

| 判断名 | 扱うこと | ファイル | 依存する判断 | 計算 |
|---|---|---|---|---|
| 認証とトークン | 認証情報を設定する・Ouraに接続するコードを書く・401が出たとき、トークンをどう更新し、どこに置き、401をどう読むか | [auth.md](references/auth.md) | — | — |
| APIの呼び方 | Ouraを読むコードを書く・404が出たとき、どの入口から呼び、何を呼び出し側で書かないか | [client-usage.md](references/client-usage.md) | `auth.md` | — |
| 心拍の取り方 | 心拍を取る・400が出たとき、範囲をどう指定し、日ごとにどう集計するか | [heartrate.md](references/heartrate.md) | — | — |
| 境界日の取りこぼし | 期間を指定して取るとき、どの範囲で取り、どう対象日のレコードを拾うか | [date-boundary.md](references/date-boundary.md) | — | — |
| 長大な時系列の要約 | 時系列を含むレコードを取るコードを書くとき、長大な時系列の配列を全件で取るか、どう要約するか | [raw-data.md](references/raw-data.md) | — | — |
| データが確定する時期 | 同期の対象日と時刻を決めるとき・項目が空だったとき、いつ取り、記録済みの日次をどうするか。空の項目をどう読むか | [data-latency.md](references/data-latency.md) | — | — |
| レコードの同一性 | 記録する処理を書くとき、何で重複を判定し、既にあったらどうするか | [record-identity.md](references/record-identity.md) | `data-latency.md` | — |
| タグの読み方 | タグを記録する・数えるとき、2つの形式と終了時刻の有無をどう読み、重複をどう除くか | [tags.md](references/tags.md) | `record-identity.md` | — |
| 睡眠区間と日次の睡眠の読み方 | 睡眠のデータを日付で引く・睡眠時間やHRVを集計するとき、昼寝の混ざり方・日付のずれ・スコアと時間の違いをどう読むか | [sleep-periods.md](references/sleep-periods.md) | `date-boundary.md` | — |
| 設定の不足 | 道具が `OuraAuthError` を返したとき、どの設定の不足によるものか | [missing-setup.md](references/missing-setup.md) | — | — |

# 手続きに使う道具

道具は `scripts/` にある。関数の一覧と引数は、各モジュールの冒頭の docstring が正。コードを書く前に読む。

| モジュール | 役割 |
|---|---|
| `oura_auth.py` | OAuth2のトークン管理。有効なトークンを返し、更新したら保存する |
| `oura_api.py` | API通信。ページ送り・心拍の分割・長大な配列の要約・エラー |
| `oura_records.py` | 取得範囲の算出・対象日のレコードの取り出し・心拍の集計・タグの形の統一・睡眠区間の日付（値の変換だけ） |
| `oura_env.py` | 認証情報の読み書き |

```python
import os, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "oura-api-generic-logic-skill", "scripts")))
from oura_auth import OuraAuthError, ensure_access_token
from oura_api import OuraError, fetch_many
import oura_records

start, end = oura_records.padded_range("2026-07-22", "2026-07-28")
data = fetch_many(["sleep", "daily_sleep"], ensure_access_token(), start, end)
```

## 例外

| 例外 | 意味 |
|---|---|
| `oura_api.OuraError` | 取得の基底。スクリプトはこれを捕まえる |
| `oura_api.OuraAPIError` | APIがエラーを返した。`.status` にHTTPステータス |
| `oura_auth.OuraAuthError` | 認証情報が無い / トークンの発行・更新を拒否された |

## シェルから起動するスクリプト

プロジェクトのフォルダから `<skill-dir>/scripts/...` の形で起動し、スキルのフォルダへ cd しない。`OURA_*` は環境変数、無ければ起動フォルダの `.env` から読み、トークンを更新したら `.env` の `OURA_*` の行だけを書き換える。トークンそのものは表示しない。

| スクリプト | 中身 |
|---|---|
| `uv run <skill-dir>/scripts/oura_auth.py init <client_id> <client_secret> [redirect_uri]` | 起動フォルダの `.env` に `OURA_*` の行を書く |
| `uv run <skill-dir>/scripts/oura_auth.py exchange <code>` | 認可コードをトークンに交換して保存する（初回だけ） |
| `uv run <skill-dir>/scripts/oura_auth.py ensure` | トークンが有効かを確かめ、有効期限を表示する |
| `uv run <skill-dir>/scripts/oura_api.py <endpoint> [start] [end] [--summarize]` | 1つのエンドポイントを取ってJSONで出す。`--summarize` で長大な時系列を要約する |

# このスキルの設計上の決まりごと

1. このスキルは判断を答えるだけで、判断の対象もデータも持たない。対象の値は、材料の写しとして受け取る。データを取りに行かず、保存もせず、IDも受け取らない。
2. 答える範囲は、聞きたい事を索引の「扱うこと」と照らして決める。索引の「依存する判断」にある判断を、先に出す。
3. 判断ファイルの「求める材料」がそろわなければ答えない。計算がある判断は、`uv run <skill-dir>/scripts/judge.py <判断> <材料.json>` で計算する。<判断> は `references/` のファイル名。依存する判断の材料も、一緒に渡す。
4. 答えは、指定された形にそろえ、理由と組にして返す。
5. 中核判断は、判断ファイルで答えられなければ、一般論で答えず「判断が無い」と返す。「未決」に当たったら、未決であることと、決めるまでの暫定の扱いを含める。一般的な業務知識は、判断ファイルに無いことを一般知識で補ってよい。
6. 読み込まれたら、索引の「扱うこと」に当たる作業で、その判断ファイルに従う。どの道具をどう呼ぶかは、判断ファイルの「道具」が示す。手続きは代わりに行わず、呼び出し側が道具を呼ぶ。操作する対象のIDは、材料ではなく、道具の引数で渡す。
