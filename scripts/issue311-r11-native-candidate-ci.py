#!/usr/bin/env python3
"""R11: create-only candidate PR -> native Windows workflow_dispatch -> CI join.

No candidate update is synthesized. No Release, merge or App CAS. The only
allowed write is a single exact-ref dispatch to windows.yml; it is never
blindly retried. CI success requires an independently fetched original Run.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO="pgextwin/orafce"
OUT=Path("r11-s6-native-candidate-ci-receipt.json")
SHA=re.compile(r"[0-9a-f]{40}\Z")
BRANCH=re.compile(r"auto-candidate/[0-9a-f]{20}\Z")

class Denied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Denied(reason)

def unique(pairs):
    value={}
    for k,v in pairs:
        need(k not in value,"duplicate JSON key")
        value[k]=v
    return value

def read(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size < 1000000,
         "original receipt missing")
    return json.loads(p.read_text("utf-8"),object_pairs_hook=unique)

def load(filename):
    spec=importlib.util.spec_from_file_location(filename.replace("-","_").replace(".","_"),
                                                "scripts/"+filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def allowed(method,path,body=None):
    if method=="GET":
        need(body is None and (path=="branches/main"
             or re.fullmatch(r"pulls/[1-9][0-9]*",path)
             or re.fullmatch(r"git/ref/heads/auto-candidate/[0-9a-f]{20}",path)
             or re.fullmatch(r"compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}",path)
             or re.fullmatch(r"contents/config/extension.json\?ref=[0-9a-f]{40}",path)
             or re.fullmatch(r"actions/workflows/windows.yml/runs\?branch=auto-candidate%2F[0-9a-f]{20}&event=workflow_dispatch&per_page=100",path)
             or re.fullmatch(r"actions/runs/[1-9][0-9]*",path)
             or re.fullmatch(r"actions/runs/[1-9][0-9]*/jobs\?per_page=100",path)),
             "GET outside native CI bridge")
    else:
        need(method=="POST" and path=="actions/workflows/windows.yml/dispatches"
             and type(body) is dict and set(body)=={"ref"}
             and type(body["ref"]) is str and BRANCH.fullmatch(body["ref"]),
             "only exact candidate Windows dispatch permitted")

def api(method,path,body=None):
    allowed(method,path,body)
    need(bool(os.getenv("GH_TOKEN")),"missing scoped token")
    req=urllib.request.Request("https://api.github.com/repos/"+REPO+"/"+path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization":"Bearer "+os.environ["GH_TOKEN"],
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "User-Agent":"pgextwin-r11-candidate-native-ci",
            "Content-Type":"application/json"})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):
            raise Denied("redirect forbidden")
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=35) as response:
        need(response.status==(204 if method=="POST" else 200), "provider HTTP status")
        if method=="POST":
            return None
        data=response.read(2000001)
        need(0<len(data)<=2000000,"oversized GET")
        return json.loads(data,object_pairs_hook=unique)

def evaluate(source,mode,writer,plan,branch,pr,ref,diff,manifest,runs,env):
    need(source.get("protectedSourceVerified") is True
         and source.get("intentMode")=="CANDIDATE_PR_NONPUBLISHING"
         and source.get("repository")==REPO
         and type(source.get("originalRun")) is int
         and source.get("attempt")==1
         and source.get("publicationAuthorized") is False
         and source.get("runtimeEnabled") is False, "untrusted operator source")
    need(mode=={"mode":"NONPUBLISHING_READONLY","originalRun":source["originalRun"],
               "originalHead":source["originalAfter"],"publicationAuthorized":False,
               "writerCalled":False}, "same-run read-only receipt mismatch")
    need(env.get("GITHUB_REPOSITORY")==REPO
         and env.get("GITHUB_EVENT_NAME")=="push"
         and env.get("GITHUB_REF")=="refs/heads/main"
         and env.get("GITHUB_ACTOR")=="ShutenOishi"
         and env.get("GITHUB_SHA")==source["originalAfter"]
         and env.get("GITHUB_RUN_ID")==str(source["originalRun"])
         and env.get("GITHUB_RUN_ATTEMPT")=="1", "not same original push")
    need(writer.get("schemaVersion")==1 and writer.get("repository")==REPO
         and writer.get("originalRun")==source["originalRun"]
         and writer.get("originalHead")==source["originalAfter"]
         and writer.get("requestId")==source["requestId"]
         and writer.get("originalRequestBlob")==source["originalRequestBlob"]
         and writer.get("publicationAuthorized") is False
         and writer.get("runtimeEnabled") is False
         and writer.get("ciDispatched") is False
         and writer.get("writeOutcomeUnknown") is False
         and writer.get("appCasPerformed") is False, "unjoined candidate Writer")
    if writer.get("action")=="NO_CHANGE":
        need(plan.get("status")=="no-op" and plan.get("updates")==[]
             and not writer.get("writes"),"false NO_CHANGE")
        return "NO_CHANGE"
    need(writer.get("action")=="DRAFT_PR_CREATED_READBACK"
         and len(writer.get("writes",[]))==4
         and [x.get("endpoint") for x in writer["writes"]]==
              ["git/trees","git/commits","git/refs","pulls"]
         and all(x.get("outcome")=="ACKNOWLEDGED_PENDING_READBACK" for x in writer["writes"]),
         "candidate create-only writes incomplete")
    head=writer.get("candidateHead")
    name=writer.get("candidateBranch")
    need(type(head) is str and SHA.fullmatch(head)
         and type(name) is str and BRANCH.fullmatch(name)
         and plan.get("status")=="candidate"
         and name==plan.get("branch")
         and name=="auto-candidate/"+plan.get("candidateId","")
         and type(writer.get("candidatePr")) is int, "candidate id/HEAD mismatch")
    need(branch.get("name")=="main" and branch.get("protected") is True
         and (branch.get("commit") or {}).get("sha")==source["originalAfter"]
         and any(c.get("context")=="Windows required summary" and c.get("app_id")==15368
             for c in (((branch.get("protection") or {}).get("required_status_checks") or {}).get("checks") or [])),
         "protected main changed")
    need(pr.get("number")==writer["candidatePr"]
         and pr.get("state")=="open" and pr.get("draft") is True
         and pr.get("merged") is False
         and pr.get("head",{}).get("ref")==name
         and pr.get("head",{}).get("sha")==head
         and pr.get("head",{}).get("repo",{}).get("full_name")==REPO
         and pr.get("base",{}).get("ref")=="main"
         and pr.get("base",{}).get("repo",{}).get("full_name")==REPO
         and pr.get("user",{}).get("login")=="github-actions[bot]"
         and pr.get("user",{}).get("type")=="Bot"
         and "<!-- pgextwin-candidate:v1:"+plan["candidateId"]+" -->" in pr.get("body","")
         and "Request: "+source["requestId"] in pr.get("body","")
         and "Source Run: "+str(source["originalRun"]) in pr.get("body",""),
         "unowned/stale candidate PR")
    need(ref.get("ref")=="refs/heads/"+name
         and (ref.get("object") or {}).get("sha")==head,"candidate branch moved")
    fs=diff.get("files",[])
    need(diff.get("status")=="ahead" and diff.get("ahead_by")==1
         and diff.get("behind_by")==0 and len(fs)==1
         and fs[0].get("filename")=="config/extension.json"
         and fs[0].get("status")=="modified"
         and fs[0].get("sha")==writer.get("manifestBlob"),"candidate diff differs")
    need(manifest.get("type")=="file"
         and manifest.get("path")=="config/extension.json"
         and manifest.get("sha")==writer["manifestBlob"],"candidate blob differs")
    need(type(runs) is dict and type(runs.get("workflow_runs")) is list
         and len(runs["workflow_runs"])<100,"CI run lookup truncated")
    need(not any(r.get("head_sha")==head and r.get("event")=="workflow_dispatch"
                 for r in runs["workflow_runs"]),"candidate CI already triggered")
    return "DISPATCH"

def only_own_run(r,source,writer):
    return (type(r) is dict and r.get("event")=="workflow_dispatch"
        and r.get("head_sha")==writer["candidateHead"]
        and r.get("head_branch")==writer["candidateBranch"]
        and r.get("path")==".github/workflows/windows.yml"
        and r.get("run_attempt")==1
        and (r.get("repository") or {}).get("full_name")==REPO
        and (r.get("actor") or {}).get("login")=="github-actions[bot]")

def main():
    receipt={"schemaVersion":1,"repository":REPO,"action":"DENIED",
             "writeOutcomeUnknown":False,"publicationAuthorized":False,
             "runtimeEnabled":False,"releaseWritten":False,"candidateMerged":False}
    try:
        source=read("r11-source/issue311-r11-source-admission.json")
        original=load("issue311-r11-event-source.py")
        need(original.main()==0 and read("issue311-r11-source-admission.json")==source,
             "source independent readmission failed")
        candidate=load("issue311-r11-candidate-pr-writer.py")
        mode=read("r11-functions/mode.json")
        candidate.bind(source,source,mode,os.environ)
        plan=read("r11-functions/candidate-plan.json")
        writer=read("r11-writer/r11-s6-candidate-pr-writer-receipt.json")
        receipt.update(originalRun=source["originalRun"],requestId=source["requestId"])
        if writer.get("action")=="NO_CHANGE":
            outcome=evaluate(source,mode,writer,plan,{}, {}, {}, {}, {},
                             {"workflow_runs":[]},os.environ)
            need(outcome=="NO_CHANGE","invalid no-op")
            receipt["action"]="NO_CHANGE"
        else:
            name=writer.get("candidateBranch")
            head=writer.get("candidateHead")
            need(type(name) is str and BRANCH.fullmatch(name)
                 and type(head) is str and SHA.fullmatch(head),"untrusted branch/head")
            listing="actions/workflows/windows.yml/runs?branch="+urllib.parse.quote(name,safe="")+"&event=workflow_dispatch&per_page=100"
            branch=api("GET","branches/main")
            pr=api("GET","pulls/"+str(writer["candidatePr"]))
            ref=api("GET","git/ref/heads/"+name)
            diff=api("GET","compare/"+source["originalAfter"]+"..."+head)
            manifest=api("GET","contents/config/extension.json?ref="+head)
            runs=api("GET",listing)
            need(evaluate(source,mode,writer,plan,branch,pr,ref,diff,manifest,runs,
                          os.environ)=="DISPATCH","candidate not qualified")
            # One final independent main/ref GET before irreversible dispatch.
            need(api("GET","branches/main")["commit"]["sha"]==source["originalAfter"]
                 and api("GET","git/ref/heads/"+name)["object"]["sha"]==head,
                 "head moved immediately before CI")
            receipt.update(action="QUARANTINED_DISPATCH_UNKNOWN",
                           candidatePr=writer["candidatePr"],
                           candidateBranch=name,candidateHead=head,
                           writeOutcomeUnknown=True)
            OUT.write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
            api("POST","actions/workflows/windows.yml/dispatches",{"ref":name})
            receipt["action"]="DISPATCH_ACK_PENDING_ORIGINAL_CI"
            # One dispatch, then bounded read-only polling. No retry of POST.
            run_id=None
            for _ in range(80):
                listed=api("GET",listing)["workflow_runs"]
                matches=[r for r in listed if only_own_run(r,source,writer)]
                need(len(matches)<=1,"multiple same-head native CI originals")
                if matches:
                    run_id=matches[0]["id"]
                    receipt["candidateCiRun"]=run_id
                    outcome=api("GET","actions/runs/"+str(run_id))
                    need(only_own_run(outcome,source,writer),"native CI run identity mismatch")
                    if outcome.get("status")=="completed":
                        need(outcome.get("conclusion")=="success",
                             "native candidate CI failed/was skipped")
                        jobs=api("GET","actions/runs/"+str(run_id)+"/jobs?per_page=100")
                        j=jobs.get("jobs")
                        need(type(j) is list and len(j)<100 and
                             any(x.get("name")=="Windows required summary" and
                                 x.get("conclusion")=="success" for x in j),
                             "required native Windows summary not successful")
                        receipt.update(action="NATIVE_CI_ORIGINAL_SUCCESS",
                                       writeOutcomeUnknown=False,
                                       candidateCiAttempt=1)
                        break
                time.sleep(45)
            need(receipt["action"]=="NATIVE_CI_ORIGINAL_SUCCESS",
                 "CI result unknown after finite observation")
        OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        print("R11_CANDIDATE_NATIVE_"+receipt["action"]+"_NONPUBLISHING")
        return 0
    except (Denied,KeyError,ValueError,TypeError,OSError,
            urllib.error.URLError,subprocess.TimeoutExpired) as exc:
        receipt["errorType"]=type(exc).__name__
        OUT.write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
        print("R11_CANDIDATE_NATIVE_CI_FAIL_CLOSED "+type(exc).__name__,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
