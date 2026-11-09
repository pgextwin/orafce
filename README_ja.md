# orafce — Windows x64 バイナリ

[English](README.md) | 日本語

[orafce](https://github.com/orafce/orafce)の**非公式Windows x64バイナリ**です。PostgreSQLでOracle互換の関数やパッケージを利用できます。

## ダウンロードと対応環境

[最新の公開Release](https://github.com/pgextwin/orafce/releases/latest)から、利用中のPostgreSQLメジャーバージョンに一致するZIPを選んでください。[過去のReleases](https://github.com/pgextwin/orafce/releases)も確認できます。PostgreSQL **14〜18**向けの配布状況は[pgextwinカタログ](https://pgextwin.github.io/website/ja/)を参照してください。PostgreSQL 14のコミュニティサポートは2026年11月12日に終了します。

## インストール

1. PostgreSQL環境のバックアップを取り、[上流のorafceドキュメント](https://github.com/orafce/orafce)で必要条件を確認します。
2. 既存ファイルの置き換え前にPostgreSQLを停止します。利用中のPostgreSQLメジャー向けZIPを展開し、lib/とshare/extension/以下のファイルをPostgreSQLの同名ディレクトリに配置します。
3. PostgreSQLを起動し、利用するデータベースで`CREATE EXTENSION orafce;`を実行します。共有ライブラリの事前ロードは不要です。
4. 関数の使い方や`search_path`などの設定は上流ドキュメントに従ってください。本番環境に導入する前に、検証環境で動作を確認してください。

ダウンロードしたZIPは、Releaseに掲載された`SHA256SUMS.txt`と照合できます。SPDX形式のSBOM、脆弱性レポート、署名付き証明の有無はReleaseで確認できます。

## ライセンス

本配布は上流公式のWindows版ではありません。SQLの機能・制限事項は上流プロジェクトの説明を参照してください。再配布条件は同梱のライセンスに従います。
