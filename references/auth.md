# 認証とトークン

## 求める材料

| 材料 | 種類 | 必須 | 形 | 無いとき |
|---|---|---|---|---|
| 認証に関わる作業（例：初めての設定、APIを呼ぶコードを書く、401が出た） | 対象の属性 | ○ | 文章 | 判断できない |
| 401になったエンドポイント | 対象の記録 | — | エンドポイント名 | 答え5を省いて答える |

## 答え

1. **Oura API v2 は OAuth2 が必須。** OAuthアプリ（client_id・client_secret）を作り、ブラウザで認可して得たコードをトークンに交換する。これは人が一度だけ行う。
2. **refresh_token は使い捨て。** 1回使うと新しい値に置き換わる。更新したら、新しい refresh_token で `.env` の `OURA_*` の行を必ず上書きする。トークンの3つは環境変数で渡さない（環境変数が優先され、更新した値が使われなくなる）。手で古い値に戻さない。
3. **APIを呼ぶ前に、毎回 `ensure_access_token()` を通す。** access_token は数十分〜24時間ほどで失効する。期限の5分前を過ぎていれば更新する。呼び出し側で更新の要否を判断しない。
4. **認証情報（client_id・client_secret・access_token・refresh_token）は、スキルの中にもNotionにも書かない。** プロジェクトのフォルダ直下の `.env` を、道具が都度読み書きするだけにする。トークンをチャットに表示しない。
5. **特定のエンドポイントだけが401になるのは、認可のスコープ不足。** `daily_resilience`・`daily_cardiovascular_age`・`vo2max` だけが401なら、認可のときに `stress`・`heart_health` のスコープを付けていない。スコープを足して認可からやり直す。

## 道具

- `oura_auth.ensure_access_token()`：有効な access_token を返す。必要なら更新して保存する。答え2・3は道具の中に実装してある。
- `uv run <skill-dir>/scripts/oura_auth.py init <client_id> <client_secret> [redirect_uri]`：起動フォルダの `.env` に `OURA_*` の行を書く。
- `uv run <skill-dir>/scripts/oura_auth.py exchange <code>`：認可コードをトークンに交換して保存する（初回だけ）。
- `uv run <skill-dir>/scripts/oura_auth.py ensure`：トークンが有効かを確かめ、有効期限を表示する。トークンそのものは表示しない。
- 失敗は `OuraAuthError` で返す。
- 読み書きするのは、起動フォルダ（プロジェクトのフォルダ直下）の `.env`。同じキーの環境変数があれば、読むときはそちらを優先する。プロジェクトのフォルダから起動し、スキルのフォルダへ cd しない。

**値（トークンの発行先・期限の5分前）は、`oura_auth.py` の定数が正。**

## 理由

2. Oura の OAuth2 の仕様で、refresh_token は1回使うと新しい値に置き換わる。
5. 2026-07に実機で確かめた。その3つのエンドポイントだけが401になり、ほかは取れていた。

## 却下した案

記録なし。

## 当てはまる範囲と限界

- Oura API v2 の OAuth2 で確かめたこと。仕様が変わったら試し直す。
