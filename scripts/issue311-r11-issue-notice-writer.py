#!/usr/bin/env python3
"""R11 S6: genuine operator-bound isolated Issue notice Writer (NONPUBLISHING).

This is NOT the legacy Issue reconciler, an update to an existing Issue, or a
candidate PR Writer. No Release, App key, workflow dispatch or cron mutation.
Only one new notification in the r11 pilot namespace can be created after an
explicit distinct human ISSUE_NOTICE_NONPUBLISHING intent and a genuine
upstream-update receipt from the SAME original first-attempt protected push.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = "pgextwin/orafce"
ACTOR = "ShutenOishi"
ACTOR_ID = 27071164
WORKFLOW = ".github/workflows/issue311-r11-event-source.yml"
SOURCE_KIND = "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
MODE = "ISSUE_NOTICE_NONPUBLISHING"
MARKER_PREFIX = "<!-- pgextwin-r11-notice:v1:"
SHA = re.compile(r"[0-9a-f]{40}\\Z")

class Denied(ValueError):
    pass

def need(condition, reason):
    if not condition:
        raise Denied("R11_ISSUE_WRITER_DENY: " + reason)

def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result

def read(path):
    file = Path(path)
    need(file.is_file() and not file.is_symlink()
         and 0 < file.stat().st_size < 1000000, "missing/unsafe original receipt")
    return json.loads(file.read_text(encoding="utf-8"), object_pairs_hook=unique)

def get(path):
    need(path in ("branches/main",)
         or re.fullmatch(r"actions/runs/[1-9][0-9]*", path)
         or path == "issues?state=all&per_page=100",
         "GET outside exact read allowlist")
    need(bool(os.environ.get("GH_TOKEN")), "missing token")
    process = subprocess.run(
        ["gh", "api", "--method", "GET", "repos/" + REPO + "/" + path],
        capture_output=True, text=True, timeout=45, check=False)
    need(process.returncode == 0 and 0 < len(process.stdout) < 2000000,
         "authenticated GET unavailable")
    return json.loads(process.stdout, object_pairs_hook=unique)

def decide(source, mode, detected, dry_issue, run, main, issues, env):
    need(type(source) is dict and source.get("schemaVersion") == 1
         and source.get("repository") == REPO
         and source.get("sourceKind") == SOURCE_KIND
         and source.get("protectedSourceVerified") is True
         and source.get("intentMode") == MODE
         and source.get("attempt") == 1
         and type(source.get("originalRun")) is int and source["originalRun"] > 0
         and type(source.get("requestId")) is str
         and re.fullmatch(r"r11-[0-9]{8}-[a-z0-9]{8,32}", source["requestId"])
         and type(source.get("originalAfter")) is str
         and SHA.fullmatch(source["originalAfter"])
         and type(source.get("originalRequestBlob")) is str
         and SHA.fullmatch(source["originalRequestBlob"])
         and all(source.get(k) is False for k in
             ("candidateWriterCalled", "signingPerformed", "appCasPerformed",
              "scheduleRemoved", "publicationAuthorized", "runtimeEnabled")),
         "untrusted original human intent")
    need(type(mode) is dict and mode.get("mode") == "NONPUBLISHING_READONLY"
         and mode.get("originalRun") == source["originalRun"]
         and mode.get("originalHead") == source["originalAfter"]
         and mode.get("writerCalled") is False
         and mode.get("publicationAuthorized") is False,
         "same-run read-only outcome not joined")
    need(env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == ACTOR
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_SHA") == source["originalAfter"]
         and str(env.get("GITHUB_RUN_ID")) == str(source["originalRun"]),
         "writer not running on same original operator event")
    need(type(run) is dict and run.get("id") == source["originalRun"]
         and run.get("run_attempt") == 1 and run.get("event") == "push"
         and run.get("head_sha") == source["originalAfter"]
         and run.get("head_branch") == "main"
         and run.get("path") == WORKFLOW
         and (run.get("repository") or {}).get("full_name") == REPO
         and (run.get("actor") or {}).get("login") == ACTOR
         and (run.get("actor") or {}).get("id") == ACTOR_ID,
         "original workflow Run not authenticated")
    need(type(main) is dict and main.get("name") == "main"
         and main.get("protected") is True
         and (main.get("commit") or {}).get("sha") == source["originalAfter"]
         and any(x.get("context") == "Windows required summary" and
                 x.get("app_id") == 15368 for x in
                 (((main.get("protection") or {}).get("required_status_checks") or {})
                    .get("checks") or [])),
         "protected expected main or App15368 gate missing")
    need(type(detected) is dict and detected.get("schemaVersion") == 1
         and detected.get("extension") == "orafce"
         and detected.get("status") in ("up-to-date", "update-available")
         and detected.get("repository") is not None
         and type(dry_issue) is dict and
             str(dry_issue.get("action", "")).startswith("dry-run:"),
         "original upstream/Issue decision missing")
    need(type(issues) is list and len(issues) < 100
         and all(type(x) is dict for x in issues),
         "Issue GET truncated or malformed")
    if detected["status"] == "up-to-date":
        need(dry_issue["action"] in ("dry-run:none", "dry-run:no-op"),
             "inconsistent dry-run for unchanged upstream")
        return {"action": "NO_CHANGE", "writerCalled": False}
    need(dry_issue["action"] in ("dry-run:create", "dry-run:update"),
         "inconsistent changed-upstream Issue action")
    updates = detected.get("updates")
    need(type(updates) is list and len(updates) > 0
         and all(type(x) is dict and type(x.get("candidate")) is dict
                 and type(x["candidate"].get("version")) is str
                 and type(x["candidate"].get("ref")) is str for x in updates),
         "no exact nonempty stable upstream update")
    # Candidate identity is independent of a request ID. Do not duplicate it
    # with a second genuine operator request or after the first Issue is closed.
    digest = hashlib.sha256(json.dumps(
        {"repository": REPO, "updates": updates},
        sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    marker = MARKER_PREFIX + digest + " -->"
    matches = [x for x in issues if "pull_request" not in x and
               marker in str(x.get("body") or "")]
    need(len(matches) <= 1, "ambiguous existing notice ownership")
    if matches:
        return {"action": "ALREADY_RECORDED", "issue": matches[0].get("number"),
                "writerCalled": False, "digest": digest}
    # Isolated namespace: NEVER edit/close the legacy update-watch Issue.
    return {"action": "CREATE_NOTICE", "digest": digest, "marker": marker,
            "writerCalled": True}

def main():
    out = Path("r11-s6-issue-writer-receipt.json")
    try:
        source = read("r11-source/issue311-r11-source-admission.json")
        mode = read("r11-functions/mode.json")
        detected = read("r11-functions/update-result.json")
        dry = read("r11-functions/reconcile-result.json")
        run = get("actions/runs/" + str(source.get("originalRun", 0)))
        branch = get("branches/main")
        issues = get("issues?state=all&per_page=100")
        result = decide(source, mode, detected, dry, run, branch, issues, os.environ)
        if result["action"] == "CREATE_NOTICE":
            # This token is issues:write only; only the new marker namespace is
            # touched. No retries on lost/ambiguous POST responses.
            ver = ", ".join(str(x["candidate"]["version"]) for x in detected["updates"])
            title = "R11 nonpublishing upstream notice: orafce " + ver[:90]
            body = "\\n".join([
                result["marker"], "## R11 isolated Issue Writer pilot",
                "Source-bound operator request: `" + source["requestId"] + "`",
                "Original GitHub Run: " + str(source["originalRun"]),
                "Protected source SHA: `" + source["originalAfter"] + "`",
                "Candidate updates (read-only detected):",
                "```json", json.dumps(detected["updates"], sort_keys=True),
                "```",
                "This is a notification only; never a candidate PR, Release,",
                "publication authorization, legacy Issue edit or cron replacement."
            ])
            # Final GET is a finite pre-write guard; it does not falsely claim
            # atomicity with the OLD writer, whose marker namespace is separate.
            need(get("branches/main")["commit"]["sha"] == source["originalAfter"],
                 "protected main changed immediately before POST")
            need(not any(result["marker"] in str(x.get("body") or "")
                         for x in get("issues?state=all&per_page=100")),
                 "notice already exists immediately before POST")
            p = subprocess.run(["gh","api","--method","POST",
                                "repos/" + REPO + "/issues",
                                "-f","title=" + title,"-f","body=" + body],
                               capture_output=True,text=True,timeout=45,check=False)
            # Exactly one POST. If HTTP response is lost, leave UNKNOWN; no
            # blind retry and no claim that a GitHub Issue was created.
            need(p.returncode == 0, "Issue POST failed/ambiguous; no retry")
            created = json.loads(p.stdout, object_pairs_hook=unique)
            need(created.get("html_url") and type(created.get("number")) is int
                 and result["marker"] in (created.get("body") or ""),
                 "ambiguous Issue POST response; no retry")
            result["issue"] = created["number"]
            result["url"] = created["html_url"]
        result.update({"schemaVersion": 1, "repository": REPO,
            "originalRun": source["originalRun"], "requestId": source["requestId"],
            "publicationAuthorized": False, "candidatePrWritten": False,
            "legacyIssueEdited": False, "scheduleRemoved": False})
        out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\\n",
                       encoding="utf-8")
        print("R11_S6_ISSUE_PILOT_" + result["action"] + "_NONPUBLISHING")
        return 0
    except (Denied, KeyError, OSError, TypeError, ValueError,
            subprocess.TimeoutExpired) as exc:
        print("R11_S6_WRITER_FAIL_CLOSED " + str(exc),file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
