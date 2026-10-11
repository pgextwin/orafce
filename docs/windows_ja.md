# orafce Windows 導入・検証ガイド

**状態：[v4.16.13-windows.1](https://github.com/pgextwin/orafce/releases/tag/v4.16.13-windows.1)をPG14〜18向けに公開済み。** 全majorのWindows CI・機能テスト・成果物検証を経て公開しました。

上流：https://github.com/orafce/orafce/tree/e538f81acccf73bd9c40977e22e8c4984e452622

上流 Meson と MSVC を利用します。ICU 等の Windows 依存関係、SQL 関数の DLL エクスポートを検証します。
PG14 は 2026-11-12 を超えて維持しません。ZIP の対応 major、SQL ファイル、ライセンス、SBOM・Grype・出自を確認してください。実運用前には対象のWindows版PostgreSQL上で、互換性とバックアップ・復旧手順を別途検証してください。

### PostgreSQL 14 のWindows互換性

PG14 の標準Windows版 `postgres.lib` は内部変数 `Mode` をエクスポートしません。PG14に限り、一時的な上流ビルド領域で `orafce.umask` の権限チェック条件をトランザクション状態に基づく、同等以上に厳格な判定へ切り替えます。PG15〜18は上流コードのままです。固定済み上流ソースの一致確認に失敗した場合はビルドを中止します。
