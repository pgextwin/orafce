# R11 controlled nonpublishing Writer (historic real upstream)

This is an isolated **real GitHub Issue POST/readback**, never an update notice or live
future stable acceptance. It reuses the actual existing `orafce/orafce` Release
`VERSION_4_17_1`, annotated tag and full commit. It does not change config
versions, Release, Catalog, Website, schedules, or production Issue namespaces.

The user-authorized immutable single-file intent must be merged via a protected
PR whose author and merger are `ShutenOishi`. Path:
`.github/r11-controlled-intents/r11c-YYYYMMDD-<unique>.json`.
Exactly one file added by the merge; protected App15368 Windows check is required.
Schema version 1: `requestId`, `mode=CONTROLLED_EXISTING_RELEASE_ISSUE_ONLY`,
`repository=pgextwin/orafce`, `expectedPriorMainSha`, `upstreamRepository=orafce/orafce`,
`tag=VERSION_4_17_1`, `tagObjectSha=4003faf7b57d2a97d56051e06f9af677a6c42405`,
`commit=542aed2e0297898cc9844fede3c4452f894b37ed`, `expiresAt` (UTC),
`runtimeEnabled=false`, `publicationAuthorized=false`.

Original push/attempt1 validates the request file blob, original PR actor/merger,
protected HEAD and CI, then performs three live authenticated upstream GETs.
It checks isolated Issue marker absence twice, journals UNKNOWN before the sole
GitHub POST, validates bot author and independently GETs the resulting issue.
Ambiguous ACK, expired intent, upstream mismatch, moved HEAD, duplicates,
foreign author or incomplete Issue enumeration fail closed. No retry on POST.

A confirmed receipt proves **CONTROLLED_INTEGRATION Issue Writer only**;
legacy Issue reconciliation #481, Draft #482, native candidate #483,
real old/new conflict #484, failure #485 and future PUBLIC_E2E are separate.
Do not mark #479 or formal R11 completed merely for source/test-only CI.
Old schedules and PUBLISH_DENY remain unchanged.
