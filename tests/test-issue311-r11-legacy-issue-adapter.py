#!/usr/bin/env python3
"""R11 legacy Issue adapter: ownership/no-op/create/update/close hostile fixtures."""
import copy
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("legacy", "scripts/issue311-r11-legacy-issue-adapter.py")
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
class Central:
    def decide_issue_action(self, detected, issues, marker):
        assert marker==g.MARKER
        current=issues[0] if issues else None
        if detected["status"]=="up-to-date":
            return {"action":"close" if current else "none","issue":current}
        if current is None:
            return {"action":"create","issue":None}
        if detected["status"]=="update-available":
            return {"action":"update","issue":current}
        raise ValueError("indeterminate")
central=Central()
h="a"*40
source={"schemaVersion":1,"sourceKind":"R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING",
        "repository":g.REPO,"intentMode":g.MODE,"protectedSourceVerified":True,
        "originalRun":123,"originalAfter":h,"attempt":1,
        "publicationAuthorized":False,"runtimeEnabled":False,"scheduleRemoved":False}
mode={"mode":"NONPUBLISHING_READONLY","originalRun":123,"originalHead":h,
      "publicationAuthorized":False,"writerCalled":False}
detected={"schemaVersion":1,"status":"up-to-date","extension":"orafce",
          "repository":"orafce/orafce","updates":[],"detectedAt":"first"}
fresh=dict(detected, detectedAt="second")
run={"id":123,"run_attempt":1,"event":"push",
     "path":".github/workflows/issue311-r11-event-source.yml",
     "head_sha":h,"actor":{"id":27071164},
     "repository":{"full_name":g.REPO}}
branch={"name":"main","protected":True,"commit":{"sha":h},
        "protection":{"required_status_checks":{"checks":[
            {"context":"Windows required summary","app_id":15368}]}}}
env={"GITHUB_REPOSITORY":g.REPO,"GITHUB_EVENT_NAME":"push",
     "GITHUB_REF":"refs/heads/main","GITHUB_ACTOR":"ShutenOishi",
     "GITHUB_RUN_ATTEMPT":"1","GITHUB_RUN_ID":"123","GITHUB_SHA":h}
issues=[]
dry={"action":"dry-run:none","marker":g.MARKER,"issueNumber":None}
base=[source,mode,detected,dry,fresh,run,branch,issues,env,central]
assert g.validate(*base)==("none",None)
owner={"number":17,"state":"open","user":{"login":"github-actions[bot]"},
       "body":g.MARKER+"\n<!-- pgextwin-update-watch-candidate:test -->\n",
       "title":"Upstream update available: orafce 4.18.0"}
close=copy.deepcopy(base); close[7]=[owner]
close[3]={"action":"dry-run:close","marker":g.MARKER,"issueNumber":17}
assert g.validate(*close)==("close",17)
create=copy.deepcopy(base); create[2]["status"]="update-available"
create[4]["status"]="update-available"
create[3]["action"]="dry-run:create"
assert g.validate(*create)==("create",None)
update=copy.deepcopy(create); update[7]=[owner]
update[3]={"action":"dry-run:update","marker":g.MARKER,"issueNumber":17}
assert g.validate(*update)==("update",17)
def denied(args):
    try: g.validate(*args)
    except (g.Denied,ValueError,KeyError,TypeError): return
    raise AssertionError("unsafe legacy Issue modification was admitted")
count=0
for index,key,value in [
    (0,"intentMode","ISSUE_NOTICE_NONPUBLISHING"),
    (0,"protectedSourceVerified",False),(0,"runtimeEnabled",True),
    (0,"publicationAuthorized",True),(1,"originalHead","b"*40),
    (2,"status","indeterminate"),(2,"extension","hypopg"),
    (3,"action","dry-run:create"),(3,"issueNumber",999),
    (4,"repository","attacker/orafce"),(5,"event","schedule"),
    (5,"run_attempt",2),(6,"protected",False),
    (7,"state","closed"),(8,"GITHUB_ACTOR","github-actions[bot]"),
    (8,"GITHUB_RUN_ATTEMPT","2")]:
    altered=copy.deepcopy(update)
    altered[index][key]=value
    denied(altered);count+=1
for key,value in [
    ("user",{"login":"ShutenOishi"}),("title","manual user Issue"),
    ("body","Prefix\n"+g.MARKER+"\n"),("state","closed")]:
    altered=copy.deepcopy(update); altered[7][0][key]=value
    # validate guards ownership BEFORE central decision on live Issues.
    denied(altered);count+=1
duplicate=copy.deepcopy(update);duplicate[7].append(dict(owner,number=18))
denied(duplicate); count+=1
for method,path,fields in [
    ("POST","releases",{}),("PATCH","repos/main",{}),
    ("PUT","issues/17",{}),("DELETE","issues/17",{})]:
    try: g.write_once(method,path,fields,{"action":"DENIED"})
    except g.Denied: count+=1
    else: raise AssertionError("wrong outbound write permitted")
wf=Path(".github/workflows/issue311-r11-event-source.yml").read_text("utf-8")
assert "ISSUE_RECONCILE_NONPUBLISHING" in wf
assert "legacy_issue_reconcile:" in wf
assert "issues: write" in wf and "schedule:" not in wf
assert "workflow_dispatch:" not in wf
src=Path("scripts/issue311-r11-event-source.py").read_text("utf-8")
assert "ISSUE_RECONCILE_NONPUBLISHING" in src
assert "publisherAuthorized" in src
print("R11_LEGACY_ISSUE_ADAPTER_HOSTILE_PASS",count,
      "OWNED_MARKER_ONLY_NO_PUBLISH")
