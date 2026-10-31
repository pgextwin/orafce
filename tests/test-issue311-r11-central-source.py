#!/usr/bin/env python3
"""W11-A central original snapshot hostile tests: no network or signer."""
import copy
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "central", "scripts/issue311-r11-central-source.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
candidate = {
    "repository": g.REPO,
    "sourceKind": "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING",
    "candidateVerified": True, "historicalNativeWindowsVerified": True,
    "historicalOriginalZipByteRehashPerformed": False,
    "originalCentralScanRunVerified": False,
    "originalCandidatePr": 8,
    "originalCandidateMerge": "9f09147b86703efd09e1ae1d5b23bd6c92c6b9b2",
    "manifestBlob": "a"*40, "sourceHead": "b"*40,
    "originalCandidateHead": "e"*40,
    "originalNativeWindowsRun": 32,
    "originalRequiredWindowsCheckRun": 55,
    "requestId": "r11-20261031-orafce03",
    "originalOperatorRun": 21,
    "candidateWriterCalled": False, "signingPerformed": False,
    "appCasPerformed": False, "scheduleRemoved": False,
    "publicationAuthorized": False, "runtimeEnabled": False,
}
run = {
    "id": g.RUN_ID, "event": "schedule",
    "path": ".github/workflows/fleet-upstream-watch.yml",
    "head_branch": "main", "head_sha": g.RUN_HEAD,
    "run_attempt": 1, "status": "completed", "conclusion": "success",
    "repository": {"full_name": g.CENTRAL},
    "created_at": "2026-10-31T01:15:35Z",
    "updated_at": "2026-10-31T01:17:30Z",
}
artifacts = {"total_count": 2, "artifacts": [
    {"name": name, "id": ident, "digest": "sha256:" + digest,
     "expired": False, "size_in_bytes": 500,
     "workflow_run": {"id": g.RUN_ID, "head_sha": g.RUN_HEAD}}
    for name, (ident, digest) in g.ARTIFACTS.items()
]}
scan = {
    "schemaVersion": 1, "scope": "STABLE_UPSTREAM_GET_ONLY",
    "publication": "DENY", "candidatePrCreated": False,
    "fleetSize": 17, "indeterminate": 0,
    "generatedAt": "2026-10-31T01:16:15Z",
    "extensions": [
        {"repository": f"pgextwin/ext{i}", "mainSha": "c"*40,
         "status": "up-to-date"} for i in range(16)
    ] + [{"repository": g.REPO, "mainSha": "d"*40, "status": "up-to-date"}]
}
manifest = {"path": "config/extension.json", "type": "file", "sha": "a"*40}
provenance = {
    "schemaVersion": 1,
    "sourceKind": "MERGED_BOT_PR_REQUALIFICATION_NONPUBLISHING",
    "centralScheduleRun": g.RUN_ID, "centralScheduleSha": g.RUN_HEAD,
    "status": "NONPUBLISHING_REQUALIFICATION_ONLY",
    "signedArtifactsVerified": False, "publisherWriteAuthorized": False,
    "publicationAuthorized": False,
    "entries": [{
        "repository": g.REPO, "status": "MERGED_BOT_PR_REQUALIFICATION_NONPUBLISHING",
        "originalPr": 8, "originalHead": "e"*40,
        "mergedAncestor": "9f09147b86703efd09e1ae1d5b23bd6c92c6b9b2",
        "currentProtectedMain": "d"*40, "manifestBlob": "a"*40,
        "originalNativeWindowsRun": 32, "requiredCheckRun": 55,
        "verifiedOriginalNativeCi": True,
        "originalNativeZipBytesRehashed": False,
        "newOIDCSigningRun": None, "independentSigstoreAudits": 0,
        "publicationAuthorized": False, "publisherSourceKindAuthorized": False
    }] + [{"repository": f"pgextwin/other{i}"} for i in range(3)]
}
parts = [candidate, run, artifacts, scan, manifest, provenance]
ok = g.validate(*parts)
assert ok["historicalCentralOriginalJsonVerified"] is True
assert ok["historicalCentralProvenanceJsonVerified"] is True
assert ok["centralOuterZipBytesIndependentlyRehashedHere"] is False
assert ok["originalCentralRun"] == g.RUN_ID
for key in ("candidateWriterCalled", "signingPerformed", "appCasPerformed",
            "scheduleRemoved", "publicationAuthorized", "runtimeEnabled"):
    assert ok[key] is False
