#!/usr/bin/env python3
"""R11: independent read-only operator intent source, never schedule/PUBLISH."""
import base64
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
KIND = "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
PREFIX = ".github/issue311-r11-intents/"
SHA = re.compile(r"[0-9a-f]{40}\Z")
RID = re.compile(r"r11-[0-9]{8}-[a-z0-9]{8,32}\Z")

class Denied(ValueError):
    pass

def need(ok, why):
    if not ok:
        raise Denied(why)

def decode(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)

def admit(event, env, branch, compare, prs, request, path, blob):
    before, after = event.get("before"), event.get("after")
    need(all(isinstance(x, str) and SHA.fullmatch(x) for x in (before, after))
         and before != "0"*40 and before != after, "bad original SHA")
    need(env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_ACTOR") == ACTOR
         and env.get("GITHUB_SHA") == after
         and str(env.get("GITHUB_RUN_ID", "")).isdecimal()
         and int(env["GITHUB_RUN_ID"]) > 0, "not authenticated original push")
    sender = event.get("sender") or {}
    need(event.get("ref") == "refs/heads/main"
         and event.get("created") is False and event.get("deleted") is False
         and (event.get("repository") or {}).get("full_name") == REPO
         and sender.get("login") == ACTOR and sender.get("id") == ACTOR_ID
         and sender.get("type") == "User", "forged push actor")
    checks = (((branch.get("protection") or {}).get("required_status_checks") or {}).get("checks") or [])
    need(branch.get("name") == "main" and branch.get("protected") is True
         and (branch.get("commit") or {}).get("sha") == after
         and any(c.get("context") == "Windows required summary"
                 and c.get("app_id") == 15368 for c in checks), "unprotected main")
    need(compare.get("status") == "ahead" and compare.get("ahead_by") == 1
         and compare.get("behind_by") == 0
         and len(compare.get("commits", [])) == 1
         and compare["commits"][0].get("sha") == after, "not one merge commit")
    files = compare.get("files") or []
    need(len(files) == 1 and files[0].get("filename") == path
         and files[0].get("status") == "added"
         and files[0].get("sha") == blob, "extra or modified files")
    need(isinstance(prs, list) and len(prs) == 1, "ambiguous PR")
    pr = prs[0]
    need(pr.get("merged") is True and pr.get("state") == "closed"
         and pr.get("merge_commit_sha") == after
         and (pr.get("base") or {}).get("ref") == "main"
         and (pr.get("base") or {}).get("repo", {}).get("full_name") == REPO
         and (pr.get("user") or {}).get("login") == ACTOR
         and (pr.get("user") or {}).get("id") == ACTOR_ID
         and (pr.get("merged_by") or {}).get("login") == ACTOR
         and (pr.get("merged_by") or {}).get("id") == ACTOR_ID, "untrusted PR provenance")
    need(set(request) == {"schemaVersion","requestId","repository","sourceKind",
          "mode","expectedPriorMainSha","candidatePr","candidateMergeSha",
          "runtimeEnabled","publisherAuthorized"}, "unrecognized request fields")
    rid = request["requestId"]
    need(isinstance(rid, str) and RID.fullmatch(rid)
         and path == PREFIX + rid + ".json"
         and type(request["schemaVersion"]) is int and request["schemaVersion"] == 1
         and request["repository"] == REPO and request["sourceKind"] == KIND
         and request["mode"] == "REQUALIFY_EXISTING_CANDIDATE_NONPUBLISHING"
         and request["expectedPriorMainSha"] == before
         and type(request["candidatePr"]) is int and request["candidatePr"] > 0
         and isinstance(request["candidateMergeSha"], str)
         and SHA.fullmatch(request["candidateMergeSha"])
         and request["runtimeEnabled"] is False
         and request["publisherAuthorized"] is False, "invalid nonpublishing source")
    return {"schemaVersion":1, "sourceKind":KIND, "requestId":rid, "repository":REPO,
            "originalRun":int(env["GITHUB_RUN_ID"]), "attempt":1,
            "originalBefore":before, "originalAfter":after, "mergedPr":pr["number"],
            "originalRequestBlob":blob, "candidatePr":request["candidatePr"],
            "candidateMergeSha":request["candidateMergeSha"],
            "protectedSourceVerified":True, "candidateVerified":False,
            "candidateWriterCalled":False, "signingPerformed":False,
            "appCasPerformed":False, "scheduleRemoved":False,
            "publicationAuthorized":False, "runtimeEnabled":False}

def get(endpoint):
    need(re.fullmatch(r"(branches/main|compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}|commits/[0-9a-f]{40}/pulls\?per_page=100|contents/\.github/issue311-r11-intents/r11-[0-9]{8}-[a-z0-9]{8,32}\.json\?ref=[0-9a-f]{40})", endpoint), "GET not allowlisted")
    need(bool(os.environ.get("GH_TOKEN")), "missing scoped GET credentials")
    p = subprocess.run(["gh","api","--method","GET","repos/"+REPO+"/"+endpoint],
                       capture_output=True, text=True, timeout=40, check=False)
    need(p.returncode == 0 and 0 < len(p.stdout) < 2000000, "GitHub GET failure")
    return decode(p.stdout)

def main():
    try:
        raw = Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes()
        need(0 < len(raw) < 20000, "invalid original payload length")
        event = decode(raw.decode("utf-8"))
        before, after = event["before"], event["after"]
        need(all(isinstance(x,str) and SHA.fullmatch(x) for x in (before,after)),
             "bad initial push identities")
        compare = get("compare/"+before+"..."+after)
        files = compare.get("files") or []
        need(len(files)==1, "exactly one added intent required")
        path = files[0]["filename"]
        need(isinstance(path,str) and re.fullmatch(r"\.github/issue311-r11-intents/r11-[0-9]{8}-[a-z0-9]{8,32}\.json",path), "path not allowlisted")
        item = get("contents/"+path+"?ref="+after)
        need(item.get("path")==path and item.get("type")=="file"
             and item.get("encoding")=="base64", "bad original source")
        original = base64.b64decode(item["content"])
        need(0 < len(original) < 8192, "invalid immutable source length")
        blob = hashlib.sha1(b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest()
        need(blob==item.get("sha"), "original content blob mismatch")
        receipt = admit(event, os.environ, get("branches/main"), compare,
                        get("commits/"+after+"/pulls?per_page=100"),
                        decode(original.decode("utf-8")), path, blob)
        Path("issue311-r11-source-admission.json").write_text(
            json.dumps(receipt, sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
        print("R11_AUTHENTIC_OPERATOR_SOURCE_ONLY; CANDIDATE_AND_PUBLISH_DENY")
        return 0
    except (Denied, OSError, ValueError, KeyError, TypeError, UnicodeError,
            subprocess.TimeoutExpired) as exc:
        print("R11_SOURCE_DENY: "+str(exc), file=sys.stderr)
        return 2
if __name__ == "__main__":
    raise SystemExit(main())
