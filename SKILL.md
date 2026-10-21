---
name: oura-api-generic-logic-skill
description: "文脈: Oura API。種類: 一般的な業務領域の判断。使う場面: この文脈の判断を直接聞かれたときに使う。この文脈の作業の前に読み、索引の「いつ聞くか」に当たる判断を聞く。"
metadata:
  version: "0.3.0"
  repository: "https://github.com/junyatakechi/oura-api-generic-logic-skill"
---

# Oura API の一般的な判断

## このスキルの役割

**Oura API v2 を扱うときの、一般的な判断を持つ generic-logic スキル。** Ouraを使う人なら誰でも同じ答えになるが、AIの一般知識にはまだ無い判断を持つ。どれも、実機で確かめたか、実際に踏んで見つけたもの。

| | このスキル |
|---|---|
| 依存してよい環境 | 誰もが共有する環境だけ（Oura API v2 `api.ouraring.com`） |
| 持たないもの | 判断の対象（Ouraのレコード）と、導入先の環境。認証情報はプロジェクトのフォルダ直下の `.env` に置き、どこに記録するか・列名は呼び出し側が持つ |
| 持つ道具 | 手続きに使う道具だけ（APIとの通信と、値の変換）。判断に使う道具は持たない |
| 共有するとき | 混ぜて1つに育てる。新しく踏んだ落とし穴（エンドポイントの癖・項目の意味）は、判断として足していく |

取得する側（同期）と、記録されたデータを読む側（評価）の両方から聞かれる。睡眠区間・タグ・日次の睡眠の読み方は、読む側のための判断。

## 聞かれ方

他のスキルから聞かれるときは、ロジックスキル共通のやり取りで進める。

| 順 | 向き | 渡すもの |
|---|---|---|
| 1 | 呼び出し側 → このスキル | 聞きたい事・判断先（判断ファイルのパス）・欲しい答えの形 |
| 2 | このスキル → 呼び出し側 | 判断に要る材料の要求（各判断の「求める材料」） |
| 3 | 呼び出し側 → このスキル | 集めた材料 |
| 4 | このスキル → 呼び出し側 | 指定された形の答えと、その理由。手続きに関わる判断では、道具の使い方（どの道具を、どう呼び、何を守るか）も含める |

- 答えと理由を、組にして返す。
- 必須の材料が無ければ、答えずに足りない材料を返す。必須でない材料が無ければ、何が無かったために何を言えなかったかを添えて答える。
- 判断ファイルで答えられない聞きたい事には、一般論で答えず「判断が無い」と返す。新しい落とし穴を踏んだら、判断として足す。
- 判断のファイルに「未決」とある箇所に当たったら、未決であることを答えに含める。
- **このスキルの答えには、道具の使い方を含めることが多い。** 索引の「いつ聞くか」に当たったら、呼び出し側は聞きたい事・判断先・欲しい答えの形を伝えて聞き、返ってきた使い方に従って道具を自分で呼ぶ。
- **このスキルは判断して答えるだけで、手続きは代わりに行わない。** 手続きに使う道具は、呼び出し側が `scripts/` から自分で呼び、手続きの結果か例外を受け取る。
- 認証の設定・疎通の確認・単発の取得は、ユーザーから直接頼まれることもある（[認証とトークン](references/auth.md)・[APIの呼び方](references/client-usage.md)）。

## 道具

道具は `scripts/` にある。どれも手続きに使う道具で、呼び出し側が手続きの中で使う。`oura_auth.py`・`oura_api.py`・`oura_env.py` はスキルの外を読み書きし（Ouraとの通信・`.env`）、`oura_records.py` は値の変換だけをする。どれも標準ライブラリだけで動く。**Pythonから使うなら常にimport、シェルからならスクリプトを起動する**（理由は [client-usage.md](references/client-usage.md)）。

- **呼び出し側は道具を写さず、自前の薄いラッパーも持たない。** トークンの入口は `oura_auth.ensure_access_token()`、取得の入口は `oura_api.fetch()` / `fetch_many()` に1つずつ置く。
- **道具で強制できる判断は、道具の中に実装してある。** トークンの更新と保存・ページ送り・心拍の分割・長大な配列の要約・日付の項目の違いの吸収で、理由は判断ファイルに書いてある。強制できない判断（日次は上書き・区間は record id で重複を防ぐ、など）は、このスキルが答えとして伝え、呼び出し側が守る。
- 失敗は例外で返す。続けるか止めるかは、呼び出し側が選ぶ。

