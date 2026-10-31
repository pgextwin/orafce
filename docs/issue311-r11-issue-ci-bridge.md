# R11 S6 continuation: legacy Issue arbitration and native candidate CI bridge

Scope: pgextwin/orafce only. Source is a new protected-main one-file human
intent; no synthetic upstream release, no publication authority, no schedule
removal, no App Secret, and no auto candidate merge.

## Distinct modes and jobs

- `ISSUE_RECONCILE_NONPUBLISHING`: read-only watch/Issue plan first, then a
  separate issues:write job independently reauthenticates the original source
  (full PR, merged-by identity, exact one-file diff, protected branch). It
  reruns the pinned real upstream detector and compares the result except
  `detectedAt`, checks that the central read-only reconciliation agrees, and
  only reconciles the existing
  `<!-- pgextwin-update-watch:v1:upstream:orafce -->` namespace.
  Existing issue edits/closure require exact first-line marker, bot ownership,
  correct title, unique owner, current protected main, and independent
  post-write GET. No update means no write unless a genuine automation-owned
  *open* stale Issue exists, in which case the central contract closes it.
  A new genuine stable update may create or update the one owned Issue.
- `CANDIDATE_PR_NONPUBLISHING`: the existing create-once candidate Writer
  runs first. A separate actions:write job reads its receipt and the original
  source, independently verifies the exact draft PR, parent/HEAD, current
  protected main, candidate manifest blob, one-file diff and branch. It
  allows one `workflow_dispatch` to `windows.yml` on that candidate
  branch only; this is not a Release workflow. It first rejects an already
  dispatched same-head native CI. After a provider HTTP 204 it retrieves the
  original native Run, its conclusion and required Windows summary.
  It never retries the dispatch POST on transport ambiguity.
  A NO_CHANGE receipt cannot dispatch a workflow.

## Acceptance limits and recovery

The existing `#74` source had genuine up-to-date upstream metadata. Do **not**
repeat that no-op or fabricate a release to exercise a write. A future
qualified protected human intent with a real new stable is necessary to prove
candidate POST, native Windows workflow and CI receipt end to end. Offline
negative tests prove guards, not actual provider HTTP409, token revoke or
old/new Writer conflict. The 80-minute job and 80 bounded run polls are finite.
A GitHub API or native CI failure keeps the receipt quarantined and must be
reviewed before a new separately authorized request; no blind resubmission.

Issue changes are not atomic with the legacy schedule writer. A scoped
current-HEAD recheck, unique owner predicate and shared GitHub Issue identity
reduce risk but do not prove a distributed CAS or real old/new concurrency.
Neither the new Issue receipt nor candidate CI receipt is durable App CAS.
No workflow should claim R11-01/R11-02 or their parent PASS solely from these
implementation/hostile PR tests.

Run:
```sh
python tests/test-issue311-r11-event-source.py
python tests/test-issue311-r11-legacy-issue-adapter.py
python tests/test-issue311-r11-native-candidate-ci.py
python tests/test-issue311-r11-candidate-pr-writer.py
```

The user-visible publication state remains `PUBLISH_DENY`,
`runtimeEnabled=false`. Do not delete schedule, create Release/Tag, or edit
Catalog or Website during this pilot. The previous PR#73/74 and original ZIP
proof are historical independent evidence, not tests to repeat.
