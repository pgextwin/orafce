# orafce — experimental Windows x64 technical pilot

[日本語](README_ja.md) | English

This is an **unofficial, unverified technical pilot** for [orafce](https://github.com/orafce/orafce) on standard Windows PostgreSQL 14–18 x64. **No binary release or successful functional compatibility is claimed until each CI matrix job actually passes.**

- Official upstream tag: `VERSION_4_16_13`
- Pinned upstream commit: `e538f81acccf73bd9c40977e22e8c4984e452622`
- Release version: `4.16.13`
- PostgreSQL 14 is eligible **only until 2026-11-12**, subject to actual upstream and Windows runtime compatibility. Central `resolve-matrix.ps1` removes it after end of support.
- PostgreSQL 15, 16, 17, 18 require independent passing build, server startup, functional test, ZIP, SPDX SBOM, Grype and checksum checks.
- License files in this repository are exact upstream copies verified during CI against the pinned source.
- See [pilot scope and installation](docs/windows.md).

There is **no automatic release**, no catalog promotion, and no unattended publishing in this pilot.
