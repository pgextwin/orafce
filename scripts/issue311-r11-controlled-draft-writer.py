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
PREFIX = ".github/r11-controlled-draft-intents/"
RID = re.compile(r"r11d-[0-9]{8}-[a-z0-9]{8,24}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
OUT = Path("r11-controlled-draft-writer-original.json")
MARKER = "<!-- pgextwin-r11-controlled-draft:"

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
    """Exact allowlist. One transport call per POST; never retry a lost ACK."""
    git_get = (re.fullmatch(r"git/commits/[0-9a-f]{40}", path)
               or re.fullmatch(r"git/trees/[0-9a-f]{40}", path)
               or re.fullmatch(r"git/ref/heads/r11-controlled-draft/r11d-[0-9]{8}-[a-z0-9]{8,24}", path)
               or re.fullmatch(r"git/matching-refs/heads/r11-controlled-draft/r11d-[0-9]{8}-[a-z0-9]{8,24}", path)
               or re.fullmatch(r"pulls/[1-9][0-9]*/files\\?per_page=100", path)
               or re.fullmatch(r"pulls\\?state=all&head=pgextwin:r11-controlled-draft/r11d-[0-9]{8}-[a-z0-9]{8,24}&per_page=100", path))
    source_get = (path == "branches/main"
                  or re.fullmatch(r"compare/[0-9a-f]{40}\\.\\.\\.[0-9a-f]{40}", path)
                  or re.fullmatch(r"commits/[0-9a-f]{40}/pulls\\?per_page=100", path)
                  or re.fullmatch(r"pulls/[1-9][0-9]*", path)
                  or re.fullmatch(r"contents/\\.github/r11-controlled-draft-intents/r11d-[0-9]{8}-[a-z0-9]{8,24}\\.json\\?ref=[0-9a-f]{40}", path))
    upstream_get = path in {"releases/tags/" + TAG, "git/ref/tags/" + TAG,
                            "git/tags/" + TAG_SHA}
    allowed = ((method == "GET" and fields is None
                and ((repo == REPO and (source_get or git_get))
                     or (repo == UPSTREAM and upstream_get)))
               or (method == "POST" and repo == REPO and path in
                   {"git/trees", "git/commits", "git/refs", "pulls"}
                   and type(fields) is dict))
    need(allowed, "outbound GitHub method or path denied")
    need(bool(os.environ.get("GH_TOKEN")), "missing scoped GitHub token")
    cmd = ["gh", "api", "--method", method, "repos/" + repo + "/" + path]
    if method == "POST":
        cmd.extend(["--input", "-"])
    raw = (None if fields is None else
           json.dumps(fields,separators=(",",":")).encode("utf-8"))
    completed = subprocess.run(cmd,input=raw,capture_output=True,timeout=45,check=False)
    need(completed.returncode == 0 and 0 < len(completed.stdout) < 2000000,
         "provider response missing/ambiguous; never retry write")
    return parse(completed.stdout.decode("utf-8"))

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
         and request["mode"] == "CONTROLLED_EXISTING_RELEASE_DRAFT_ONLY"
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

def verify_create(method, path, payload, ctx):
    """Reject arbitrary field/path write and non-create mutation before HTTP."""
    need(method == "POST" and type(payload) is dict, "only POST create allowed")
    branch = "r11-controlled-draft/" + ctx["rid"]
    if path == "git/trees":
        need(payload == {"base_tree":ctx["baseTree"],"tree":[
             {"path":ctx["proofPath"],"mode":"100644","type":"blob",
              "content":ctx["proof"]}]}, "only one isolated proof tree allowed")
    elif path == "git/commits":
        need(payload == {"message":ctx["message"],"tree":ctx["tree"],
                         "parents":[ctx["sourceHead"]]}, "untrusted draft commit")
    elif path == "git/refs":
        need(payload == {"ref":"refs/heads/"+branch,"sha":ctx["commit"]},
             "only isolated create-only ref allowed")
    elif path == "pulls":
        need(payload == {"title":ctx["title"],"head":branch,"base":"main",
                         "body":ctx["body"],"draft":True},
             "only isolated draft PR creation allowed")
    else:
        raise Denied("write endpoint denied")

def post_once(path, payload, ctx, receipt):
    verify_create("POST",path,payload,ctx)
    need(not any(x.get("path")==path for x in receipt["writes"]),
         "duplicate write endpoint")
    receipt["writes"].append({"path":path,"outcome":"UNKNOWN"})
    receipt["action"]="QUARANTINED_ACK_UNKNOWN"
    OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\\n",encoding="utf-8")
    value=api(REPO,path,"POST",payload)
    receipt["writes"][-1]["outcome"]="RESPONSE_OBSERVED_NOT_YET_READBACK"
    return value

def validate_base(main, request, source, ctx):
    need(main.get("name")=="main" and main.get("protected") is True
         and (main.get("commit") or {}).get("sha")==source
         and request["expectedPriorMainSha"]!=source, "stale or unprotected source")
    need(ctx["rid"]==request["requestId"] and
         ctx["sourceHead"]==source and
         ctx["proofPath"]=="docs/r11-controlled-draft-proof/"+ctx["rid"]+".md",
         "draft context substituted")

def main():
    receipt={"schemaVersion":1,"classification":"CONTROLLED_INTEGRATION_DRAFT_ONLY",
        "repository":REPO,"action":"DENY","writeOutcome":"NOT_ATTEMPTED",
        "writes":[],"newStableDetected":False,"legacyIssueEdited":False,
        "candidateManifestChanged":False,"nativeCiDispatched":False,
        "runtimeEnabled":False,"publicationAuthorized":False}
    try:
        env=dict(os.environ)
        event=parse(Path(env["GITHUB_EVENT_PATH"]).read_text("utf-8"))
        before,after=event["before"],event["after"]
        need(type(before) is str and type(after) is str
             and SHA.fullmatch(before) and SHA.fullmatch(after),
             "missing original commit")
        compare=api(REPO,"compare/"+before+"..."+after)
        files=compare.get("files") or []
        need(len(files)==1,"original intent is not one file")
        path=files[0]["filename"]
        need(re.fullmatch(r"\\.github/r11-controlled-draft-intents/r11d-[0-9]{8}-[a-z0-9]{8,24}\\.json",path),
             "source intent not in isolated draft namespace")
        item=api(REPO,"contents/"+path+"?ref="+after)
        request=parse(decode_contents(item).decode("utf-8"))
        associated=api(REPO,"commits/"+after+"/pulls?per_page=100")
        need(type(associated) is list and len(associated)==1,"untrusted source PR")
        pr=api(REPO,"pulls/"+str(associated[0]["number"]))
        validate_intent(request,event,env,api(REPO,"branches/main"),
                        compare,associated,pr,item)
        verify_upstream(parse(Path("config/extension.json").read_text("utf-8")),
                        api(UPSTREAM,"releases/tags/"+TAG),
                        api(UPSTREAM,"git/ref/tags/"+TAG),
                        api(UPSTREAM,"git/tags/"+TAG_SHA))
        rid=request["requestId"]
        branch="r11-controlled-draft/"+rid
        ctx={"rid":rid,"sourceHead":after,
             "proofPath":"docs/r11-controlled-draft-proof/"+rid+".md",
             "message":"test(r11): controlled historic-release isolated Draft only",
             "title":"R11 CONTROLLED DRAFT (historic orafce 4.17.1; NOT update)"}
        ctx["proof"]="\\n".join([
            "# R11 controlled Draft integration (never publish)",
            "Request: "+rid, "Original protected source: "+after,
            "Real existing upstream: "+UPSTREAM+" "+TAG+" "+COMMIT,
            "No new stable, no change to config/extension.json.",
            "No eligible candidate, no release/signature/attestation claim.",""])
        ctx["body"]="\\n".join([
            "Controlled, isolated create-only provider PR test. Not a new upstream update.",
            "Exact genuine upstream: https://github.com/orafce/orafce/releases/tag/"+TAG,
            "Source user intent: "+rid+" / main "+after,
            "This PR modifies only its own proof file. Never auto merge or publish."])
        receipt.update(requestId=rid,sourceHead=after,sourceRun=int(env["GITHUB_RUN_ID"]),
                       sourceBlob=item["sha"],upstreamTag=TAG,upstreamCommit=COMMIT)
        def absent():
            refs=api(REPO,"git/matching-refs/heads/"+branch)
            prs=api(REPO,"pulls?state=all&head=pgextwin:"+branch+"&per_page=100")
            need(refs==[] and prs==[], "existing controlled ref/PR or replay")
        absent()
        validate_base(api(REPO,"branches/main"),request,after,ctx)
        parent=api(REPO,"git/commits/"+after)
        ctx["baseTree"]=(parent.get("tree") or {}).get("sha")
        need(type(ctx["baseTree"]) is str and SHA.fullmatch(ctx["baseTree"]),
             "source tree unavailable")
        absent()
        validate_base(api(REPO,"branches/main"),request,after,ctx)
        receipt["writeOutcome"]="UNKNOWN"
        body={"base_tree":ctx["baseTree"],"tree":[
              {"path":ctx["proofPath"],"mode":"100644","type":"blob",
               "content":ctx["proof"]}]}
        tree=post_once("git/trees",body,ctx,receipt)
        ctx["tree"]=tree.get("sha")
        need(type(ctx["tree"]) is str and SHA.fullmatch(ctx["tree"]),
             "tree response unknown")
        treeback=api(REPO,"git/trees/"+ctx["tree"])
        need(treeback.get("sha")==ctx["tree"] and
             any(x.get("path")==ctx["proofPath"] and x.get("type")=="blob"
                 for x in treeback.get("tree",[])),"independent tree GET mismatch")
        commit=post_once("git/commits",{"message":ctx["message"],
               "tree":ctx["tree"],"parents":[after]},ctx,receipt)
        ctx["commit"]=commit.get("sha")
        need(type(ctx["commit"]) is str and SHA.fullmatch(ctx["commit"]),
             "commit response unknown")
        commitback=api(REPO,"git/commits/"+ctx["commit"])
        need(commitback.get("sha")==ctx["commit"] and
             (commitback.get("tree") or {}).get("sha")==ctx["tree"]
             and [x.get("sha") for x in commitback.get("parents",[])]==[after],
             "independent commit parent/tree mismatch")
        absent()
        validate_base(api(REPO,"branches/main"),request,after,ctx)
        ref=post_once("git/refs",{"ref":"refs/heads/"+branch,
                      "sha":ctx["commit"]},ctx,receipt)
        need(ref.get("ref")=="refs/heads/"+branch
             and (ref.get("object") or {}).get("sha")==ctx["commit"],
             "branch create response unknown")
        refback=api(REPO,"git/ref/heads/"+branch)
        need(refback.get("ref")=="refs/heads/"+branch
             and (refback.get("object") or {}).get("sha")==ctx["commit"],
             "independent branch readback failed")
        need(api(REPO,"pulls?state=all&head=pgextwin:"+branch+"&per_page=100")==[],
             "draft PR already exists")
        validate_base(api(REPO,"branches/main"),request,after,ctx)
        draft=post_once("pulls",{"title":ctx["title"],"head":branch,
                         "base":"main","body":ctx["body"],"draft":True},ctx,receipt)
        number=draft.get("number")
        need(type(number) is int and number>0 and draft.get("draft") is True,
             "PR create ACK unknown")
        readback=api(REPO,"pulls/"+str(number))
        changed=api(REPO,"pulls/"+str(number)+"/files?per_page=100")
        need(readback.get("number")==number and readback.get("draft") is True
             and readback.get("state")=="open"
             and (readback.get("head") or {}).get("sha")==ctx["commit"]
             and (readback.get("head") or {}).get("ref")==branch
             and (readback.get("base") or {}).get("sha")==after
             and (readback.get("user") or {}).get("login")=="github-actions[bot]"
             and type(changed) is list and len(changed)==1
             and changed[0].get("filename")==ctx["proofPath"]
             and changed[0].get("status")=="added",
             "independent nonpublishing Draft readback failed")
        for entry in receipt["writes"]:
            entry["outcome"]="INDEPENDENTLY_CONFIRMED"
        receipt.update(action="CONTROLLED_DRAFT_CREATE_READBACK",
            writeOutcome="CONFIRMED",draftNumber=number,
            draftUrl=readback.get("html_url"),branch=branch,
            draftHead=ctx["commit"],writeCount=len(receipt["writes"]))
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\\n",encoding="utf-8")
        print("R11_CONTROLLED_DRAFT_PROVIDER_CREATE_READBACK_PASS_NOT_NEW_STABLE")
        return 0
    except (Denied,ValueError,KeyError,TypeError,OSError,UnicodeError,subprocess.TimeoutExpired) as exc:
        receipt["errorType"]=type(exc).__name__
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\\n",encoding="utf-8")
        print("R11_CONTROLLED_DRAFT_DENY: "+type(exc).__name__,file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
