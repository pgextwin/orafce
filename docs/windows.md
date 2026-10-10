# Windows pilot — orafce

Status: **engineering only / release blocked until green full matrix**.

Upstream: https://github.com/orafce/orafce/tree/e538f81acccf73bd9c40977e22e8c4984e452622

Native MSVC/Meson compilation uses upstream source; an exact Windows dependency and export audit is required. The pinned upstream control file may advertise a future default_version; the test checkout must use the release SQL version 4.16 rather than claiming 4.17.

1. Validate full native Windows x64 CI for PG14 (if still maintained) through PG18.
2. Verify exact license bytes and immutable upstream SHA.
3. Validate `CREATE EXTENSION orafce` and scenarios in `config/test-contract.json`.
4. For deployment, stop the server before replacing libraries; install the ZIP contents into the matching PostgreSQL root and restart for preload modules.
5. Run the documented SQL tests and repeat on an isolated production-equivalent Windows environment.

Do not install a pilot ZIP into production and do not treat unexecuted tests as passes. Upgrades, rollback, interaction with other extensions and backup/restore require separate testing.

All published binary artifacts must carry source provenance, exact PostgreSQL major, checksums, SBOM and vulnerability report.
