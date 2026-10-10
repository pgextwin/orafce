# orafce Windows パイロット

**状態：技術検証中。全 PostgreSQL major の機能テスト・成果物検査が成功するまで公開禁止。**

上流：https://github.com/orafce/orafce/tree/e538f81acccf73bd9c40977e22e8c4984e452622

上流 Meson と MSVC を利用します。ICU 等の Windows 依存関係、SQL 関数の DLL エクスポートを検証します。
PG14 は 2026-11-12 を超えて維持しません。ZIP の対応 major、SQL ファイル、ライセンス、SBOM・Grype・出自を確認してください。現時点では本番環境への導入を推奨しません。

### PostgreSQL 14 のWindows互換性

PG14 の標準Windows版 `postgres.lib` は内部変数 `Mode` をエクスポートしません。PG14に限り、一時的な上流ビルド領域で `orafce.umask` の権限チェック条件をトランザクション状態に基づく、同等以上に厳格な判定へ切り替えます。PG15〜18は上流コードのままです。固定済み上流ソースの一致確認に失敗した場合はビルドを中止します。
