#!/usr/bin/env python3
"""Source-bound create-only draft candidate PR pilot; never Release or CI dispatch.

Only the orafce uniform stable-version path is supported. Recompute the plan
with immutable central code and live policy, regenerate the original source
admission, and use the legacy candidate digest/namespace/concurrency group.
Existing refs/PRs are BLOCKED, never repaired, overwritten or blindly retried.
"""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "pgextwin/orafce"
UPSTREAM = "orafce/orafce"
MODE = "CANDIDATE_PR_NONPUBLISHING"
CENTRAL = "19477b9440ce809fbadbd4fc0c7fadfd40a4a78f"
SHA = re.compile(r"[0-9a-f]{40}\Z")
CID = re.compile(r"[0-9a-f]{20}\Z")
OUT = Path("r11-s6-candidate-pr-writer-receipt.json")

class Denied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Denied(reason)

def unique(items):
    value = {}
    for k, v in items:
        need(k not in value, "duplicate JSON field")
        value[k] = v
    return value

def read(path):
    p = Path(path)
    need(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size < 1000000,
         "unsafe/missing receipt")
    return json.loads(p.read_text("utf-8"), object_pairs_hook=unique)

def encode(item):
    return (json.dumps(item, indent=2) + "\n").encode()

def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def bind(source, regenerated, mode, env):
    need(source == regenerated and source.get("protectedSourceVerified") is True
         and source.get("repository") == REPO and source.get("intentMode") == MODE
         and source.get("sourceKind") == "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
         and source.get("attempt") == 1
         and type(source.get("originalRun")) is int
         and source["originalRun"] > 0
         and SHA.fullmatch(str(source.get("originalAfter", "")))
         and all(source.get(k) is False for k in ("candidateWriterCalled",
             "appCasPerformed", "publicationAuthorized", "runtimeEnabled",
             "scheduleRemoved", "signingPerformed")), "original source not independently joined")
    need(env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == "ShutenOishi"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_SHA") == source["originalAfter"]
         and env.get("GITHUB_RUN_ID") == str(source["originalRun"]),
         "not same original operator push")
    need(mode == {"mode": "NONPUBLISHING_READONLY", "originalRun": source["originalRun"],
                  "originalHead": source["originalAfter"],
                  "publicationAuthorized": False, "writerCalled": False},
         "read-only receipt not same run/head")

def proposal(record, recomputed, config):
    # Detection timestamps can differ between independent GET observations.
    def stable(x):
        need(type(x) is dict, "plan must be an object")
        return {k: v for k, v in x.items() if k != "detectedAt"}
    need(stable(record) == stable(recomputed), "live plan changed or untrusted receipt")
    need(record.get("schemaVersion") == 1 and record.get("extension") == "orafce"
         and record.get("repository") == UPSTREAM
         and record.get("releasePolicy") == "manual-only", "plan identity/policy mismatch")
    base_keys = {"schemaVersion", "extension", "repository", "detectedAt",
                 "releasePolicy", "status", "updates"}
    if record.get("status") == "no-op":
        need(set(record) == base_keys and record.get("updates") == [], "malformed no-op")
        return None
    need(set(record) == base_keys | {"candidateId", "branch"}
         and record.get("status") == "candidate"
         and CID.fullmatch(str(record.get("candidateId", "")))
         and record.get("branch") == "auto-candidate/" + record["candidateId"],
         "unsupported candidate fields/namespace")
    updates = record.get("updates")
    need(type(updates) is list and len(updates) == 1 and type(updates[0]) is dict,
         "only one uniform orafce update is authorized")
    u = updates[0]
    need(set(u) == {"major", "oldRef", "oldVersion", "ref", "version", "commit",
                    "notes", "pinOnly", "initialOnly"}
         and u["major"] is None and u["pinOnly"] is False and u["initialOnly"] is False
         and SHA.fullmatch(str(u["commit"]))
         and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(u["version"]))
         and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(u["oldVersion"]))
         and u["ref"] == "VERSION_" + u["version"].replace(".", "_")
         and u["notes"] == "https://github.com/orafce/orafce/releases/tag/" + u["ref"],
         "not a full-SHA stable release candidate")
    need(tuple(map(int, u["version"].split("."))) > tuple(map(int, u["oldVersion"].split("."))),
         "downgrade/same-version candidate")
    stable_id = json.dumps([(None, u["ref"], u["commit"])], separators=(",", ":"))
    digest = hashlib.sha256((UPSTREAM + "\n" + stable_id).encode()).hexdigest()[:20]
    need(digest == record["candidateId"], "legacy immutable candidate digest mismatch")
    need(config.get("name") == "orafce" and config.get("upstream", {}).get("repository") == UPSTREAM
         and "perPostgresql" not in config["upstream"]
         and config.get("postgresql", {}).get("majors") == [14, 15, 16, 17, 18],
         "unsupported manifest/maintained PG set")
    old = config["upstream"]
    need(old.get("ref") == u["oldRef"] and old.get("version") == u["oldVersion"]
         and SHA.fullmatch(str(old.get("commit", ""))) and old["commit"] != u["commit"],
         "configured source changed or not pinned")
    changed = copy.deepcopy(config)
    changed["upstream"].update({k: u[k] for k in ("ref", "version", "commit")})
    return changed

