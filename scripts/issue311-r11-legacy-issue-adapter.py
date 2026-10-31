#!/usr/bin/env python3
"""R11 source-bound legacy update-watch Issue reconciliation; never publish.

Triggered only by a distinct protected, human-created immutable operator intent.
Re-check source provenance and live upstream independently. Preserve the legacy
marker; do not treat isolated R11 notice issues as existing legacy owners.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = "pgextwin/orafce"
MODE = "ISSUE_RECONCILE_NONPUBLISHING"
MARKER = "<!-- pgextwin-update-watch:v1:upstream:orafce -->"
OUT = Path("r11-source-bound-legacy-issue-receipt.json")

class Denied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Denied(reason)

def unique(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate JSON field")
        result[key] = value
    return result

def read(path):
    p = Path(path)
    need(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size < 1000000,
         "missing/untrusted receipt")
    return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=unique)

def source_module():
    p = Path("scripts/issue311-r11-event-source.py")
    spec = importlib.util.spec_from_file_location("r11_source_admission", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def central_module():
    need(Path(".pgextwin-build/scripts/reconcile-update-issue.py").is_file(),
         "pinned central reconciler absent")
    sys.path.insert(0, str(Path(".pgextwin-build/scripts").resolve()))
    spec = importlib.util.spec_from_file_location("central_issue_reconcile",
         ".pgextwin-build/scripts/reconcile-update-issue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get(path):
    need(path in ("branches/main", "issues?state=open&per_page=100")
         or re.fullmatch(r"issues/[1-9][0-9]*", path)
         or re.fullmatch(r"actions/runs/[1-9][0-9]*", path),
         "GET endpoint denied")
    need(bool(os.getenv("GH_TOKEN")), "missing scoped GitHub token")
    p = subprocess.run(["gh", "api", "--method", "GET",
                        "repos/" + REPO + "/" + path],
                       text=True, capture_output=True, timeout=40)
    need(p.returncode == 0 and 0 < len(p.stdout) < 2000000, "authenticated GET failed")
    return json.loads(p.stdout, object_pairs_hook=unique)

def validate(source, mode, detected, dry, fresh, run, branch, issues, env, central):
    need(type(source) is dict and source.get("sourceKind") ==
         "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
         and source_module().scope_allows(source, MODE)
         and source.get("repository") == REPO
         and source.get("protectedSourceVerified") is True
         and type(source.get("originalRun")) is int and source["originalRun"] > 0
         and source.get("attempt") == 1
         and source.get("publicationAuthorized") is False
         and source.get("runtimeEnabled") is False
         and source.get("scheduleRemoved") is False, "untrusted source")
    need(mode == {"mode":"NONPUBLISHING_READONLY",
                  "originalRun":source["originalRun"],
                  "originalHead":source["originalAfter"],
                  "publicationAuthorized":False,"writerCalled":False},
         "read-only job identity differs")
    need(env.get("GITHUB_REPOSITORY") == REPO and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_ACTOR") == "ShutenOishi"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_RUN_ID") == str(source["originalRun"])
         and env.get("GITHUB_SHA") == source["originalAfter"], "different original run")
    need(type(run) is dict and run.get("id") == source["originalRun"]
         and run.get("run_attempt") == 1 and run.get("event") == "push"
         and run.get("path") == ".github/workflows/issue311-r11-event-source.yml"
         and run.get("head_sha") == source["originalAfter"]
         and (run.get("actor") or {}).get("id") == 27071164
         and (run.get("repository") or {}).get("full_name") == REPO, "run provenance mismatch")
    need(branch.get("name") == "main" and branch.get("protected") is True
         and (branch.get("commit") or {}).get("sha") == source["originalAfter"]
         and any(x.get("context") == "Windows required summary" and x.get("app_id") == 15368
                 for x in (((branch.get("protection") or {}).get("required_status_checks") or {}).get("checks") or [])),
         "branch protection/main changed")
    need(type(detected) is dict and type(fresh) is dict
         and {k:v for k,v in detected.items() if k != "detectedAt"} ==
             {k:v for k,v in fresh.items() if k != "detectedAt"}
         and detected.get("extension") == "orafce"
         and detected.get("repository") == "orafce/orafce"
         and detected.get("status") in ("up-to-date","update-available"),
         "upstream state changed/indeterminate")
    need(type(issues) is list and len(issues) < 100 and
         all(type(x) is dict for x in issues), "Issue listing truncated")
    relevant = [x for x in issues if "pull_request" not in x
                and MARKER in (x.get("body") or "")]
    need(len(relevant) <= 1, "ambiguous legacy issue marker")
    for item in relevant:
        need(type(item.get("number")) is int and item.get("state") == "open"
             and (item.get("user") or {}).get("login") == "github-actions[bot]"
             and (item.get("body") or "").startswith(MARKER + "\n")
             and (item.get("title") or "").startswith("Upstream update available: orafce"),
             "unowned/forged legacy Issue")
    decision = central.decide_issue_action(detected, relevant, MARKER)
    action = decision["action"]
    owned = (decision.get("issue") or {}).get("number")
    need(type(dry) is dict and dry.get("action") == "dry-run:" + action
         and dry.get("marker") == MARKER and dry.get("issueNumber") == owned,
         "read-only dry-run disagrees with live original")
    return action, owned

def write_once(method, path, fields, receipt):
    need(method == "POST" and path == "issues" or
         method == "PATCH" and re.fullmatch(r"issues/[1-9][0-9]*",path),
         "write outside legacy Issue boundary")
    receipt["writeOutcomeUnknown"] = True
    receipt["action"] = "QUARANTINED_ACK_UNKNOWN"
    OUT.write_text(json.dumps(receipt,sort_keys=True)+"\n", encoding="utf-8")
    args = ["gh","api","--method",method,"repos/" + REPO + "/" + path]
    for name, value in fields.items():
        need(name in ("title","body","state","state_reason") and type(value) is str,
             "unexpected Issue field")
        args.extend(["-f",name+"="+value])
    p = subprocess.run(args, capture_output=True, text=True, timeout=40)
    need(p.returncode == 0, "Issue write failed/ambiguous; never retry")
    return json.loads(p.stdout, object_pairs_hook=unique)

def main():
    receipt = {"schemaVersion":1,"repository":REPO, "action":"DENIED",
               "writeOutcomeUnknown":False,"publicationAuthorized":False,
               "runtimeEnabled":False,"candidateDispatched":False}
    try:
        source=read("r11-source/issue311-r11-source-admission.json")
        need(source_module().main() == 0, "independent source readmission failed")
        need(source == read("issue311-r11-source-admission.json"), "source substitution")
        mode=read("r11-functions/mode.json")
        detected=read("r11-functions/update-result.json")
        dry=read("r11-functions/reconcile-result.json")
        p=subprocess.run([sys.executable,".pgextwin-build/scripts/check-upstream-update.py",
             "--extension-config","config/extension.json",
             "--watch-config","config/update-watch.json",
             "--output","r11-issue-live-update.json",
             "--watcher-repository","pgextwin/build",
             "--watcher-sha","19477b9440ce809fbadbd4fc0c7fadfd40a4a78f"],
             text=True,capture_output=True,timeout=180)
        need(p.returncode == 0, "independent upstream detection failed")
        fresh=read("r11-issue-live-update.json")
        central=central_module()
        run=get("actions/runs/"+str(source["originalRun"]))
        main_branch=get("branches/main")
        issues=get("issues?state=open&per_page=100")
        action, number=validate(source,mode,detected,dry,fresh,run,main_branch,issues,
                                os.environ,central)
        receipt.update(requestId=source["requestId"],originalRun=source["originalRun"],
                       originalHead=source["originalAfter"],sourceBlob=source["originalRequestBlob"],
                       intended=action,issueNumber=number)
        if action == "none":
            receipt["action"]="NO_CHANGE"
        else:
            # Recheck immediately before the one irreversible call.
            need(get("branches/main")["commit"]["sha"] == source["originalAfter"],
                 "main moved before issue write")
            now=get("issues?state=open&per_page=100")
            current, existing=validate(source,mode,detected,dry,fresh,run,
                            get("branches/main"),now,os.environ,central)
            need(current == action and existing == number, "legacy issue changed")
            if action == "create":
                title,body=central.render_extension(detected, MARKER)
                response=write_once("POST","issues",{"title":title,"body":body},receipt)
            elif action == "update":
                title,body=central.render_extension(detected, MARKER)
                response=write_once("PATCH","issues/"+str(number),
                                    {"title":title,"body":body},receipt)
            elif action == "close":
                response=write_once("PATCH","issues/"+str(number),
                                    {"state":"closed","state_reason":"completed"},receipt)
            else:
                raise Denied("unknown reconciliation action")
            need(type(response.get("number")) is int
                 and (number is None or response["number"] == number)
                 and (response.get("body") or "").startswith(MARKER+"\n")
                 and (response.get("user") or {}).get("login") == "github-actions[bot]"
                 and response.get("state") == ("closed" if action=="close" else "open"),
                 "write response mismatch")
            confirmed=get("issues/"+str(response["number"]))
            need(confirmed.get("number")==response["number"]
                 and confirmed.get("state")==response["state"]
                 and confirmed.get("body")==response.get("body"),
                 "independent Issue readback mismatch")
            receipt.update(action="ISSUE_"+action.upper()+"_READBACK",
                           issueNumber=response["number"],writeOutcomeUnknown=False)
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("R11_LEGACY_ISSUE_"+receipt["action"]+"_NONPUBLISHING")
        return 0
    except (Denied, KeyError, ValueError, TypeError, OSError, subprocess.TimeoutExpired) as e:
        receipt["errorType"]=type(e).__name__
        OUT.write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
        print("R11_LEGACY_ISSUE_FAIL_CLOSED "+type(e).__name__,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
