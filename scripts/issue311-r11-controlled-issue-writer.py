#!/usr/bin/env python3
"""R11 isolated real Issue POST using a real *existing* upstream release.

CONTROLLED_INTEGRATION only. Never assert a new stable, reconcile legacy Issues,
propose a version change, dispatch native CI or authorize publication.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = "pgextwin/orafce"
UPSTREAM = "orafce/orafce"
TAG = "VERSION_4_17_1"
TAG_SHA = "4003faf7b57d2a97d56051e06f9af677a6c42405"
COMMIT = "542aed2e0297898cc9844fede3c4452f894b37ed"
PREFIX = ".github/r11-controlled-intents/"
RID = re.compile(r"r11c-[0-9]{8}-[a-z0-9]{8,24}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
OUT = Path("r11-controlled-issue-writer-original.json")
MARKER = "<!-- pgextwin-r11-controlled-issue:"

class Denied(ValueError):
    pass

def need(ok, why):
    if not ok:
        raise Denied(why)

def unique(pairs):
    obj = {}
    for key, value in pairs:
        need(key not in obj, "duplicate JSON key")
        obj[key] = value
    return obj

def parse(value):
    return json.loads(value, object_pairs_hook=unique)

def api(repo, path, method="GET", fields=None):
    allowed = (repo == UPSTREAM and path in
               {"releases/tags/" + TAG, "git/ref/tags/" + TAG, "git/tags/" + TAG_SHA}) or (
               repo == REPO and (path in {"branches/main", "issues?state=all&per_page=100"}
               or re.fullmatch(r"compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}", path)
               or re.fullmatch(r"commits/[0-9a-f]{40}/pulls\?per_page=100", path)
               or re.fullmatch(r"pulls/[1-9][0-9]*", path)
               or re.fullmatch(r"issues/[1-9][0-9]*", path)
               or re.fullmatch(r"contents/\.github/r11-controlled-intents/r11c-[0-9]{8}-[a-z0-9]{8,24}\.json\?ref=[0-9a-f]{40}", path)
               or path == "issues"))
    need(allowed and (method == "GET" or (method == "POST" and repo == REPO
         and path == "issues" and set(fields or {}) == {"title","body"})),
         "endpoint/method outside exact allowlist")
    need(os.environ.get("GH_TOKEN"), "authenticated token required")
    cmd = ["gh","api","--method",method,"repos/"+repo+"/"+path]
    if fields:
        for k,v in fields.items():
            need(type(v) is str and len(v) < 6000, "unsafe issue field")
            cmd += ["-f",k+"="+v]
    result = subprocess.run(cmd,capture_output=True,text=True,timeout=45,check=False)
    need(result.returncode == 0 and 0 < len(result.stdout) < 2000000,
         "provider denied or response ambiguous; never retry write")
    return parse(result.stdout)

def decode_contents(item):
    """GitHub Contents API Base64 has LF line wrapping; reject all other whitespace."""
    need(type(item) is dict and item.get("encoding") == "base64"
         and type(item.get("content")) is str and bool(item["content"])
         and "\r" not in item["content"] and "\t" not in item["content"],
         "malformed GitHub Contents encoding")
    return base64.b64decode(item["content"].replace("\n", ""), validate=True)

def validate_intent(request, event, env, branch, compare, associated, pr, item):
    before, after = event.get("before"),event.get("after")
    need(all(type(s) is str and SHA.fullmatch(s) for s in (before,after))
         and before != after and before != "0"*40, "invalid source commit")
    need(env.get("GITHUB_REPOSITORY") == REPO and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_SHA") == after and env.get("GITHUB_ACTOR") == "ShutenOishi"
         and str(env.get("GITHUB_RUN_ID","")).isdigit(), "not original user main push")
    sender = event.get("sender") or {}
    need(sender.get("login") == "ShutenOishi" and sender.get("id") == 27071164
         and event.get("ref") == "refs/heads/main" and event.get("created") is False
         and event.get("deleted") is False
         and (event.get("repository") or {}).get("full_name") == REPO,
         "original sender not authenticated")
    checks = (((branch.get("protection") or {}).get("required_status_checks") or {}).get("checks") or [])
    need(branch.get("name") == "main" and branch.get("protected") is True
         and (branch.get("commit") or {}).get("sha") == after
         and any(x.get("context") == "Windows required summary" and x.get("app_id") == 15368 for x in checks),
         "protected main/required CI not established")
    files = compare.get("files") or []
    need(compare.get("status") == "ahead" and compare.get("ahead_by") == 1
         and compare.get("behind_by") == 0 and len(compare.get("commits") or []) == 1
         and len(files) == 1 and files[0].get("status") == "added"
         and files[0].get("sha") == item.get("sha"), "not a sole immutable added intent")
    path = files[0]["filename"]
    need(type(request) is dict and set(request) ==
         {"schemaVersion","requestId","mode","repository","expectedPriorMainSha",
          "upstreamRepository","tag","tagObjectSha","commit","expiresAt",
          "runtimeEnabled","publicationAuthorized"}, "unrecognized request fields")
    rid = request["requestId"]
    need(type(rid) is str and RID.fullmatch(rid)
         and path == PREFIX + rid + ".json"
         and request["schemaVersion"] == 1
         and request["mode"] == "CONTROLLED_EXISTING_RELEASE_ISSUE_ONLY"
         and request["repository"] == REPO and request["expectedPriorMainSha"] == before
         and request["upstreamRepository"] == UPSTREAM and request["tag"] == TAG
         and request["tagObjectSha"] == TAG_SHA and request["commit"] == COMMIT
         and request["runtimeEnabled"] is False and request["publicationAuthorized"] is False,
         "request not in controlled nonpublishing scope")
    expiry = datetime.strptime(request["expiresAt"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    need(datetime.now(timezone.utc) < expiry, "original intent expired")
    need(item.get("path") == path and item.get("type") == "file"
         and item.get("encoding") == "base64", "blob not from original commit")
    raw = decode_contents(item)
    need(0 < len(raw) < 8192 and parse(raw.decode("utf-8")) == request
         and hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest() == item["sha"],
         "intent blob mismatch")
    need(type(associated) is list and len(associated) == 1
         and associated[0].get("number") == pr.get("number")
         and pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == after
         and (pr.get("base") or {}).get("ref") == "main"
         and (pr.get("user") or {}).get("login") == "ShutenOishi"
         and (pr.get("merged_by") or {}).get("login") == "ShutenOishi",
         "source PR not user-origin protected merge")
    return path,item["sha"]

def verify_upstream(config, release, ref, tag):
    u = config.get("upstream") or {}
    need(config.get("name") == "orafce"
         and u.get("repository") == UPSTREAM and u.get("ref") == TAG
         and u.get("version") == "4.17.1" and u.get("commit") == COMMIT,
         "installed config does not match historic upstream")
    need(release.get("tag_name") == TAG and release.get("draft") is False
         and release.get("prerelease") is False and release.get("published_at")
         and release.get("html_url") == "https://github.com/orafce/orafce/releases/tag/" + TAG,
         "no authentic public stable Release")
    need(ref.get("ref") == "refs/tags/" + TAG
         and (ref.get("object") or {}).get("type") == "tag"
         and (ref.get("object") or {}).get("sha") == TAG_SHA
         and tag.get("tag") == TAG and tag.get("sha") == TAG_SHA
         and (tag.get("object") or {}).get("type") == "commit"
         and (tag.get("object") or {}).get("sha") == COMMIT, "upstream annotated tag mismatch")

def main():
    receipt = {"schemaVersion":1,"classification":"CONTROLLED_INTEGRATION_ONLY",
               "repository":REPO,"action":"DENY","writeOutcome":"NOT_ATTEMPTED",
               "newStableDetected":False,"legacyIssueEdited":False,"draftCreated":False,
               "runtimeEnabled":False,"publicationAuthorized":False}
    try:
        env = dict(os.environ)
        event = parse(Path(env["GITHUB_EVENT_PATH"]).read_text("utf-8"))
        before,after=event["before"],event["after"]
        need(SHA.fullmatch(before or "") and SHA.fullmatch(after or ""), "invalid original SHA")
        compare=api(REPO,"compare/"+before+"..."+after)
        files=compare.get("files") or []
        need(len(files)==1, "expected one added intent")
        path=files[0]["filename"]
        need(re.fullmatch(r"\.github/r11-controlled-intents/r11c-[0-9]{8}-[a-z0-9]{8,24}\.json",path),
             "outside controlled intent namespace")
        item=api(REPO,"contents/"+path+"?ref="+after)
        raw=decode_contents(item)
        request=parse(raw.decode("utf-8"))
        associated=api(REPO,"commits/"+after+"/pulls?per_page=100")
        need(type(associated) is list and len(associated)==1, "non-unique merged PR")
        pr=api(REPO,"pulls/"+str(associated[0]["number"]))
        validate_intent(request,event,env,api(REPO,"branches/main"),
                        compare,associated,pr,item)
        verify_upstream(parse(Path("config/extension.json").read_text("utf-8")),
                        api(UPSTREAM,"releases/tags/"+TAG),
                        api(UPSTREAM,"git/ref/tags/"+TAG),api(UPSTREAM,"git/tags/"+TAG_SHA))
        rid=request["requestId"]
        marker=MARKER+rid+" -->"
        receipt.update(requestId=rid,sourceRun=int(env["GITHUB_RUN_ID"]),
                       sourceHead=after,sourceBlob=item["sha"],upstreamTag=TAG,
                       upstreamTagObject=TAG_SHA,upstreamCommit=COMMIT)
        def ensure_absent():
            items=api(REPO,"issues?state=all&per_page=100")
            need(type(items) is list and len(items)<100, "Issue listing not exhaustive")
            need(not any(marker in str(x.get("body") or "") for x in items),
                 "replay or prior Issue detected")
        ensure_absent()
        need(api(REPO,"branches/main")["commit"]["sha"]==after, "main moved")
        ensure_absent()
        title="R11 CONTROLLED integration: existing orafce 4.17.1 (NOT an update)"
        body="\n".join([marker,"## Isolated nonpublishing Writer proof",
            "Existing genuine upstream Release: https://github.com/orafce/orafce/releases/tag/"+TAG,
            "Original protected request: `"+rid+"`",
            "Original Run: "+env["GITHUB_RUN_ID"]+"; head: `"+after+"`",
            "Pinned upstream commit: `"+COMMIT+"`",
            "**This is NOT a newly available stable, update notice, candidate or permission to publish.**"])
        receipt.update(action="QUARANTINED_ACK_UNKNOWN",writeOutcome="UNKNOWN",writeAttempts=1)
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        created=api(REPO,"issues","POST",{"title":title,"body":body})
        number=created.get("number")
        need(type(number) is int and number>0
             and created.get("title")==title and created.get("body")==body
             and (created.get("user") or {}).get("login")=="github-actions[bot]",
             "Issue write ACK not trustworthy")
        independent=api(REPO,"issues/"+str(number))
        need(independent.get("number")==number and independent.get("title")==title
             and independent.get("body")==body and independent.get("state")=="open"
             and (independent.get("user") or {}).get("login")=="github-actions[bot]",
             "Issue independent readback failed")
        receipt.update(action="CONTROLLED_ISSUE_CREATE_READBACK",
                       writeOutcome="CONFIRMED",issueNumber=number,
                       issueUrl=independent["html_url"])
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print("R11_CONTROLLED_PROVIDER_ISSUE_WRITE_READBACK_PASS_NOT_PUBLIC_E2E")
        return 0
    except (Denied,ValueError,KeyError,TypeError,OSError,UnicodeError,subprocess.TimeoutExpired) as exc:
        receipt["errorType"]=type(exc).__name__
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print("R11_CONTROLLED_FAIL_CLOSED: "+type(exc).__name__,file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