```python
import os, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "oura-api-generic-logic-skill", "scripts")))
from oura_auth import OuraAuthError, ensure_access_token
from oura_api import OuraError, fetch_many
import oura_records

start, end = oura_records.padded_range("2026-07-22", "2026-07-28")
data = fetch_many(["sleep", "daily_sleep"], ensure_access_token(), start, end)
nights = [r for r in oura_records.records_on_day(data["sleep"], "sleep", "2026-07-23")
          if oura_records.is_night_sleep(r)]
```

| モジュール             | 役割                                                |
| ----------------- | ------------------------------------------------- |
| `oura_auth.py`    | OAuth2のトークン管理。`ensure_access_token()` が有効なトークンを返す |
| `oura_api.py`     | API通信。ページ送り・心拍の分割・長大な配列の要約・エラー                    |
| `oura_records.py` | 取得範囲の算出・対象日のレコードの取り出し・心拍の集計・タグの形の統一・睡眠区間の日付       |
| `oura_env.py`     | 認証情報の読み書き                                         |

### 関数

| 関数 | 中身 |
|---|---|
| `oura_auth.ensure_access_token(path=None)` | 有効な access_token。期限の5分前を過ぎていれば更新し、新しい refresh_token ごと保存する |
| `oura_api.fetch(endpoint, token, start, end, full=True)` | 1つのエンドポイントを取る。`{"data": [...]}`。`full=False` で長大な時系列を要約する |
| `oura_api.fetch_many(endpoints, token, start, end, full=True, on_error=None)` | 複数をまとめて取る。`on_error` を渡すと、失敗したものを空にして続ける |
| `oura_records.padded_range(start, end)` | 境界日を取りこぼさない取得範囲 |
| `oura_records.records_on_day(response, endpoint, day)` / `find_by_day(...)` | 対象日のレコード（全件 / 1件） |
| `oura_records.heart_rate_min_avg(response, day)` | 対象日の心拍の最低と平均 |
| `oura_records.normalize_tag(record, kind)` | タグの2形式を共通の形にする |
| `oura_records.is_night_sleep(record)` / `bedtime_day(record)` / `wake_day(record)` | 夜の主睡眠か / 寝始めた実日付 / 目覚めた実日付 |
| `oura_records.g(record, *path, default=None)` | ネストした項目を安全に取り出す |

| 例外 | 意味 |
|---|---|
| `oura_api.OuraError` | 取得の基底。スクリプトはこれを捕まえる |
| `oura_api.OuraAPIError` | APIがエラーを返した。`.status` にHTTPステータス |
| `oura_auth.OuraAuthError` | 認証情報が無い / トークンの発行・更新を拒否された |

### シェルから起動するスクリプト

いずれも環境変数、無ければ起動フォルダ（プロジェクトのフォルダ直下）の `.env` から `OURA_*` を読み、トークンを更新したら `.env` の `OURA_*` の行だけを書き換える。プロジェクトのフォルダから `<skill-dir>/scripts/...` の形で起動し、スキルのフォルダへ cd しない。

| スクリプト | 中身 |
|---|---|
| `uv run <skill-dir>/scripts/oura_auth.py init <client_id> <client_secret> [redirect_uri]` | 起動フォルダの `.env` に `OURA_*` の行を書く |
| `uv run <skill-dir>/scripts/oura_auth.py exchange <code>` | 認可コードをトークンに交換して保存する（初回だけ） |
| `uv run <skill-dir>/scripts/oura_auth.py ensure` | トークンが有効かを確かめ、有効期限を表示する。トークンは表示しない |
| `uv run <skill-dir>/scripts/oura_api.py <endpoint> [start] [end] [--summarize]` | 1つのエンドポイントを取ってJSONで出す。`--summarize` で長大な時系列を要約する |

## 索引

