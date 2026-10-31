#!/usr/bin/env python3
"""R11 real-operator source-kind negative tests; no HTTP, writer or dispatch."""
import copy
import importlib.util
from pathlib import Path

s=importlib.util.spec_from_file_location("gate",Path("scripts/issue311-r11-event-source.py"))
g=importlib.util.module_from_spec(s); s.loader.exec_module(g)
before,after,blob="a"*40,"b"*40,"c"*40
rid="r11-20261031-orafce01"
path=g.PREFIX+rid+".json"
actor={"login":g.ACTOR,"id":g.ACTOR_ID,"type":"User"}
env={"GITHUB_REPOSITORY":g.REPO,"GITHUB_EVENT_NAME":"push",
     "GITHUB_REF":"refs/heads/main","GITHUB_RUN_ATTEMPT":"1",
     "GITHUB_ACTOR":g.ACTOR,"GITHUB_SHA":after,"GITHUB_RUN_ID":"123"}
event={"before":before,"after":after,"ref":"refs/heads/main",
       "repository":{"full_name":g.REPO},"sender":actor,
       "created":False,"deleted":False}
main={"name":"main","protected":True,"commit":{"sha":after},
      "protection":{"required_status_checks":{"checks":[
          {"context":"Windows required summary","app_id":15368}]}}}
compare={"status":"ahead","ahead_by":1,"behind_by":0,"commits":[{"sha":after}],
         "files":[{"filename":path,"sha":blob,"status":"added"}]}
pr={"number":89,"merged":True,"state":"closed","merge_commit_sha":after,
    "base":{"ref":"main","repo":{"full_name":g.REPO}},
    "user":actor,"merged_by":actor}
request={"schemaVersion":1,"requestId":rid,"repository":g.REPO,"sourceKind":g.KIND,
         "mode":"REQUALIFY_EXISTING_CANDIDATE_NONPUBLISHING",
         "expectedPriorMainSha":before,"candidatePr":55,"candidateMergeSha":"d"*40,
         "runtimeEnabled":False,"publisherAuthorized":False}
base=[event,env,main,compare,[pr],request,path,blob]
def decide(a):
    return g.admit(*a)
receipt=decide(base)
assert receipt["protectedSourceVerified"] is True
for k in ("candidateVerified","candidateWriterCalled","signingPerformed",
          "appCasPerformed","scheduleRemoved","publicationAuthorized","runtimeEnabled"):
    assert receipt[k] is False

cases=[
    (1,["GITHUB_EVENT_NAME"],"schedule"),
    (1,["GITHUB_ACTOR"],"github-actions[bot]"),
    (1,["GITHUB_REF"],"refs/tags/test"),
    (1,["GITHUB_RUN_ATTEMPT"],"2"),
    (1,["GITHUB_SHA"],"f"*40),
    (1,["GITHUB_RUN_ID"],"0"),
    (0,["before"],"0"*40),
    (0,["after"],"f"*40),
    (0,["created"],True),
    (0,["deleted"],True),
    (0,["sender","id"],1),
    (0,["sender","type"],"Bot"),
    (2,["protected"],False),
    (2,["commit","sha"],"f"*40),
    (2,["protection","required_status_checks","checks"],[]),
    (3,["ahead_by"],2),
    (3,["files",0,"status"],"modified"),
    (3,["files",0,"sha"],"f"*40),
    (4,[0,"merged"],False),
    (4,[0,"merge_commit_sha"],"f"*40),
    (4,[0,"merged_by","id"],1),
    (5,["mode"],"PUBLISH"),
    (5,["sourceKind"],"FAKE_SCHEDULE"),
    (5,["publisherAuthorized"],True),
    (5,["runtimeEnabled"],True),
    (5,["expectedPriorMainSha"],"f"*40),
    (5,["candidatePr"],0),
    (5,["candidateMergeSha"],"bad"),
    (5,["requestId"],"invalid"),
    (5,["schemaVersion"],2),
    (6,[],".github/workflows/update-watch.yml"),
    (7,[],"f"*40),
]
for index,chain,value in cases:
    args=copy.deepcopy(base)
    if chain:
        obj=args[index]
        for part in chain[:-1]:
            obj=obj[part]
        obj[chain[-1]]=value
    else:
        args[index]=value
    try:
        decide(args)
    except (g.Denied, ValueError, TypeError, KeyError):
        continue
    raise AssertionError("unsafe admission case: "+str((index,chain)))
# Commit-associated PR REST listing is NOT full /pulls/{number} metadata.
# The exact full PR must be fetched separately; never invent merged fields.
full=copy.deepcopy(pr)
full["head"]={"sha":"e"*40}
association={"number":pr["number"],"state":"closed",
             "merge_commit_sha":after,
             "head":{"sha":"e"*40},
             "base":{"ref":"main","repo":{"full_name":g.REPO}}}
assert g.bind_full_pr([association],full,after)==[full]
associated_negative=[
 (0,["number"],1),
 (0,["state"],"open"),
 (0,["merge_commit_sha"],"f"*40),
 (0,["head","sha"],"f"*40),
 (0,["base","ref"],"develop"),
 (0,["base","repo","full_name"],"other/repo"),
 (1,["number"],1),
 (1,["merge_commit_sha"],"f"*40),
 (1,["head","sha"],"f"*40),
 (1,["base","ref"],"develop"),
 (1,["base","repo","full_name"],"other/repo"),
 (1,["merged"],False),
]
for idx,chain,wrong in associated_negative:
    args=[copy.deepcopy(association),copy.deepcopy(full)]
    item=args[idx]
    for part in chain[:-1]:
        item=item[part]
    item[chain[-1]]=wrong
    try:
        g.bind_full_pr([args[0]],args[1],after)
    except (g.Denied,ValueError,TypeError,KeyError):
        continue
    raise AssertionError("forged associated/full PR passed "+str((idx,chain)))
for bad in ([],[association,association],[{}],None):
    try:
        g.bind_full_pr(bad,full,after)
    except (g.Denied,TypeError,ValueError,KeyError):
        continue
    raise AssertionError("ambiguous association accepted")
# Explicit allowlist remains restricted to single authenticated full PR GET.
assert "per_page=100|pulls/[1-9][0-9]*|contents/" in Path(
    "scripts/issue311-r11-event-source.py").read_text()

wf=Path(".github/workflows/issue311-r11-event-source.yml").read_text()
assert "schedule:" not in wf and "workflow_dispatch:" not in wf
assert "contents: write" not in wf and "pull-requests: write" not in wf
assert "issue311-r11-intents/*.json" in wf
assert "GH_TOKEN:" in wf
source=Path("scripts/issue311-r11-event-source.py").read_text()
for deny in ("gh release", "gh workflow run", "git push", "POST", "PUT"):
    assert deny not in source
print("R11_AUTHENTIC_SOURCE_NEGATIVES_PASS",len(cases)+len(associated_negative)+4,
      "READ_ONLY_NO_CANDIDATE_NO_SCHEDULE_REMOVAL")
