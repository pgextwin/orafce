# Windows installation and verification — orafce

Status: **v4.16.13-windows.1 published for PostgreSQL 14–18** after the required Windows CI and Release verification. [Published release](https://github.com/pgextwin/orafce/releases/tag/v4.16.13-windows.1).

Upstream: https://github.com/orafce/orafce/tree/e538f81acccf73bd9c40977e22e8c4984e452622

Native MSVC/Meson compilation uses upstream source; an exact Windows dependency and export audit is required. The pinned v4.16.13 release tag correctly sets default_version 4.16; preserve the upstream release control file exactly rather than using the development-branch 4.17 default.

1. Validate full native Windows x64 CI for PG14 (if still maintained) through PG18.
2. Verify exact license bytes and immutable upstream SHA.
3. Validate `CREATE EXTENSION orafce` and scenarios in `config/test-contract.json`.
4. For deployment, stop the server before replacing libraries; install the ZIP contents into the matching PostgreSQL root and restart for preload modules.
5. Run the documented SQL tests and repeat on an isolated production-equivalent Windows environment.

Do not interpret CI coverage as a production compatibility guarantee; verify the exact ZIP on a production-equivalent environment before deployment. Upgrades, rollback, interaction with other extensions and backup/restore require separate testing.

All published binary artifacts must carry source provenance, exact PostgreSQL major, checksums, SBOM and vulnerability report.

### PostgreSQL 14 import-library note

The PG14 Windows `postgres.lib` does not expose the backend data symbol `Mode`. On PG14 only, the disposable build checkout keeps the `orafce.umask` permission guard active whenever a transaction is in progress, rather than importing the internal `IsNormalProcessingMode()` macro's `Mode` symbol. PG15–18 retain upstream logic. The change is constrained to the exact pinned source text and must pass the PG14 functional tests before distribution.
