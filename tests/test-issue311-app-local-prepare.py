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
    "needs: app_local_prepare",
    "needs.app_local_prepare.result == 'success'",
    "github.repository == 'pgextwin/orafce'",
    "github.event_name == 'workflow_dispatch'",
    "github.ref == 'refs/heads/main'",
    "github.actor == 'pgextwin-issue311-prepare-coord[bot]'",
    "github.run_attempt == 1",
    "permissions:\n      contents: read",
    "build-extension.yml@474ae1745c5c570956b39de3d882febad560ea7f",
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
