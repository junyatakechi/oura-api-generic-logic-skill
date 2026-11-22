---
sources:
  S1:
    name: "Oura API v2 の OAuth2 の仕様"
    checked: "記録なし"
---

# 認証とトークン

## 扱うこと

認証情報を設定する・Ouraに接続するコードを書く・401が出たとき、トークンをどう更新し、どこに置き、401をどう読むか

## 答え方と理由

### 0. 判断全体

Oura API v2 の OAuth2 について、次のとおりにする。`OuraAuthError` がどの設定の不足によるかは、この判断では答えない（→ [設定の不足](missing-setup.md)）。

### 1. 認可は、人が一度だけ行う

Oura API v2 は OAuth2 が必須。OAuthアプリ（client_id・client_secret）を作り、ブラウザで認可して得たコードをトークンに交換する。これは人が一度だけ行う。

1. 記録なし

### 2. refresh_token は使い捨てなので、更新したら必ず保存する

refresh_token は使い捨て。更新したら、新しい refresh_token で `.env` の `OURA_*` の行を必ず上書きする。トークンの3つ（`OURA_ACCESS_TOKEN`・`OURA_REFRESH_TOKEN`・`OURA_EXPIRES_AT`）は環境変数で渡さない。手で古い値に戻さない。

1. （知見）Oura の OAuth2 の仕様で、refresh_token は1回使うと新しい値に置き換わる。（出典：S1）
2. （根拠）環境変数が `.env` より優先されるので、トークンを環境変数で渡すと、更新した値が使われなくなる。（決定日：記録なし）

### 3. APIを呼ぶ前に、毎回 `ensure_access_token()` を通す

APIを呼ぶ前に、毎回 `ensure_access_token()` を通す。期限まで【更新する期限の手前】を切っていれば更新する。呼び出し側で更新の要否を判断しない。

1. （知見）access_token は、数十分〜24時間ほどで失効する。（出典：なし）

### 4. 認証情報を、スキルにもNotionにもチャットにも出さない

認証情報（client_id・client_secret・access_token・refresh_token）は、スキルの中にもNotionにも書かない。プロジェクトのフォルダ直下の `.env` を、道具が都度読み書きするだけにする。トークンをチャットに表示しない。

1. 記録なし

### 5. 特定のエンドポイントだけの401は、スコープ不足と読む

特定のエンドポイントだけが401になるのは、認可のスコープ不足。`daily_resilience`・`daily_cardiovascular_age`・`vo2max` だけが401なら、認可のときに `stress`・`heart_health` のスコープを付けていない。スコープを足して認可からやり直す。トークンの失効と読まない。

1. （原因）2026-07 に、その3つのエンドポイントだけが401になり、ほかは取れていた。日は残っていない。（発生日：記録なし）

## 判断定数

多くのスキルがimportする道具なので、道具はこの表を読まない。正は `oura_auth.REFRESH_MARGIN_MIN` の定数で、この表は写し。

| 名前 | 値 | 単位 | 理由 |
|---|---|---|---|
| 更新する期限の手前 | 5 | 分 | 記録なし |

## 未決

なし

## 求める材料

| 材料 | 種類 | 必須 | 形 | 無いとき |
|---|---|---|---|---|
| 認証に関わる作業 | 対象の値 | ○ | 文章（例：`"初めての設定"`・`"APIを呼ぶコードを書く"`・`"401が出た"`） | 判断できない |
| 401になったエンドポイント | 対象の値 | — | `["daily_resilience", "vo2max"]` | 答え方5を省いて答える |

## 計算

なし

## 道具

答え方2・3：`oura_auth.ensure_access_token()` が、有効な access_token を返し、必要なら更新して保存する。どちらも道具の中に実装してある。

答え方1：`uv run <skill-dir>/scripts/oura_auth.py init <client_id> <client_secret> [redirect_uri]` で起動フォルダの `.env` に `OURA_*` の行を書き、`uv run <skill-dir>/scripts/oura_auth.py exchange <code>` で認可コードをトークンに交換して保存する。

答え方3：`uv run <skill-dir>/scripts/oura_auth.py ensure` で、トークンが有効かを確かめ、有効期限を表示する。トークンそのものは表示しない。

失敗は `OuraAuthError` で返す。読み書きするのは起動フォルダの `.env` で、同じキーの環境変数があれば、読むときはそちらを優先する。

トークンの発行先は、`oura_auth.py` の定数が正。Oura API の仕様（公知の事実）なので、判断ファイルには置かない。
