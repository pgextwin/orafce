# R11 S6: source-bound candidate draft PR pilot

This pilot adds only a create-once draft candidate PR. It does not replace the
old schedule, legacy Issue reconciliation, candidate CI dispatch, signed audit,
Publisher, state CAS, recovery, or fleet operation.

## Activation boundary

Only a new one-file protected human intent with mode
`CANDIDATE_PR_NONPUBLISHING` can activate the job. Existing intents retain
their original mode and do not activate it. Source admission independently
rechecks real GitHub push/actor/merge provenance in the Writer job. No new
intent is included in this implementation PR; do not fabricate an upstream
update to exercise POST.

The same-run read-only candidate plan must match an independently recomputed
plan using central code at `19477b9440ce809fbadbd4fc0c7fadfd40a4a78f`, live
central BUILD policy, current protected main, stable upstream tag and full SHA.
Only uniform orafce stable upgrades for PG14–18 are supported. No-op writes
nothing; other shapes fail closed.

## Exact writes and collision boundary

| Resource | Permitted operation | Conflict/uncertainty behavior |
| --- | --- | --- |
| Git tree/commit | Create object with sole `config/extension.json` change, parent exact source SHA | Stop on ambiguity; no automatic resubmission |
| `auto-candidate/<20-hex-id>` | Create ref once; same digest as legacy proposer | Existing ref/PR blocks; no PATCH/PUT/force/delete/repair |
| Candidate PR | Create draft to main once, independent ownership/HEAD/body readback | Ambiguous response quarantined; no retry/reopen/merge |
| Windows workflow / Release / Issue / state | No writes | Denied by endpoint allowlist and job scopes |

New and old proposers share `candidate-proposer-${{ github.repository }}`.
This coordinates cooperating jobs; it does not prove live old/new contention,
CAS durability, HTTP409, token revocation, or safe recovery after runner loss.
The matching-refs GET and create-only ref POST protect against overwriting a
concurrently created branch. The final GET is not an atomic main-HEAD lease.

Before every POST, the runner receipt records UNKNOWN. After a failed or lost
response the job stops, preserves its best available receipt, and makes no
second POST. Runner-local journaling is not durable App CAS. Recovery must
independently GET the candidate namespace and source before any new request;
this pilot itself never resumes a partially written candidate.

GITHUB_TOKEN-created PR CI is not assumed to fire. There is no actions:write
or CI dispatch in this pilot. A draft PR without native CI remains unaccepted.
Actual nonempty Writer operation needs a genuine eligible update and a fresh
protected human intent; offline tests cannot substitute for those originals.
R11-01/R11-02 and their parent stay PENDING until all contract gates hold.

## Reproducible checks

Run `python tests/test-issue311-r11-candidate-pr-writer.py` plus existing R11
source/candidate/central/readonly/notice tests. Mutation tests cover source
identity, plan/tag/SHA mismatch, write allowlists, main advancement, sole-file
diff and byte readback, existing candidate refusal, draft ownership, controlled
ACK loss and synthetic HTTP409 with one-call termination. These tests are
offline evidence only, never actual GitHub writes or original conflict proof.
