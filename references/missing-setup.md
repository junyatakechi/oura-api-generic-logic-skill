---
sources:
  S1:
    name: "Oura API v2 の OAuth2 の仕様"
    checked: "記録なし"
---

# 設定の不足

## 扱うこと

道具が `OuraAuthError` を返したとき、どの設定の不足によるものか

## 答え方と理由

### 0. 判断全体

一部のエンドポイントだけが401になるときは、この判断では答えない（→ [認証とトークン](auth.md)）。

### 1. `client_id/client_secret is missing` は、`.env` か client の値が無い

`client_id/client_secret is missing. run 'init' first.` は、起動フォルダの `.env`、またはその中の `OURA_CLIENT_ID`・`OURA_CLIENT_SECRET` が無い。README の「セットアップ」を案内する。

1. 記録なし

### 2. `refresh_token is missing` は、認可がまだ

`refresh_token is missing. run 'exchange' first.` は、ブラウザでの認可と、コードの交換がまだ。README の「セットアップ」を案内する。

1. 記録なし

### 3. refresh のときの `Oura token endpoint error 400` は、認可からやり直す

refresh のときの `Oura token endpoint error 400` は、有効な refresh_token が無い。別の処理が先に使ったか、古い値に戻したかのどちらか。README の「セットアップ」の認可からやり直す。

1. （知見）refresh_token は使い捨てで、1回使うと新しい値に置き換わる。（出典：S1）

### 4. 設定は補わない

設定は補わない。認証情報を探したり作ったりせず、指示者に作ってもらう。認証情報をチャットで受け取らない。

1. 記録なし

## 判断定数

なし

## 未決

なし

## 求める材料

| 材料 | 種類 | 必須 | 形 | 無いとき |
|---|---|---|---|---|
| 道具が返した失敗 | 対象の値 | ○ | `{"例外": "OuraAuthError", "メッセージ": "refresh_token is missing. run 'exchange' first.", "操作": "refresh"}` | 判断できない |

## 計算

なし

## 道具

例外は `oura_auth.OuraAuthError` で捕まえ、メッセージで見分ける。
