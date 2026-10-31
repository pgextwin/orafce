#!/usr/bin/env python3
"""Deterministic candidate Writer boundary tests; never live GitHub evidence."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import urllib.error

spec = importlib.util.spec_from_file_location("candidate_writer", "scripts/issue311-r11-candidate-pr-writer.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
count = 0

def denied(fn):
    global count
    try:
        fn()
    except (g.Denied, ValueError, TypeError, KeyError):
        count += 1
    else:
        raise AssertionError("unsafe candidate input accepted")

source = {"protectedSourceVerified": True, "repository": g.REPO, "intentMode": g.MODE,
          "sourceKind": "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING", "attempt": 1,
          "originalRun": 123, "originalAfter": "a"*40, "requestId": "r11-20261031-orafce06"}
source.update({k: False for k in ("candidateWriterCalled", "appCasPerformed", "publicationAuthorized",
                                "runtimeEnabled", "scheduleRemoved", "signingPerformed")})
env = {"GITHUB_REPOSITORY": g.REPO, "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/main",
       "GITHUB_ACTOR": "ShutenOishi", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": "a"*40,
       "GITHUB_RUN_ID": "123"}
mode = {"mode": "NONPUBLISHING_READONLY", "originalRun": 123, "originalHead": "a"*40,
        "publicationAuthorized": False, "writerCalled": False}
g.bind(source, copy.deepcopy(source), mode, env)
for k, value in (("GITHUB_EVENT_NAME", "schedule"), ("GITHUB_ACTOR", "github-actions[bot]"),
                 ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_SHA", "b"*40),
                 ("GITHUB_RUN_ID", "124"), ("GITHUB_REPOSITORY", "pgextwin/hypopg"),
                 ("GITHUB_REF", "refs/tags/test")):
    changed = dict(env, **{k: value})
    denied(lambda: g.bind(source, source, mode, changed))
for k, value in (("intentMode", "REQUALIFY_EXISTING_CANDIDATE_NONPUBLISHING"),
                 ("sourceKind", "FAKE_SCHEDULE"), ("attempt", 2), ("originalRun", True),
                 ("protectedSourceVerified", False), ("publicationAuthorized", True),
                 ("runtimeEnabled", True), ("originalAfter", "bad")):
    changed = dict(source, **{k: value})
    denied(lambda: g.bind(changed, changed, mode, env))
denied(lambda: g.bind(source, dict(source, originalRun=124), mode, env))
denied(lambda: g.bind(source, source, dict(mode, writerCalled=True), env))

config = json.loads(Path("config/extension.json").read_text())
record = {"schemaVersion": 1, "extension": "orafce", "repository": g.UPSTREAM,
          "detectedAt": "fixture-only", "releasePolicy": "manual-only", "status": "candidate",
          "updates": [{"major": None, "oldRef": config["upstream"]["ref"],
              "oldVersion": config["upstream"]["version"], "ref": "VERSION_4_18_0", "version": "4.18.0",
              "commit": "b"*40, "notes": "https://github.com/orafce/orafce/releases/tag/VERSION_4_18_0",
              "pinOnly": False, "initialOnly": False}]}
stable = json.dumps([(None, "VERSION_4_18_0", "b"*40)], separators=(",", ":"))
record["candidateId"] = hashlib.sha256((g.UPSTREAM + "\n" + stable).encode()).hexdigest()[:20]
record["branch"] = "auto-candidate/" + record["candidateId"]
manifest = g.proposal(record, copy.deepcopy(record), config)
assert manifest["upstream"]["commit"] == "b"*40
assert {k: v for k, v in manifest.items() if k != "upstream"} == {k: v for k, v in config.items() if k != "upstream"}
for key, value in (("repository", "attacker/repo"), ("extension", "hypopg"),
                   ("releasePolicy", "automatic"), ("candidateId", "c"*20),
                   ("branch", "main"), ("status", "disabled"), ("firstRelease", True)):
    changed = dict(record, **{key: value})
    denied(lambda: g.proposal(changed, changed, config))
for key, value in (("major", 14), ("pinOnly", True), ("initialOnly", True),
                   ("commit", "x"*40), ("oldVersion", "99.0.0"), ("version", "4.16.0"),
                   ("ref", "VERSION_4_18_0-rc1"), ("notes", "https://attacker.invalid/")):
    changed = copy.deepcopy(record)
    changed["updates"][0][key] = value
    denied(lambda: g.proposal(changed, changed, config))
denied(lambda: g.proposal(record, dict(record, branch="auto-candidate/"+"d"*20), config))
no_op = {k: v for k, v in record.items() if k not in ("candidateId", "branch")}
no_op.update(status="no-op", updates=[])
assert g.proposal(no_op, dict(no_op, detectedAt="later"), config) is None
denied(lambda: g.proposal(dict(no_op, updates=record["updates"]), dict(no_op, updates=record["updates"]), config))

context = {"head": "a"*40, "branch": record["branch"], "manifest": g.encode(manifest).decode(),
           "message": "fixture", "title": "fixture title", "body": "fixture marker"}
for method, path, data in (("PATCH", "git/refs/heads/main", {}), ("PUT", "contents/config/extension.json", {}),
                           ("POST", "releases", {}), ("POST", "actions/workflows/windows.yml/dispatches", {}),
                           ("POST", "issues", {}), ("DELETE", "git/refs/heads/main", None),
                           ("GET", "../secrets", None), ("POST", "git/refs", {"ref": "refs/heads/main", "sha": "b"*40})):
    denied(lambda: g.allow(method, path, data, context))

class Provider:
    def __init__(self, existing=False, fault=None, lose=None, moved=False):
        self.writes = []
        self.calls = []
        self.existing, self.fault, self.lose, self.moved = existing, fault, lose, moved
    def call(self, method, path, body, ctx, receipt):
        g.allow(method, path, body, ctx)
        self.calls.append((method, path))
        if method == "POST":
            self.writes.append(path)
            if path == self.lose:
                raise OSError("fixture ACK lost")
        if path == "branches/main":
            return {"name": "main", "protected": True, "commit": {"sha": "c"*40 if self.moved else "a"*40},
                "protection": {"required_status_checks": {"checks": [{"context": "Windows required summary", "app_id": 15368}]}}}
        if path.startswith("git/matching-refs/"):
            return [{"ref": "refs/heads/"+ctx["branch"], "object": {"sha": "e"*40}}] if self.existing or "git/refs" in self.writes else []
        if path.startswith("pulls?"):
            return []
        if path == "git/commits/"+"a"*40:
            return {"sha": "a"*40, "tree": {"sha": "c"*40}}
        if path == "git/trees":
            return {"sha": "d"*40}
        if path == "git/commits":
            return {"sha": "e"*40}
        if path == "git/commits/"+"e"*40:
            return {"sha": "e"*40, "tree": {"sha": "d"*40}, "parents": [{"sha": "a"*40}]}
        if path.startswith("compare/"):
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0, "files": [{
                "filename": "evil.txt" if self.fault == "diff" else "config/extension.json",
                "status": "modified", "sha": g.blob_sha(ctx["manifest"].encode())}]}
        if path.startswith("contents/"):
            return {"type": "file", "path": "config/extension.json", "encoding": "base64",
                    "sha": g.blob_sha(ctx["manifest"].encode()),
                    "content": base64.b64encode(("tampered" if self.fault == "bytes" else ctx["manifest"]).encode()).decode()}
        if path == "git/refs":
            if self.fault == "409":
                raise urllib.error.HTTPError("fixture", 409, "conflict", {}, None)
            return {"ref": "refs/heads/"+ctx["branch"], "object": {"sha": "e"*40}}
        if path == "pulls":
            return {"number": 777}
        if path == "pulls/777":
            return {"number": 777, "draft": self.fault != "draft", "state": "open", "merged": False,
                "title": ctx["title"], "body": ctx["body"], "user": {"login": "github-actions[bot]", "type": "Bot"},
                "head": {"ref": ctx["branch"], "sha": "e"*40, "repo": {"full_name": g.REPO}},
                "base": {"ref": "main", "repo": {"full_name": g.REPO}}}
        raise AssertionError(path)

receipt = {"writes": []}
provider = Provider()
g.execute(dict(context), source, record, receipt, call=provider.call)
assert provider.writes == ["git/trees", "git/commits", "git/refs", "pulls"]
assert receipt["action"] == "DRAFT_PR_CREATED_READBACK"
existing = Provider(existing=True)
r = {"writes": []}
g.execute(dict(context), source, record, r, call=existing.call)
assert existing.writes == [] and r["action"] == "BLOCKED_EXISTING_CANDIDATE"
for fault in ("diff", "bytes", "draft"):
    provider = Provider(fault=fault)
    denied(lambda: g.execute(dict(context), source, record, {"writes": []}, call=provider.call))
    assert len(provider.writes) == len(set(provider.writes))
for endpoint in ("git/trees", "git/commits", "git/refs", "pulls"):
    provider = Provider(lose=endpoint)
    try:
        g.execute(dict(context), source, record, {"writes": []}, call=provider.call)
    except OSError:
        pass
    else:
        raise AssertionError("ACK loss must stop")
    assert provider.writes.count(endpoint) == 1 and provider.writes[-1] == endpoint
    count += 1
provider = Provider(fault="409")
try:
    g.execute(dict(context), source, record, {"writes": []}, call=provider.call)
except urllib.error.HTTPError:
    pass
else:
    raise AssertionError("409 must stop")
assert provider.writes == ["git/trees", "git/commits", "git/refs"]
count += 1
provider = Provider(moved=True)
denied(lambda: g.execute(dict(context), source, record, {"writes": []}, call=provider.call))
assert provider.writes == []

# Validate real transport one-call/no redirect behavior and UNKNOWN journaling,
# separately from the fake provider scenario above.
class LostTransport:
    calls = 0
    def open(self, request, timeout):
        self.calls += 1
        raise OSError("controlled network loss")
old_opener = g.urllib.request.build_opener
old_token = g.os.environ.get("GH_TOKEN")
old_out = g.OUT
import tempfile
try:
    transport = LostTransport()
    g.urllib.request.build_opener = lambda *a: transport
    g.os.environ["GH_TOKEN"] = "fixture-not-a-token"
    with tempfile.TemporaryDirectory() as td:
        g.OUT = Path(td) / "receipt.json"
        r = {"writes": []}
        ctx = dict(context, commit="e"*40)
        try:
            g.api("POST", "git/refs", {"ref": "refs/heads/"+ctx["branch"], "sha": "e"*40}, ctx, r)
        except OSError:
            pass
        else:
            raise AssertionError("lost transport accepted")
        assert transport.calls == 1
        assert json.loads(g.OUT.read_text())["writes"] == [{"endpoint": "git/refs", "outcome": "UNKNOWN"}]
finally:
    g.urllib.request.build_opener = old_opener
    g.OUT = old_out
    if old_token is None:
        g.os.environ.pop("GH_TOKEN", None)
    else:
        g.os.environ["GH_TOKEN"] = old_token
denied(lambda: g.NoRedirect().redirect_request(None, None, None, None, None, None))

workflow = Path(".github/workflows/issue311-r11-event-source.yml").read_text()
job = workflow.split("  candidate_pr_writer:\n", 1)[1].split("  legacy_issue_reconcile:\n", 1)[0]
assert "intent_mode == 'CANDIDATE_PR_NONPUBLISHING'" in job
assert "group: candidate-proposer-${{ github.repository }}" in job and "cancel-in-progress: false" in job
assert "persist-credentials: false" in job and "ref: " + g.CENTRAL in job
assert "      contents: write" in job and "      pull-requests: write" in job and "      actions: read" in job
assert not re.search(r"^\s+(issues|actions|id-token|attestations): write$", job, re.M)
assert "  schedule:" not in workflow and "workflow_dispatch:" not in workflow
print("R11_CANDIDATE_PR_WRITER_OFFLINE_PASS", count, "negative/fault boundaries; no live POST/CAS/409 evidence")
