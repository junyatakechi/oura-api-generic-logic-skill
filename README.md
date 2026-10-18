# oura-api-generic-logic

Oura Ring の公式API（Oura API v2）をClaudeから扱うための、generic-logic スキル。
Claudeに頼むと、トークンを壊したり、境界日のデータを取りこぼしたり、昼寝を夜の睡眠として数えたりする落とし穴を避けながら、Ouraのデータを取得する。

中身は、Ouraを使う人なら誰でも同じ答えになる一般的な判断（落とし穴とその避け方）と、Oura API を呼ぶ道具。取ったデータをどこに記録するかは決めない。
他のスキルがOuraのデータを取るとき・記録されたOuraのデータを読むときに、判断を聞き、道具を部品として使える。

- [SKILL.md](SKILL.md): 役割・判断の索引・道具の一覧・判断ファイルの形
- [references/](references/): 1判断1ファイル。どれも「求める材料・答え・値・道具・理由・却下した案・当てはまる範囲と限界」の形で書いてある
- [scripts/](scripts/): Oura API を呼ぶ道具。標準ライブラリだけで動く

## 必要なもの

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)
- Oura Ring と、Ouraのアカウント
- Python 3.11以上と [uv](https://docs.astral.sh/uv/)

## インストール

スキルのフォルダでクローンする。フォルダ名はリポジトリ名のままでよい。

```bash
git clone https://github.com/junyatakechi/oura-api-generic-logic.git ~/.claude/skills/oura-api-generic-logic
```

特定のプロジェクトだけで使うなら、`<プロジェクト>/.claude/skills/` の中でクローンする。

## セットアップ

1. [OuraのOAuthアプリの画面](https://cloud.ouraring.com/oauth/applications)でアプリを作り、client_id と client_secret を控える。リダイレクトURIは `http://localhost:8765/callback` にする。別の用途で作ったアプリがあれば、それを使ってよい。
2. 認証情報を書く。プロジェクトのフォルダ直下（Claude Code を起動するフォルダ）の `.env` に `OURA_*` の行が書かれる（`.env` が無ければ作られ、他のキーの行はそのまま残る）。キーの名前は同梱の `.env.example` と同じ。以下のコマンドは、どれもプロジェクトのフォルダで実行する。

   ```bash
   cd <プロジェクトのフォルダ>
   uv run ~/.claude/skills/oura-api-generic-logic/scripts/oura_auth.py init <client_id> <client_secret>
   ```

3. ブラウザで次のURLを開いて認可する。`<client_id>` は控えた値に置き換える。**スコープに `stress` と `heart_health` を含める。** 含めないと、回復力・心血管年齢・VO2Maxだけが取れない。

   ```
   https://cloud.ouraring.com/oauth/authorize?response_type=code&client_id=<client_id>&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback&scope=email+personal+daily+heartrate+workout+tag+session+spo2+stress+heart_health
   ```

4. 許可すると `http://localhost:8765/callback?code=...` へ移り、接続エラーになる。手元で何も待ち受けていないためで、問題ない。アドレスバーの `code=` の値を控え、トークンに換える。

   ```bash
   uv run ~/.claude/skills/oura-api-generic-logic/scripts/oura_auth.py exchange <code>
   ```

5. 確かめる。

   ```bash
   uv run ~/.claude/skills/oura-api-generic-logic/scripts/oura_auth.py ensure
   ```

refresh_token は使い捨てで、使うたびに道具が `.env` の `OURA_*` の行を新しい値で上書きする。手で古い値に戻さない。同じ `.env` を、同時に動く2つの処理で使わない。トークンの3つ（`OURA_ACCESS_TOKEN`・`OURA_REFRESH_TOKEN`・`OURA_EXPIRES_AT`）は環境変数で渡さず `.env` に置く。環境変数が優先されるので、更新した値が使われなくなる。

## 使い方

Claudeに普段の言葉で頼むと、Claudeがこのスキルを読み込んで作業する。

| 頼み方 | Claudeがすること |
|---|---|
| 「Ouraの認証を設定して」 | セットアップの手順を案内する |
| 「Ouraに繋がるか確かめて」 | トークンが有効かを確かめる（必要なら更新する） |
| 「Ouraで昨日の睡眠を取ってみて」 | 境界日を取りこぼさない範囲で取り、対象日のレコードを見せる |
| 「Ouraが401を返す」 | スコープ不足かトークンの問題かを見分け、次にすることを答える |

取ったデータをNotionに記録するのは、アプリケーションスキル（oura-collection-app など）の担当。

## 他のスキルから使う

```python
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/oura-api-generic-logic/scripts"))
from oura_auth import ensure_access_token
from oura_api import OuraError, fetch_many
import oura_records

start, end = oura_records.padded_range("2026-07-22", "2026-07-28")   # 前後1日を足す
data = fetch_many(["sleep", "daily_sleep", "heartrate"], ensure_access_token(), start, end)
day_sleep = oura_records.records_on_day(data["sleep"], "sleep", "2026-07-23")
```

| モジュール | 役割 |
|---|---|
| `oura_auth.py` | OAuth2のトークン管理 |
| `oura_api.py` | API通信。ページ送り・心拍の分割・長大な配列の要約・エラー |
| `oura_records.py` | 対象日のレコードの取り出し・心拍の集計・タグの形の統一・睡眠区間の日付 |
| `oura_env.py` | 認証情報の読み書き |

- APIを呼ぶ前に、毎回 `ensure_access_token()` を通す。
- エラーは `sys.exit` ではなく例外（`OuraError`・`OuraAuthError`）で返る。

## ライセンス

[MIT License](LICENSE)
