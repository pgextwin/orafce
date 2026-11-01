# R11 controlled historical Draft — separate from real candidate qualification

This single-use original provider integration mode is deliberately not a new stable,
not a candidate manifest update and not release approval. It reuses true upstream
orafce/orafce VERSION_4_17_1 annotated tag and commit under an actual protected
single-file user-authorized request. Its output is one bot-authored Draft PR in
`r11-controlled-draft/r11d-...` changing only
`docs/r11-controlled-draft-proof/r11d-....md`. It does not touch the
`auto-candidate/` branch namespace, config/extension.json, legacy Issues,
schedules, releases, Catalog or Website.

Original request file must be the sole addition of a user-authored and user-merged
protected PR to main:
`.github/r11-controlled-draft-intents/<requestId>.json`.
Use exact JSON keys identical to the existing controlled Issue source schema,
with mode `CONTROLLED_EXISTING_RELEASE_DRAFT_ONLY` and fresh requestId
`r11d-YYYYMMDD-...`. Source/expiry/replay-key uniqueness is implicit in the
immutable request blob/branch; never use existing or expired ID.
The source is validated via original push/PR/actor/full blob/HEAD, required
App15368 Summary, and 3 authentic upstream GETs.

Provider writes are one-shot POST `git/trees`, `git/commits`,
`git/refs` and `pulls`; journal UNKNOWN before each write. Ambiguous ACK,
pre-existing candidate branch/PR, changed main, forged actor, moved upstream
or provider failure stop fail-closed; never blindly replay. Every write has
read-only independent GET and the last Draft PR must be open, draft, bot-owned,
base exact protected main, and one isolated proof file. The new Draft PR is not
auto-merged. Due to GITHUB_TOKEN event-suppression, its own CI is not assumed
to automatically run: this mode never counts native candidate dispatch #483.

A controlled success is only CONTROLLED_INTEGRATION_DRAFT_ONLY. The original
#482/#483 formal genuine-new-stable end-to-end requirement remains PENDING.
Runtime stays false and PUBLISH_DENY.