def allow(method, path, body, context):
    """Exact outbound allowlist; no caller-controlled command/URL or write retry."""
    head, tree, commit = (context.get(k) for k in ("head", "tree", "commit"))
    branch = context.get("branch", "")
    need(re.fullmatch(r"auto-candidate/[0-9a-f]{20}", branch), "bad branch context")
    if method == "GET":
        need(body is None and (path == "branches/main"
             or re.fullmatch(r"git/commits/[0-9a-f]{40}", path)
             or path == "compare/" + str(head) + "..." + str(commit)
             or path == "contents/config/extension.json?ref=" + str(commit)
             or path == "git/matching-refs/heads/" + branch
             or path == "pulls?state=all&head=pgextwin:" + branch + "&per_page=100"
             or (type(context.get("pr")) is int and path == "pulls/" + str(context["pr"]))),
             "GET outside candidate allowlist")
        return
    need(method == "POST" and type(body) is dict, "only create-only POST permitted")
    if path == "git/trees":
        need(SHA.fullmatch(str(context.get("baseTree", "")))
             and body == {"base_tree": context["baseTree"], "tree": [{
                 "path": "config/extension.json", "mode": "100644", "type": "blob",
                 "content": context["manifest"]}]}, "tree must modify sole manifest")
    elif path == "git/commits":
        need(SHA.fullmatch(str(head)) and SHA.fullmatch(str(tree))
             and body == {"message": context["message"], "tree": tree, "parents": [head]},
             "commit must parent exact protected source")
    elif path == "git/refs":
        need(SHA.fullmatch(str(commit))
             and body == {"ref": "refs/heads/" + branch, "sha": commit},
             "create-only candidate ref required")
    elif path == "pulls":
        need(body == {"title": context["title"], "head": branch, "base": "main",
                      "body": context["body"], "draft": True}, "draft-only PR required")
    else:
        raise Denied("write endpoint outside exact allowlist")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Denied("API redirects are forbidden")

def api(method, path, body, context, receipt):
    allow(method, path, body, context)
    token = os.environ.get("GH_TOKEN")
    need(token, "missing scoped token")
    if method == "POST":
        # Before every write persist UNKNOWN; failed/ambiguous HTTP is never resent.
        receipt["writes"].append({"endpoint": path, "outcome": "UNKNOWN"})
        OUT.write_bytes(encode(receipt))
    request = urllib.request.Request("https://api.github.com/repos/" + REPO + "/" + path,
        data=json.dumps(body).encode() if body is not None else None, method=method,
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "pgextwin-r11-draft-candidate",
                 "Content-Type": "application/json"})
    # One transport call, no retry/backoff, no logged token or response body.
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=40) as response:
        need(response.status == (201 if method == "POST" else 200), "unexpected HTTP status")
        raw = response.read(2000001)
        need(0 < len(raw) <= 2000000, "oversized/empty API response")
        result = json.loads(raw, object_pairs_hook=unique)
    if method == "POST":
        receipt["writes"][-1]["outcome"] = "ACKNOWLEDGED_PENDING_READBACK"
        OUT.write_bytes(encode(receipt))
    return result

def command(*args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=300, check=False)
    need(p.returncode == 0, "bounded read-only recomputation failed")
    return p.stdout.strip()

