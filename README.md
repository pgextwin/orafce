# orafce — Windows x64

[日本語](README_ja.md) | English

pgextwin provides **unofficial Windows x64 binaries** of [orafce](https://github.com/orafce/orafce). orafce adds Oracle-compatible functions and packages to PostgreSQL.

## Download and compatibility

Get the ZIP for your PostgreSQL major version from the [latest published Release](https://github.com/pgextwin/orafce/releases/latest), or [browse all Releases](https://github.com/pgextwin/orafce/releases). Published PostgreSQL **14–18** packages are listed in the [pgextwin catalog](https://pgextwin.github.io/website/en/). PostgreSQL 14 community support ends November 12, 2026; historical downloads may remain available.

## Installation

1. Back up the PostgreSQL installation and check [upstream orafce documentation](https://github.com/orafce/orafce).
2. Stop PostgreSQL before replacing extension files. Unpack the ZIP for your PostgreSQL major and copy the included lib/ and share/extension/ files into the matching PostgreSQL directories.
3. Start PostgreSQL, then run CREATE EXTENSION orafce; in each database that needs it. Shared preloading is not required.
4. Follow the upstream documentation for function usage and any search_path settings, and test in a non-production environment first.

Verify the downloaded ZIP with SHA256SUMS.txt from its Release. Check the Release for any SPDX SBOM, vulnerability report and signed attestations.

## License

This is an independent community Windows build, not an official upstream release. The upstream project documents its SQL functions and limitations. See the included license notices.