cases = [
    (0, ["sourceKind"], "SCHEDULE"),
    (0, ["candidateVerified"], False),
    (0, ["historicalNativeWindowsVerified"], False),
    (0, ["historicalOriginalZipByteRehashPerformed"], True),
    (0, ["originalCentralScanRunVerified"], True),
    (0, ["originalCandidatePr"], 99),
    (0, ["originalCandidateMerge"], "f"*40),
    (0, ["manifestBlob"], "bad"),
    (0, ["sourceHead"], "bad"),
    (0, ["originalOperatorRun"], 0),
    (0, ["candidateWriterCalled"], True),
    (0, ["signingPerformed"], True),
    (0, ["appCasPerformed"], True),
    (0, ["scheduleRemoved"], True),
    (0, ["publicationAuthorized"], True),
    (0, ["runtimeEnabled"], True),
    (1, ["event"], "workflow_dispatch"),
    (1, ["path"], "other.yml"),
    (1, ["run_attempt"], 2),
    (1, ["head_sha"], "f"*40),
    (1, ["conclusion"], "skipped"),
    (1, ["repository", "full_name"], "pgextwin/orafce"),
    (1, ["created_at"], "2026-10-31T03:00:00Z"),
    (2, ["total_count"], 3),
    (2, ["artifacts", 0, "id"], 0),
    (2, ["artifacts", 0, "digest"], "sha256:"+"f"*64),
    (2, ["artifacts", 0, "workflow_run", "id"], 3),
    (2, ["artifacts", 0, "expired"], True),
    (2, ["artifacts", 1, "name"], "fleet-upstream-watch"),
    (3, ["publication"], "ALLOW"),
    (3, ["candidatePrCreated"], True),
    (3, ["fleetSize"], 16),
    (3, ["indeterminate"], 1),
    (3, ["generatedAt"], "2026-10-31T04:20:00Z"),
    (3, ["extensions", 0, "repository"], g.REPO),
    (3, ["extensions", 16, "status"], "update-available"),
    (3, ["extensions", 16, "mainSha"], "bad"),
    (4, ["sha"], "f"*40),
    (4, ["path"], "config/update-watch.json"),
    (5, ["sourceKind"], "FAKE_SCHEDULE"),
    (5, ["centralScheduleRun"], 2),
    (5, ["centralScheduleSha"], "f"*40),
    (5, ["publicationAuthorized"], True),
    (5, ["signedArtifactsVerified"], True),
    (5, ["entries", 0, "repository"], "pgextwin/hypopg"),
    (5, ["entries", 0, "originalPr"], 9),
    (5, ["entries", 0, "originalHead"], "f"*40),
    (5, ["entries", 0, "mergedAncestor"], "f"*40),
    (5, ["entries", 0, "currentProtectedMain"], "f"*40),
    (5, ["entries", 0, "manifestBlob"], "f"*40),
    (5, ["entries", 0, "originalNativeWindowsRun"], 33),
    (5, ["entries", 0, "requiredCheckRun"], 56),
    (5, ["entries", 0, "verifiedOriginalNativeCi"], False),
    (5, ["entries", 0, "publisherSourceKindAuthorized"], True),
]
for idx, path, wrong in cases:
    args = copy.deepcopy(parts)
    obj = args[idx]
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = wrong
    try:
        g.validate(*args)
    except (g.Denied, ValueError, TypeError, KeyError):
        continue
    raise AssertionError(f"hostile central source admitted: {idx} {path}")
wf = Path(".github/workflows/issue311-r11-event-source.yml").read_text()
assert "schedule:" not in wf and "workflow_dispatch:" not in wf
assert "id-token: write" not in wf and "contents: write" not in wf
assert "issue311-r11-central-source.py" in wf
assert "issue311-r11-central-original.json" in wf
print("R11_CENTRAL_ORIGINAL_HOSTILE_PASS", len(cases),
      "HISTORICAL_ONLY_NO_SIGNER_NO_CAS_NO_PUBLISH")
