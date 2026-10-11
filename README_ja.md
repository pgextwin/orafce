# orafce — Windows x64 バイナリ（pgextwin）

[English](README.md) | 日本語

[orafce](https://github.com/orafce/orafce) **4.16.13**（上流タグ `VERSION_4_16_13`、固定コミット `e538f81acccf73bd9c40977e22e8c4984e452622`）を基にした非公式コミュニティ製Windows x64バイナリです。

**現在の公開Release：** [v4.16.13-windows.1](https://github.com/pgextwin/orafce/releases/tag/v4.16.13-windows.1)。PostgreSQL **14〜18**向けに、メジャーバージョン別のZIPを公開しています。SHA256・SPDX SBOM・Grype・証明情報は[pgextwin Pages](https://pgextwin.github.io/website/ja/)で確認できます。上流公式のWindows配布ではありません。

Windows CIではPostgreSQLの起動、`CREATE EXTENSION orafce`、Oracle互換`last_day`のうるう年処理、`nvl`のNULL置換を実際に検証しています。**事前ロードは不要**です。Oracle互換機能のすべて、拡張機能のアップグレード、Oracleとの完全互換性を検証済みとするものではありません。[Windows導入・検証ガイド](docs/windows_ja.md)も参照してください。

PostgreSQL 14の新規ビルド対象は公式EOLの**2026-11-12**までで、公開済みZIPはEOL後も履歴として保持します。上流更新だけで無条件にReleaseを公開する運用ではありません。
