# oura-api-generic-logic-skill

Oura Ring の公式API（Oura API v2）を扱うときの、一般的な判断を持つロジックスキル。
トークンを壊す・境界日のデータを取りこぼす・昼寝を夜の睡眠として数える、といった落とし穴とその避け方を答え、Oura API を呼ぶ道具を部品として渡す。

## 必要なもの

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)
- Python 3.11以上と [uv](https://docs.astral.sh/uv/)
- Oura Ring と、Ouraのアカウント

## インストール

```bash
git clone https://github.com/junyatakechi/oura-api-generic-logic-skill.git ~/.claude/skills/oura-api-generic-logic-skill
```

特定のプロジェクトだけで使うなら、`<プロジェクト>/.claude/skills/` の中でクローンする。

## セットアップ

1. [OuraのOAuthアプリの画面](https://cloud.ouraring.com/oauth/applications)でアプリを作り、client_id と client_secret を控える。リダイレクトURIは `http://localhost:8765/callback` にする。別の用途で作ったアプリがあれば、それを使ってよい。
2. 認証情報を書く。プロジェクトのフォルダ直下（Claude Code を起動するフォルダ）の `.env` に `OURA_*` の行が書かれる（`.env` が無ければ作られ、他のキーの行はそのまま残る）。キーの中身は `.env.example` のコメントにある。以下のコマンドは、どれもプロジェクトのフォルダで実行する。

   ```bash
   cd <プロジェクトのフォルダ>
   uv run ~/.claude/skills/oura-api-generic-logic-skill/scripts/oura_auth.py init <client_id> <client_secret>
   ```

3. ブラウザで次のURLを開いて認可する。`<client_id>` は控えた値に置き換える。**スコープに `stress` と `heart_health` を含める。** 含めないと、回復力・心血管年齢・VO2Maxだけが取れない。

   ```
   https://cloud.ouraring.com/oauth/authorize?response_type=code&client_id=<client_id>&redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback&scope=email+personal+daily+heartrate+workout+tag+session+spo2+stress+heart_health
   ```

4. 許可すると `http://localhost:8765/callback?code=...` へ移り、接続エラーになる。手元で何も待ち受けていないためで、問題ない。アドレスバーの `code=` の値を控え、トークンに換える。

   ```bash
   uv run ~/.claude/skills/oura-api-generic-logic-skill/scripts/oura_auth.py exchange <code>
   ```

5. 確かめる。

   ```bash
   uv run ~/.claude/skills/oura-api-generic-logic-skill/scripts/oura_auth.py ensure
   ```

refresh_token は使い捨てで、使うたびに道具が `.env` の `OURA_*` の行を新しい値で上書きする。手で古い値に戻さない。トークンの3つ（`OURA_ACCESS_TOKEN`・`OURA_REFRESH_TOKEN`・`OURA_EXPIRES_AT`）は環境変数で渡さず `.env` に置く。環境変数が優先されるので、更新した値が使われなくなる。

## 使い方

主に、アプリケーションスキルから呼ばれる。
直接頼むときも、`/oura-api-generic-logic-skill` で名前を指名する。指名しないと、このスキルは読み込まれない。

- 「/oura-api-generic-logic-skill Ouraに繋がるか確かめて」
- 「/oura-api-generic-logic-skill 昨日の睡眠を取ってみて」
- 「/oura-api-generic-logic-skill Ouraが401を返す」
