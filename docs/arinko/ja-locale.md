# 管理画面とテンプレート編集画面の日本語化

上流（docusealco/docuseal）の日本語訳は、署名する人の画面と `config/locales/i18n.yml` の `ja:` の一部だけである。
残りの管理画面とテンプレート編集画面は、このフォークで次の2つのファイルに訳している。

| 対象 | 訳を置くファイル | 上流のファイルとの関係 |
|---|---|---|
| 管理画面・メール・通知（Rails の i18n） | `config/locales/arinko_ja.yml` | 新規ファイル。`ja:` の下に、上流の `ja:` に無いキーだけを置く |
| テンプレート編集画面（Vue） | `app/javascript/template_builder/i18n_ja.js` | 新規ファイル。`i18n.js` に `import` 1行と `export` の1語を足して読み込む（行末に `// ARINKO`） |
| 署名する人の画面 | `app/javascript/submission_form/i18n.js` の `ja` | 上流の訳をそのまま使う。このフォークでは触らない |

言語の選択は、テンプレート編集画面では `builder.vue` が `i18n[this.language]` で引くため、`i18n.js` から `ja` を export すれば拾われる。
Rails 側は `config/locales/*.yml` をすべて読むので、`arinko_ja.yml` を置くだけで読み込まれる。

## 訳の決まり

- 中小企業の総務・経営者が読む業務用の日本語。文は「です・ます」調、ボタンやラベルは体言止め。
- `%{name}`、`{template.name}`、`{count}` などの埋め込み変数と HTML タグは、そのまま残す。`_html` で終わるキーはタグの構造も残す。
- 製品名・帰属表示の「DocuSeal」は訳さず、消さない。AGPL の追加条項（LICENSE_ADDITIONAL_TERMS）で、画面の DocuSeal の帰属表示を残す義務があるため。
- 上流の `ja:` に既にあるキーは `arinko_ja.yml` に書かない。上流の訳を優先する。

## 用語集

上流の `ja:` と `submission_form/i18n.js` の ja で使われている語に合わせてある。食い違ったときは上流の訳を優先し、この表を直す。

| 英語 | 日本語 | 備考 |
|---|---|---|
| template | テンプレート | |
| submission | 送信 | 書類1件の署名依頼のまとまり。上流 `ja:` の1か所（完了した提出に関連付けられた…）だけ「提出」 |
| submitter / signer | 署名者 | |
| recipient | 受信者 | |
| party | 当事者 | 上流の「他の当事者」に合わせる。`first_party` は「第1当事者」 |
| field | 項目 | |
| audit log / audit trail | 監査ログ | |
| event log | イベントログ | |
| webhook | Webhook | |
| API key / API token | API キー / API トークン | |
| account | アカウント | |
| user | ユーザー | |
| archive / archived | アーカイブ / アーカイブ済み | |
| completed | 完了 | |
| pending | 未完了 | |
| declined / decline | 辞退済み / 辞退 | |
| expired | 期限切れ | |
| delegate | 委任 | |
| 2FA | 2段階認証 | 上流の訳に合わせる |
| sign in / sign out | サインイン / サインアウト | |
| folder | フォルダー | |
| embedding | 埋め込み | |
| tenant | テナント | |
| redact（編集画面） | 墨消し | |

## 上流が英語のキーを足したときの追従手順

上流を rebase / merge したら、次を実行する。

```sh
python3 tools/arinko/check_ja_locale.py --list-english
```

出力の見方:

- `[1] 足りないキー`: 上流の `en:` に足されたキー。`config/locales/arinko_ja.yml` の `ja:` 配下に、`en:` と同じ階層で訳を足す。
- `[1] 上流と重なるキー`: 上流が `ja:` に同じキーの訳を足したもの。`arinko_ja.yml` からそのキーを消す（上流の訳を優先する）。
- `[1] en に無いキー`: 上流が `en:` から消したキー。`arinko_ja.yml` からも消す。
- `[2] 変数が違う / タグが違う`: `%{...}`・`{...}`・HTML タグの集合が `en:` と一致しない。訳を直す。
- `[3] template_builder`: `i18n.js` の `en` に足されたキーを `i18n_ja.js` に足す。同じ順序で並べる。
- `[参考] 訳し忘れの疑い`: 値が英語のままのキー。固有名詞なら放置してよい。

最後の行が `結果: OK`（終了コード 0）になれば追従は完了。node が無い環境では、template_builder の比較は正規表現にフォールバックする。
依存は Python 3 と PyYAML だけ。

## Rails を立てずに確かめる方法

`docker build` で本体のイメージを作り、管理画面を日本語（アカウント設定の言語で「日本語」を選ぶ）で開くと、英語が残っている画面を目で探せる。
文言だけの変更なので、データベースや API には影響しない。

## 監査ログの訳の語順(submission_event_names)

監査ログの PDF(`lib/submissions/generate_audit_trail.rb`)は、各行を `<b>(.*?)</b>(.*)` で太字と残りに分け、`<b>` より前の文字を捨てる。
日本語の語順で署名者名を文頭に置くと、監査ログから署名者名が消える。`submission_event_names` の訳は必ず `<b>` で始め、
署名者名・宛先は後ろに置く(例 `<b>署名を完了</b> 署名者: %{submitter_name}`)。`check_ja_locale.py` の [2] がこれを検査する。
