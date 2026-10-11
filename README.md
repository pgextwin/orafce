# orafce — Windows x64 binaries (pgextwin)

[日本語](README_ja.md) | English

This repository publishes unofficial, community-built Windows x64 binaries of [orafce](https://github.com/orafce/orafce) **4.16.13** (`VERSION_4_16_13`), pinned to upstream commit `e538f81acccf73bd9c40977e22e8c4984e452622`.

**Current published release:** [v4.16.13-windows.1](https://github.com/pgextwin/orafce/releases/tag/v4.16.13-windows.1), covering PostgreSQL **14–18**. Use the ZIP for the matching PostgreSQL major. SHA256 hashes, SPDX SBOM, Grype reports and attestations are referenced from the [pgextwin Catalog](https://pgextwin.github.io/website/en/). These are not upstream-official Windows packages.

The Windows functional CI validates server startup, `CREATE EXTENSION orafce`, Oracle-compatible `last_day` leap-year behavior and `nvl` NULL substitution. Preload is not required. CI does **not** claim coverage of all Oracle compatibility functions, extension upgrades or application-level Oracle equivalence. See [Windows installation guidance](docs/windows.md).

PostgreSQL 14 is eligible for new builds only through **2026-11-12** (community EOL); published assets remain historically available after EOL. The release is published only after required verification, not automatically on every upstream change.
