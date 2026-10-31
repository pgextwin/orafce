# R10-02：停止前のdispatch入力の保全

過去の制御skip Run41014360341とtimeout Run41015468625は、入力を保存する処理より前に停止した。どちらも子artifactは存在しない。元の7入力を過去のRun時刻やソースから推測して完全結合したとはしない。原本は変更・再実行しない。

今後の真正App workflow_dispatchでは、独立した最初のjobが既存authenticate_eventを通し、7個の宣言済み入力・実sender・Run/attempt・HEADをoriginal artifactへ保存する。PREPAREはこのupload成功後だけ開始する。このjobは中央ZIPの真正性、ローカル処理完了、OIDC署名、公開を認可しない。scopeはAUTHENTICATED_DISPATCH_INPUT_OBSERVATION_ONLY、centralSourceAdmissionVerified=false、childPrepareCompleted=false。

環境変数全体・イベント全体・Secretは保存しない。未知の入力、偽actor/ID、別ref/head、attempt2、誤ったrequestは既存検証器で拒否する。保存失敗ならPREPARE開始を止める。既存の中央原本照合・App signing intent・PG14〜18・二重Sigstore・PUBLISH_DENYのゲートは継続する。

再現：

```bash
python tests/test-issue311-app-local-prepare.py
python tests/test-issue311-dispatch-input-observation.py
```

新しい3テストはoffline fixtureで、実dispatchの証明ではない。PRとoriginal postmerge pushで同じテストを実行する。Windows必須CIとprotected merge/original postmergeも確認する。

live受入には、後の明示された限定要求による新しい真正Run、観測artifactの実ZIP SHA256、7入力と中央source/request/cycleの結合、実際のskip/timeoutのjob原本、State CAS/revoke401/別Runner readbackが必要。この修正をマージしただけではR10-02を受入しない。新しい障害試験の承認や人工の承認待ちは作らず、旧成功Runをrerunしない。
