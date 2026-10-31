#!/usr/bin/env python3
"""R11 native candidate CI: no-op and hostile one-shot dispatch contract."""
import copy
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("native_ci","scripts/issue311-r11-native-candidate-ci.py")
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
s="a"*40; h="b"*40; cid="1"*20; name="auto-candidate/"+cid
source={"repository":g.REPO,"intentMode":"CANDIDATE_PR_NONPUBLISHING",
        "protectedSourceVerified":True,"originalRun":123,"attempt":1,
        "originalAfter":s,"requestId":"r11-20261031-orafcecp01",
        "originalRequestBlob":"c"*40,
        "publicationAuthorized":False,"runtimeEnabled":False}
mode={"mode":"NONPUBLISHING_READONLY","originalRun":123,
      "originalHead":s,"publicationAuthorized":False,"writerCalled":False}
env={"GITHUB_REPOSITORY":g.REPO,"GITHUB_EVENT_NAME":"push",
     "GITHUB_REF":"refs/heads/main","GITHUB_ACTOR":"ShutenOishi",
     "GITHUB_SHA":s,"GITHUB_RUN_ID":"123","GITHUB_RUN_ATTEMPT":"1"}
writer={"schemaVersion":1,"repository":g.REPO,"originalRun":123,
        "originalHead":s,"requestId":source["requestId"],
        "originalRequestBlob":source["originalRequestBlob"],"action":"NO_CHANGE",
        "writes":[],"publicationAuthorized":False,"runtimeEnabled":False,
        "ciDispatched":False,"writeOutcomeUnknown":False,"appCasPerformed":False}
plan={"status":"no-op","updates":[]}
assert g.evaluate(source,mode,writer,plan,{},{},{},{},{},
                  {"workflow_runs":[]},env)=="NO_CHANGE"
plan={"status":"candidate","branch":name,"candidateId":cid}
writer=dict(writer,action="DRAFT_PR_CREATED_READBACK",candidatePr=77,
            candidateHead=h,candidateBranch=name,manifestBlob="d"*40,
            writes=[{"endpoint":x,"outcome":"ACKNOWLEDGED_PENDING_READBACK"}
                for x in ("git/trees","git/commits","git/refs","pulls")])
branch={"name":"main","protected":True,"commit":{"sha":s},
       "protection":{"required_status_checks":{"checks":[
           {"context":"Windows required summary","app_id":15368}]}}}
pr={"number":77,"state":"open","draft":True,"merged":False,
    "head":{"ref":name,"sha":h,"repo":{"full_name":g.REPO}},
    "base":{"ref":"main","repo":{"full_name":g.REPO}},
    "user":{"login":"github-actions[bot]","type":"Bot"},
    "body":"<!-- pgextwin-candidate:v1:"+cid+" -->\nRequest: "+source["requestId"]+
           "\nSource Run: 123"}
ref={"ref":"refs/heads/"+name,"object":{"sha":h}}
diff={"status":"ahead","ahead_by":1,"behind_by":0,
      "files":[{"filename":"config/extension.json","status":"modified",
                "sha":"d"*40}]}
manifest={"type":"file","path":"config/extension.json","sha":"d"*40}
runs={"workflow_runs":[]}
base=[source,mode,writer,plan,branch,pr,ref,diff,manifest,runs,env]
assert g.evaluate(*base)=="DISPATCH"
count=0
def deny(params):
    global count
    try:g.evaluate(*params)
    except (g.Denied,KeyError,TypeError,ValueError):count+=1;return
    raise AssertionError("hostile candidate CI was dispatched")
for i,key,value in [
  (0,"intentMode","ISSUE_NOTICE_NONPUBLISHING"),
  (0,"publicationAuthorized",True),(0,"originalRun",999),
  (1,"writerCalled",True),(2,"candidateBranch","main"),
  (2,"candidateHead","f"*40),(2,"writeOutcomeUnknown",True),
  (2,"ciDispatched",True),(2,"candidatePr",3),
  (3,"status","no-op"),(3,"candidateId","2"*20),
  (4,"protected",False),(4,"commit",{"sha":"f"*40}),
  (5,"draft",False),(5,"state","closed"),
  (5,"user",{"login":"ShutenOishi","type":"User"}),
  (6,"object",{"sha":"f"*40}),
  (7,"ahead_by",2),(8,"sha","f"*40),
  (9,"workflow_runs",[{"head_sha":h,"event":"workflow_dispatch"}]),
  (10,"GITHUB_SHA","f"*40),(10,"GITHUB_ACTOR","github-actions[bot]")]:
    changed=copy.deepcopy(base)
    changed[i][key]=value
    deny(changed)
for method,path,body in [
    ("POST","releases",{}),("POST","actions/workflows/windows.yml/dispatches",{"ref":"main"}),
    ("POST","actions/workflows/promote.yml/dispatches",{"ref":name}),
    ("PATCH","git/refs/heads/main",{}),
    ("GET","../../secrets",None),
    ("POST","actions/workflows/windows.yml/dispatches",{"ref":name,"inputs":{"publish":True}})]:
    try:g.allowed(method,path,body)
    except (g.Denied,ValueError,TypeError):count+=1
    else:raise AssertionError("unsafe CI API endpoint accepted")
g.allowed("POST","actions/workflows/windows.yml/dispatches",{"ref":name})
assert not g.only_own_run({"head_sha":h,"head_branch":name,
          "event":"workflow_dispatch","path":".github/workflows/windows.yml",
          "run_attempt":2,"repository":{"full_name":g.REPO},
          "actor":{"login":"github-actions[bot]"}},source,writer)
assert g.only_own_run({"head_sha":h,"head_branch":name,
          "event":"workflow_dispatch","path":".github/workflows/windows.yml",
          "run_attempt":1,"repository":{"full_name":g.REPO},
          "actor":{"login":"github-actions[bot]"}},source,writer)
assert "schedule:" not in Path(".github/workflows/issue311-r11-event-source.yml").read_text()
assert "candidate_native_ci:" in Path(".github/workflows/issue311-r11-event-source.yml").read_text()
print("R11_NATIVE_CANDIDATE_CI_HOSTILE_PASS",count,
      "ONE_SHOT_NO_RELEASE_NO_FAKE_UPDATE")