| 判断             | ファイル                                                | 扱うこと                          | 依存する判断     | いつ聞くか                                |
| -------------- | --------------------------------------------------- | ----------------------------- | ---------- | ------------------------------------ |
| 認証とトークン        | [auth.md](references/auth.md)                       | トークンをどう更新し、どこに置き、401をどう読むか    | —          | 認証情報を設定する前・Ouraに接続するコードを書く前・401が出たとき |
| APIの呼び方        | [client-usage.md](references/client-usage.md)       | どの入口から呼び、何を呼び出し側で書かないか        | 認証とトークン    | Ouraを読むコードを書く前・404が出たとき              |
| 心拍の取り方         | [heartrate.md](references/heartrate.md)             | 心拍の範囲の指定と、日ごとの集計              | —          | 心拍を取る前・400が出たとき                      |
| 境界日の取りこぼし      | [date-boundary.md](references/date-boundary.md)     | どの範囲で取り、どう対象日のレコードを拾うか        | —          | 期間を指定して取る前                           |
| 長大な時系列の要約     | [raw-data.md](references/raw-data.md)               | 長大な時系列の配列を全件で取るか、どう要約するか    | —          | 時系列を含むレコードを取るコードを書く前              |
| データが確定する時期     | [data-latency.md](references/data-latency.md)       | いつ取り、記録済みの日次をどうするか。空の項目をどう読むか | —          | 同期の対象日と時刻を決めるとき・項目が空だったとき            |
| レコードの同一性       | [record-identity.md](references/record-identity.md) | 何で重複を判定し、既にあったらどうするか          | データが確定する時期 | 記録する処理を書く前                           |
| タグの読み方         | [tags.md](references/tags.md)                       | 2つの形式と終了時刻の有無、重複の除き方          | レコードの同一性   | タグを記録する前・タグを数える前                     |
| 睡眠区間と日次の睡眠の読み方 | [sleep-periods.md](references/sleep-periods.md)     | 昼寝の混ざり方、日付のずれ、スコアと時間の違い       | 境界日の取りこぼし  | 睡眠のデータを日付で引く前・睡眠時間やHRVを集計する前         |

## 依存の順

答えを別の判断の材料にする依存は無い。どの判断から聞いてもよい。索引の「依存する判断」は、あわせて読むと答えの前提が分かる判断で、各ファイルの本文からリンクしている。

## 判断ファイルの形

判断を足すとき・直すときは、この形を守る。

| 項目 | 書くこと |
|---|---|
| 求める材料 | 呼び出し側に求めるもの。列は「材料・種類・必須・形・無いとき」。判断の対象は、Ouraでする作業。種類は `対象の属性`（作業の中身）/ `対象の記録` / `別の判断` / `導入先の環境`（判断が環境に依るときだけ） |
| 答え | 判断そのもの |
| 値 | 作成者が決めた値だけを、`| 名前 | 値 | 単位 |` の表で書く。無ければ省く |
| 道具 | 道具の使い方。どの道具を、どう呼び、何を守るか |
| 理由 | なぜそう判断するか。実際に確かめた日付と、起きたことを残す |
| 却下した案 | 選ばなかった案と、その理由。記録が無ければ「記録なし」と書く |
| 当てはまる範囲と限界 | どこまで使えるか |

- **導入先の環境は書かない。** 認証情報・どこに記録するか・列名は、呼び出し側か `.env` が持つ。
- **環境の仕様に合わせた値は、道具のコードの定数が正。** APIのURL・エンドポイントのパス・心拍の上限日数のような値は、人が決めるものではないので判断ファイルに値の表として置かない。判断の本文から「`oura_api.py` の定数が正」と指す。
- **道具は値の表を読まない。** 多くのスキルが読み込むたびにimportするので、表の書き損じ1つで、使うすべてのスキルが止まるため。作成者が決めた値（前後に足す日数・要約の閾値）はコードに定数として置き、表は写しとして残し、決めた理由を判断ファイルに書く。

## 設定が無いとき → README の「セットアップ」

認証情報は導入先の環境なので、スキルの外に置く。OAuthアプリの作成と認可は人の手作業で、手順は README の「セットアップ」だけが持つ。次の合図が出たら先へ進まず、README の「セットアップ」をユーザーに案内する。

| 合図 | 足りないもの |
|---|---|
| `client_id/client_secret is missing. run 'init' first.` | 起動フォルダの `.env`、またはその中の `OURA_CLIENT_ID`・`OURA_CLIENT_SECRET` |
| `refresh_token is missing. run 'exchange' first.` | 認可（ブラウザでの認可と、コードの交換） |
| `daily_resilience`・`daily_cardiovascular_age`・`vo2max` だけが401 | 認可のスコープ `stress`・`heart_health`（[認証とトークン](references/auth.md)） |
| `Oura token endpoint error 400`（refresh のとき） | 有効な refresh_token。別の処理が先に使った・古い値に戻した、のどちらか。認可からやり直す |

## 未決

- 心血管年齢の `pulse_wave_velocity` が実データで入るか（[データが確定する時期](references/data-latency.md)）。
- 前後に足す日数（1日）と、長大な時系列の要約の閾値（200文字・20件・5件）を決めた理由の記録が無い。