def load_source_module():
    spec = importlib.util.spec_from_file_location("original_source", Path(__file__).with_name("issue311-r11-event-source.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def live_plan():
    need(command("git", "-C", ".pgextwin-build", "rev-parse", "HEAD") == CENTRAL,
         "central executable checkout not immutable")
    # The CLI success alone does not mean allowed=true.
    raw = command(sys.executable, ".pgextwin-build/scripts/fleet-control.py", "--extension", "config/extension.json",
            "--watch", "config/update-watch.json", "--repository", REPO, "--action", "candidate",
            "--candidate-policy", "config/candidate-build.json")
    policy = json.loads(raw, object_pairs_hook=unique)
    need(policy.get("allowed") is True and policy.get("mode") == "BUILD", "live policy denies candidate")
    target = str(Path(os.environ["RUNNER_TEMP"]) / "r11-writer-recomputed-plan.json")
    command(sys.executable, ".pgextwin-build/scripts/candidate-update.py", "plan", "--extension", "config/extension.json",
            "--watch", "config/update-watch.json", "--policy", "config/candidate-build.json",
            "--lifecycle", ".pgextwin-build/metadata/postgresql.json", "--output", target)
    return read(target)

def execute(context, source, record, receipt, call=api, refresh=None):
    def request(method, path, body=None):
        return call(method, path, body, context, receipt)
    def main_guard():
        main = request("GET", "branches/main")
        checks = ((main.get("protection") or {}).get("required_status_checks") or {}).get("checks") or []
        need(main.get("protected") is True and main.get("name") == "main"
             and main.get("commit", {}).get("sha") == context["head"]
             and any(c.get("context") == "Windows required summary" and c.get("app_id") == 15368 for c in checks),
             "protected main changed/missing required check")
    main_guard()
    refs = request("GET", "git/matching-refs/heads/" + context["branch"])
    prs = request("GET", "pulls?state=all&head=pgextwin:" + context["branch"] + "&per_page=100")
    need(type(refs) is list and type(prs) is list and len(prs) < 100, "truncated/invalid existing writer lookup")
    if refs or prs:
        receipt["action"] = "BLOCKED_EXISTING_CANDIDATE"
        return  # Never adopt, repair, re-open, dispatch or replace an old candidate.
    parent = request("GET", "git/commits/" + context["head"])
    need(parent.get("sha") == context["head"], "parent commit mismatch")
    context["baseTree"] = parent.get("tree", {}).get("sha")
    created = request("POST", "git/trees", {"base_tree": context["baseTree"], "tree": [{
        "path": "config/extension.json", "mode": "100644", "type": "blob", "content": context["manifest"]}]})
    context["tree"] = created.get("sha")
    created = request("POST", "git/commits", {"message": context["message"],
                      "tree": context["tree"], "parents": [context["head"]]})
    context["commit"] = created.get("sha")
    need(SHA.fullmatch(str(context["commit"])), "commit response mismatch")
    actual = request("GET", "git/commits/" + context["commit"])
    need(actual.get("sha") == context["commit"] and actual.get("tree", {}).get("sha") == context["tree"]
         and [p.get("sha") for p in actual.get("parents", [])] == [context["head"]], "created commit readback mismatch")
    diff = request("GET", "compare/" + context["head"] + "..." + context["commit"])
    files = diff.get("files", [])
    need(diff.get("status") == "ahead" and diff.get("ahead_by") == 1
         and diff.get("behind_by") == 0 and len(files) == 1
         and files[0].get("filename") == "config/extension.json"
         and files[0].get("status") == "modified"
         and files[0].get("sha") == blob_sha(context["manifest"].encode()),
         "candidate diff exceeds sole immutable manifest")
    item = request("GET", "contents/config/extension.json?ref=" + context["commit"])
    need(item.get("type") == "file" and item.get("path") == "config/extension.json"
         and item.get("encoding") == "base64"
         and base64.b64decode(item.get("content", "")) == context["manifest"].encode()
         and item.get("sha") == blob_sha(context["manifest"].encode()),
         "candidate manifest bytes/blob readback mismatch")
    if refresh:
        need(proposal(record, refresh(), read("config/extension.json")) is not None,
             "candidate ceased to be eligible")
    main_guard()
    created = request("POST", "git/refs", {"ref": "refs/heads/" + context["branch"], "sha": context["commit"]})
    need(created.get("ref") == "refs/heads/" + context["branch"]
         and created.get("object", {}).get("sha") == context["commit"], "candidate ref response mismatch")
    refs = request("GET", "git/matching-refs/heads/" + context["branch"])
    need(type(refs) is list and len(refs) == 1 and refs[0].get("ref") == created["ref"]
         and refs[0].get("object", {}).get("sha") == context["commit"], "candidate ref readback mismatch")
    main_guard()
    created = request("POST", "pulls", {"title": context["title"], "head": context["branch"],
                      "base": "main", "body": context["body"], "draft": True})
    need(type(created.get("number")) is int and created["number"] > 0, "PR response mismatch")
    context["pr"] = created["number"]
    pr = request("GET", "pulls/" + str(context["pr"]))
    need(pr.get("number") == context["pr"] and pr.get("draft") is True
         and pr.get("state") == "open" and pr.get("merged") is False
         and pr.get("body") == context["body"] and pr.get("title") == context["title"]
         and pr.get("head", {}).get("ref") == context["branch"]
         and pr.get("head", {}).get("sha") == context["commit"]
         and pr.get("head", {}).get("repo", {}).get("full_name") == REPO
         and pr.get("base", {}).get("ref") == "main"
         and pr.get("base", {}).get("repo", {}).get("full_name") == REPO
         and pr.get("user", {}).get("login") == "github-actions[bot]"
         and pr.get("user", {}).get("type") == "Bot", "draft PR readback/ownership mismatch")
    receipt.update(action="DRAFT_PR_CREATED_READBACK", candidatePr=pr["number"],
                   candidateHead=context["commit"], candidateBranch=context["branch"])

def main():
    receipt = {"schemaVersion": 1, "repository": REPO, "action": "DENIED", "writes": [],
               "publicationAuthorized": False, "runtimeEnabled": False, "scheduleRemoved": False,
               "ciDispatched": False, "appCasPerformed": False, "durableRecoveryAccepted": False, "writeOutcomeUnknown": False}
    try:
        source = read("r11-source/issue311-r11-source-admission.json")
        # Full independent GitHub source admission in THIS writer job; never
        # trust a bare success flag in a downloaded JSON document.
        need(load_source_module().main() == 0, "original source regeneration failed")
        bind(source, read("issue311-r11-source-admission.json"), read("r11-functions/mode.json"), os.environ)
        receipt.update(requestId=source["requestId"], originalRun=source["originalRun"],
                       originalHead=source["originalAfter"], originalRequestBlob=source["originalRequestBlob"])
        record = read("r11-functions/candidate-plan.json")
        changed = proposal(record, live_plan(), read("config/extension.json"))
        if changed is None:
            receipt["action"] = "NO_CHANGE"
        else:
            marker = "<!-- pgextwin-candidate:v1:" + record["candidateId"] + " -->"
            context = {"head": source["originalAfter"], "branch": record["branch"],
                "manifest": encode(changed).decode(),
                "message": "chore: propose upstream candidate\n\n" + marker,
                "title": "chore: candidate orafce " + record["updates"][0]["version"],
                "body": marker + "\nR11 source-bound draft candidate, never a Release.\n"
                    + "Request: " + source["requestId"] + "\nSource Run: " + str(source["originalRun"])
                    + "\nSource HEAD: " + source["originalAfter"]
                    + "\nCI event delivery is NOT assumed; no CI dispatch/merge/publication in this pilot.\n"}
            receipt["manifestBlob"] = blob_sha(context["manifest"].encode())
            execute(context, source, record, receipt, refresh=live_plan)
        OUT.write_bytes(encode(receipt))
        print("R11_CANDIDATE_DRAFT_PILOT_" + receipt["action"])
        return 0
    except (Denied, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        receipt["action"] = "QUARANTINED" if receipt["writes"] else "DENIED"
        receipt["writeOutcomeUnknown"] = bool(receipt["writes"])
        # Never print provider response bodies/headers/credentials.
        receipt["reason"] = "candidate boundary failed closed: " + type(exc).__name__
        OUT.write_bytes(encode(receipt))
        print("R11_CANDIDATE_PR_FAIL_CLOSED: " + type(exc).__name__, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
