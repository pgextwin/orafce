#!/usr/bin/env python3
"""R11 isolated Issue writer hostile tests. Pure fixtures: no network or writes."""
import copy
import importlib.util
from pathlib import Path

p = Path("scripts/issue311-r11-issue-notice-writer.py")
spec = importlib.util.spec_from_file_location("r11_writer", p)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

sha = "a" * 40
source = {
    "schemaVersion": 1, "repository": g.REPO,
    "sourceKind": g.SOURCE_KIND, "intentMode": g.MODE,
    "protectedSourceVerified": True, "attempt": 1,
    "originalRun": 12345, "requestId": "r11-20261031-orafcewriter01",
    "originalAfter": sha, "originalRequestBlob": "b" * 40,
    "candidateWriterCalled": False, "signingPerformed": False,
    "appCasPerformed": False, "scheduleRemoved": False,
    "publicationAuthorized": False, "runtimeEnabled": False
}
mode = {"mode": "NONPUBLISHING_READONLY", "originalRun": 12345,
        "originalHead": sha, "writerCalled": False,
        "publicationAuthorized": False}
detect = {"schemaVersion": 1, "extension": "orafce", "repository": "upstream/orafce",
          "status": "up-to-date", "updates": []}
dry = {"action": "dry-run:none"}
run = {"id": 12345, "run_attempt": 1, "event": "push", "head_sha": sha,
       "head_branch": "main", "path": g.WORKFLOW,
       "repository": {"full_name": g.REPO},
       "actor": {"login": g.ACTOR, "id": g.ACTOR_ID}}
branch = {"name": "main", "protected": True, "commit": {"sha": sha},
          "protection": {"required_status_checks": {"checks": [
              {"context": "Windows required summary", "app_id": 15368}]}}}
issues = []
env = {"GITHUB_REPOSITORY": g.REPO, "GITHUB_EVENT_NAME": "push",
       "GITHUB_REF": "refs/heads/main", "GITHUB_ACTOR": g.ACTOR,
       "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": sha, "GITHUB_RUN_ID": "12345"}
base = [source, mode, detect, dry, run, branch, issues, env]
assert g.decide(*base) == {"action": "NO_CHANGE", "writerCalled": False}
changed = copy.deepcopy(base)
changed[2]["status"] = "update-available"
changed[2]["updates"] = [{"current": {"ref": "v1.0", "version": "1.0"},
                          "candidate": {"ref": "v1.1", "version": "1.1",
                                        "url": "https://github.com/example/release"}}]
changed[3]["action"] = "dry-run:create"
created = g.decide(*changed)
assert created["action"] == "CREATE_NOTICE" and created["writerCalled"] is True
assert created["marker"].startswith(g.MARKER_PREFIX)
exist = copy.deepcopy(changed)
exist[6] = [{"number": 99, "state": "closed", "body": created["marker"]}]
assert g.decide(*exist)["action"] == "ALREADY_RECORDED"
doubled = copy.deepcopy(exist)
doubled[6].append({"number": 100, "state": "open", "body": created["marker"]})
try:
    g.decide(*doubled)
except g.Denied:
    pass
else:
    raise AssertionError("duplicate notice owners admitted")

negatives = [
 (0, "intentMode", "REQUALIFY_EXISTING_CANDIDATE_NONPUBLISHING"),
 (0, "protectedSourceVerified", False),
 (0, "candidateWriterCalled", True),
 (0, "publicationAuthorized", True),
 (0, "scheduleRemoved", True),
 (0, "originalAfter", "f"*40),
 (0, "attempt", 2),
 (0, "requestId", "not-an-id"),
 (1, "originalRun", 9),
 (1, "mode", "WRITER"),
 (1, "writerCalled", True),
 (2, "extension", "pg_ivm"),
 (2, "status", "indeterminate"),
 (3, "action", "write:create"),
 (4, "run_attempt", 2),
 (4, "path", ".github/workflows/update-watch.yml"),
 (5, "protected", False),
 (7, "GITHUB_EVENT_NAME", "schedule"),
 (7, "GITHUB_ACTOR", "github-actions[bot]"),
 (7, "GITHUB_SHA", "f"*40),
 (7, "GITHUB_RUN_ATTEMPT", "2"),
]
for idx, key, value in negatives:
    item = copy.deepcopy(changed)
    item[idx][key] = value
    try:
        g.decide(*item)
    except (g.Denied, ValueError, TypeError, KeyError):
        continue
    raise AssertionError("hostile write admission: " + str((idx, key)))

mismatch = copy.deepcopy(base)
mismatch[3]["action"] = "dry-run:update"
try:
    g.decide(*mismatch)
except g.Denied:
    pass
else:
    raise AssertionError("inconsistent no-op receipt admitted")

# This pilot is strictly its own notification namespace and cannot replace
# the legacy update-watch reconciliation or create an update candidate.
code = p.read_text(encoding="utf-8")
assert 'repos/" + REPO + "/issues"' in code
assert '"--method","POST"' in code
for forbidden in ('"PATCH"', '"DELETE"', 'gh workflow run', 'git push',
                  'gh release', 'contents: write', 'pull-requests: write'):
    assert forbidden not in code, forbidden
wf = Path(".github/workflows/issue311-r11-event-source.yml").read_text("utf-8")
assert "schedule:" not in wf and "workflow_dispatch:" not in wf
assert "cancel-in-progress: false" in wf
assert "r11-s6-issue-writer-receipt" in wf
assert "issues: write" in wf
print("R11_S6_ISSUE_WRITER_HOSTILE_PASS",len(negatives)+5,
      "NO_OLD_ISSUE_EDIT_NO_RELEASE_NO_CANDIDATE_PR")
