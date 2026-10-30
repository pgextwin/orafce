#!/usr/bin/env python3
"""Negative auth/source-kind tests, no external dispatch or tokens."""
import copy
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "app_local", Path("scripts/issue311-app-local-prepare.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
env = {
    "GITHUB_REPOSITORY": m.REPO, "GITHUB_WORKFLOW": m.WORKFLOW,
    "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
    "GITHUB_ACTOR": m.BOT, "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "1234"
}
ev = {
    "repository": {"full_name": m.REPO}, "ref": "refs/heads/main",
    "sender": {"login": m.BOT, "id": m.BOT_ID, "type": "Bot"},
    "inputs": {
        "request_id": m.REQUEST_ID, "source_run_id": "123",
        "source_head_sha": "b" * 40, "source_artifact_id": "456",
        "source_zip_sha256": "c" * 64,
        "central_request_id": "r-20261030-r06preparecoord001",
        "local_main_sha": "a" * 40
    }
}
assert m.authenticate_event(ev, env)["source_run_id"] == "123"
def reject(event, context):
    try:
        m.authenticate_event(event, context)
    except m.Denied:
        return
    raise AssertionError("unsafe App event/source accepted")
for key, value in (
    ("GITHUB_ACTOR", "ShutenOishi"),
    ("GITHUB_REPOSITORY", "pgextwin/build"),
    ("GITHUB_WORKFLOW", "Issue 311 unrelated"),
    ("GITHUB_EVENT_NAME", "push"),
    ("GITHUB_REF", "refs/tags/v1"),
    ("GITHUB_RUN_ATTEMPT", "2"),
    ("GITHUB_SHA", "d" * 40),
):
    reject(ev, dict(env, **{key: value}))
for key, value in (
    ("sender", {"login": m.BOT, "id": 1, "type": "Bot"}),
    ("repository", {"full_name": "evil/repo"}),
    ("ref", "refs/heads/dev"),
):
    bad = copy.deepcopy(ev)
    bad[key] = value
    reject(bad, env)
for key, value in (
    ("request_id", "r-20261030-r06coordactorpilot01"),
    ("source_run_id", "0"),
    ("source_artifact_id", "abc"),
    ("source_zip_sha256", "f" * 63),
    ("source_head_sha", "f" * 39),
    ("central_request_id", "r-20261029-fake"),
    ("local_main_sha", "f" * 40),
    ("mode", "PUBLISH"),
):
    bad = copy.deepcopy(ev)
    bad["inputs"][key] = value
    reject(bad, env)
body = Path("scripts/issue311-app-local-prepare.py").read_text()
for required in ("authenticate_original(", "remote_branch(", "centralOriginalOuterZipSha256Verified",
                 "publisherSourceKindAuthorized", "candidateAdmissionAuthorized"):
    assert required in body
assert "release create" not in body and "git push" not in body
print("ISSUE311_APP_BOT_LOCAL_PREPARE_NEGATIVE_TESTS_PASS")

# R07 must not inherit trusted App identity from a mere dispatch or PR.
# The only Windows build path follows the strict local original source verifier.
workflow = Path(".github/workflows/issue311-request-local-prepare.yml").read_text()
assert workflow.count("\n  r07_windows:") == 1
assert workflow.count("\n  r07_windows_required:") == 1
app_windows = workflow.split("\n  r07_windows:", 1)[1].split("\n  r07_windows_required:", 1)[0]
for guard in (
    "needs: [app_local_prepare, r08_app_signing_intent]",
    "needs.r08_app_signing_intent.result == 'success'",
    "needs.app_local_prepare.result == 'success'",
    "github.repository == 'pgextwin/orafce'",
    "github.event_name == 'workflow_dispatch'",
    "github.ref == 'refs/heads/main'",
    "github.actor == 'pgextwin-issue311-prepare-coord[bot]'",
    "github.run_attempt == 1",
    "permissions:\n      contents: read",
    "build-extension-attested.yml@5756b3c5136a8bf4db710016cfe97555f0a71c6d",
    "id-token: write", "attestations: write", "artifact-metadata: write",
):
    assert guard in app_windows, f"unsafe R07 App-Windows policy: {guard}"
summary = workflow.split("\n  r07_windows_required:", 1)[1]
for guard in (
    "always()", "needs: [app_local_prepare, r07_windows]",
    "needs.r07_windows.result", "R07_APP_LOCAL_RESULT",
    'test "$R07_APP_LOCAL_RESULT" = success || exit 1',
    "scripts/required_windows_summary.py",
):
    assert guard in summary, f"unsafe R07 required Windows summary: {guard}"
assert "release create" not in app_windows.lower()
assert "permissions:\n      contents: write" not in workflow
print("ISSUE311_R07_APP_WINDOWS_FAIL_CLOSED_NEGATIVE_PASS")

# R08 app OIDC intent must be same original workflow and strictly read-only;
# the ONLY signing job gets id-token, never a write token or Publisher grant.
for name in ("r08_app_signing_intent", "r08_signed_audit_first",
             "r08_signed_audit_second", "r08_dual_audit_join"):
    assert workflow.count("\n  "+name+":") == 1, f"missing mandatory R08 job {name}"
intent = workflow.split("\n  r08_app_signing_intent:",1)[1].split("\n  # R07-01:",1)[0]
for guard in ("needs: app_local_prepare", "needs.app_local_prepare.result == 'success'",
              "issue311-r08-app-oidc-intent.py", "issue311-app-local-prepare-original-receipt",
              "4df051757689327fa3308ed09dc999829b4a17d5"):
    assert guard in intent, f"unsigned or spoofable R08 intent: {guard}"
for name in ("r08_signed_audit_first","r08_signed_audit_second"):
    segment = workflow.split("\n  "+name+":",1)[1].split("\n  ",1)[0]
    assert segment
assert workflow.count("issue311-r08-audit-app-signed-candidate.py") == 2
assert workflow.count("issue311-r08-join-app-oidc-audits.py") == 1
assert workflow.count("pattern: orafce-pg*-windows-x64") == 2
for deny in ("release create", "gh release", "contents: write", "pull-requests: write"):
    assert deny not in workflow.lower(), f"R08 unauthorized publication path: {deny}"
print("ISSUE311_R08_APP_OIDC_TWO_REAL_SIGSTORE_JOBS_POLICY_PASS; NO_LIVE_CREDIT")
