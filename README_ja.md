# orafce — Windows x64 技術パイロット

[English](README.md) | 日本語

通常の Windows 版 PostgreSQL 向けの**非公式・検証中**の拡張機能です。実際の CI で合格するまで、バイナリ配布や動作保証はしません。

- 上流：`orafce/orafce`、安定版 `VERSION_4_16_13`、固定コミット `e538f81acccf73bd9c40977e22e8c4984e452622`
- 対象：PostgreSQL 14・15・16・17・18、Windows x64
- PG14 は上流が対応する場合のみ。2026-11-12 の EOL 後は共通 Build のマトリクスから自動除外
- 各 PostgreSQL major で Windows ビルド、PostgreSQL 起動、実機能検証、ZIP、SPDX SBOM、Grype、チェックサムを実施
- 正式 Release・Catalog・Website 掲載は、実動作と検証済み成果物が揃うまで禁止

[機能範囲と導入方法](docs/windows_ja.md) を参照してください。
