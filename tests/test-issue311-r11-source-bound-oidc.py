#!/usr/bin/env python3
"""W11-A offline hostile tests. All identity inputs here are synthetic, NOT acceptance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile

spec = importlib.util.spec_from_file_location("r11_oidc", "scripts/issue311-r11-source-bound-oidc.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

HEAD = "a"*40
env={"GITHUB_REPOSITORY":g.REPO,"GITHUB_EVENT_NAME":"push",
     "GITHUB_REF":"refs/heads/main","GITHUB_RUN_ATTEMPT":"1",
     "GITHUB_ACTOR":"ShutenOishi","GITHUB_SHA":HEAD,"GITHUB_RUN_ID":"9021"}
root={"id":9021,"head_sha":HEAD,"run_attempt":1,"event":"push",
      "path":g.CALLER,"actor":{"id":27071164},"status":"in_progress",
      "conclusion":None}
original={"id":g.SOURCE_RUN,"head_sha":g.SOURCE_HEAD,"head_branch":"main",
          "event":"push","path":g.SOURCE_PATH,"run_attempt":1,"status":"completed",
          "conclusion":"success","actor":{"id":27071164}}
jobs={"total_count":2,"jobs":[{"id":124424997720,"conclusion":"success"},
                              {"id":124424999428,"conclusion":"skipped"}]}
artifact={"id":g.SOURCE_ARTIFACT,"digest":"sha256:"+g.SOURCE_DIGEST}
branch={"name":"main","protected":True,"commit":{"sha":HEAD},
        "protection":{"required_status_checks":{"checks":[
             {"context":"Windows required summary","app_id":15368}]}}}
comparison={"status":"ahead","ahead_by":1,"behind_by":0,"commits":[{"sha":HEAD}]}
flags={"candidateWriterCalled":False,"signingPerformed":False,
       "appCasPerformed":False,"scheduleRemoved":False,
       "publicationAuthorized":False,"runtimeEnabled":False}
source={"schemaVersion":1,"requestId":g.REQUEST_ID,"sourceKind":g.SOURCE_KIND,
        "repository":g.REPO,"originalRun":g.SOURCE_RUN,"attempt":1,
        "originalAfter":g.SOURCE_HEAD,"mergedPr":63,"candidatePr":8,
        "candidateMergeSha":g.EXPECTED_MERGE,"protectedSourceVerified":True,
        "candidateVerified":False,**flags}
candidate={"schemaVersion":1,"requestId":g.REQUEST_ID,"sourceHead":g.SOURCE_HEAD,
           "sourceAttempt":1,"originalOperatorRun":g.SOURCE_RUN,
           "originalCandidatePr":8,"originalCandidateMerge":g.EXPECTED_MERGE,
           "centralRegistryBlob":"d6161c4bd374d3860a1c0adbeb73ed392f25a12f",
           "candidateVerified":True,"historicalNativeWindowsVerified":True,
           "historicalOriginalZipByteRehashPerformed":False,
           "originalCentralScanRunVerified":False,"newOIDCSigningRun":None,
           "independentSigstoreAudits":0,"publisherSourceKindAuthorized":False,**flags}
args=[root, original, jobs, artifact, branch, comparison, source, candidate, env]
valid=g.verify_source(*args)
assert valid["status"]=="SOURCE_BOUND_OIDC_ELIGIBLE_NONPUBLISHING"
assert valid["sourceArtifactOuterSha256"]==g.SOURCE_DIGEST
assert all(valid[k] is False for k in ("publicationAuthorized","runtimeEnabled",
                                      "appCasPerformed","scheduleRemoved"))
g.safe_signed_receipt(valid,env)

cases=[
 (0,["id"],9022),(0,["run_attempt"],2),(0,["path"],"update-watch.yml"),
 (0,["actor","id"],0),(0,["head_sha"],"b"*40),(0,["status"],"completed"),
 (1,["event"],"schedule"),(1,["path"],"update-watch.yml"),
 (1,["head_sha"],"b"*40),(1,["run_attempt"],2),
 (1,["actor","id"],0),(1,["conclusion"],"failure"),
 (2,["total_count"],1),(2,["jobs",0,"conclusion"],"failure"),
 (2,["jobs",1,"conclusion"],"success"),
 (3,["id"],1),(3,["digest"],"sha256:"+"0"*64),
 (4,["protected"],False),(4,["commit","sha"],"b"*40),
 (4,["protection","required_status_checks","checks",0,"app_id"],1),
 (5,["status"],"diverged"),(5,["ahead_by"],21),(5,["behind_by"],1),
 (5,["commits",0,"sha"],"b"*40),
 (6,["requestId"],"forged"),(6,["sourceKind"],"schedule"),
 (6,["originalRun"],5),(6,["attempt"],2),
 (6,["originalAfter"],"b"*40),(6,["candidatePr"],9),
 (6,["candidateVerified"],True),(6,["protectedSourceVerified"],False),
 (6,["candidateWriterCalled"],True),(6,["signingPerformed"],True),
 (6,["appCasPerformed"],True),(6,["scheduleRemoved"],True),
 (6,["publicationAuthorized"],True),(6,["runtimeEnabled"],True),
 (7,["candidateVerified"],False),(7,["sourceHead"],"b"*40),
 (7,["sourceAttempt"],2),(7,["originalCandidatePr"],9),
 (7,["originalCandidateMerge"],"b"*40),
 (7,["centralRegistryBlob"],"b"*40),
 (7,["historicalNativeWindowsVerified"],False),
 (7,["historicalOriginalZipByteRehashPerformed"],True),
 (7,["originalCentralScanRunVerified"],True),
 (7,["newOIDCSigningRun"],7),(7,["independentSigstoreAudits"],2),
 (7,["publisherSourceKindAuthorized"],True),
 (8,["GITHUB_EVENT_NAME"],"schedule"),(8,["GITHUB_RUN_ATTEMPT"],"2"),
 (8,["GITHUB_ACTOR"],"someone-else"),(8,["GITHUB_SHA"],g.SOURCE_HEAD)
]
for pos,keys,value in cases:
    bad=copy.deepcopy(args)
    item=bad[pos]
    for key in keys[:-1]:
        item=item[key]
    item[keys[-1]]=value
    try: g.verify_source(*bad)
    except (g.Denied,ValueError,KeyError,TypeError): continue
    raise AssertionError("hostile source admitted: "+str((pos,keys)))

for key,value in [("sourceRun",8),("sourceArtifact",5),("sourceHead","0"*40),
                  ("newSigningHead","a"*39),("publicationAuthorized",True),
                  ("runtimeEnabled",True),("appCasPerformed",True),
                  ("scheduleRemoved",True)]:
    bad=dict(valid);bad[key]=value
    try: g.safe_signed_receipt(bad,env)
    except (g.Denied,ValueError,KeyError,TypeError): continue
    raise AssertionError("hostile signer intent admitted: "+key)

os.environ["GITHUB_RUN_ID"]=env["GITHUB_RUN_ID"]
os.environ["GITHUB_SHA"]=env["GITHUB_SHA"]
base={"schemaVersion":1,"result":"TWO_REQUIRED_REAL_AUDIT_JOBS_NONPUBLISHING",
      "sourceRun":g.SOURCE_RUN,"sourceArtifact":g.SOURCE_ARTIFACT,
      "newSigningRun":9021,"newSigningHead":HEAD,
      "job":"independent_audit","auditInstance":"first",
      "signedOriginalByMajor":{str(i):{
          "zipSha256":"1"*64,"spdxSha256":"2"*64,"grypeSha256":"3"*64}
          for i in range(14,19)},
      "cryptographicVerification":"REAL_GH_SIGSTORE",
      "publicationAuthorized":False,"runtimeEnabled":False,
      "appCasPerformed":False,"scheduleRemoved":False}
with tempfile.TemporaryDirectory() as d:
    old=Path.cwd()
    os.chdir(d)
    try:
        a=Path("first.json");b=Path("second.json")
        a.write_text(json.dumps(base),encoding="utf-8")
        second=dict(base);second["auditInstance"]="second"
        b.write_text(json.dumps(second),encoding="utf-8")
        g.join_main(a,b)
        joined=json.loads(Path("r11-source-bound-dual-sigstore.json").read_text())
        assert joined["independentSigstoreAudits"]==2
        assert joined["publicationAuthorized"] is False
        for field,value in [("sourceRun",1),("newSigningRun",1),
                            ("publicationAuthorized",True),
                            ("cryptographicVerification","FAKE"),
                            ("signedOriginalByMajor",{}),("auditInstance","first")]:
            bad=copy.deepcopy(second);bad[field]=value
            b.write_text(json.dumps(bad),encoding="utf-8")
            try: g.join_main(a,b)
            except (g.Denied,ValueError,KeyError,TypeError): continue
            raise AssertionError("forged dual-audit join admitted "+field)
    finally: os.chdir(old)

wf=Path(".github/workflows/issue311-r11-source-bound-signed.yml").read_text()
assert "schedule:" not in wf and "workflow_dispatch:" not in wf
assert "contents: write" not in wf and "pull-requests: write" not in wf
assert "issues: write" not in wf and "actions: write" not in wf
assert "signed_windows:" in wf and "independent_audit:" in wf and "join:" in wf
assert g.SIGNER_SHA in wf and g.SOURCE_RUN == 41163177685

# The authentic Actions outer artifact is named orafce-pg17-windows-x64,
# but download-artifact extracts VERSION-prefixed inner files.
expected_files=g.signed_file_names("VERSION_4_17_1")
assert len(expected_files)==15
assert "orafce-VERSION_4_17_1-pg17-windows-x64.zip" in expected_files
assert "orafce-VERSION_4_17_1-pg17-windows-x64.spdx.json" in expected_files
assert "orafce-VERSION_4_17_1-pg17-windows-x64.vulnerabilities.json" in expected_files
assert "orafce-pg17-windows-x64.zip" not in expected_files
for wrong in ("../VERSION_4_17_1","VERSION_4_17_1/../bad","v4.17.1","VERSION_4_17_1.zip",42):
    try: g.signed_file_names(wrong)
    except (g.Denied, TypeError, ValueError): continue
    raise AssertionError("unsafe signed file prefix accepted")

print("R11_SOURCE_BOUND_HOSTILE_PASS",len(cases)+8+6,
      "synthetic_only_NO_SCHEDULE_NO_APP_CAS_NO_PUBLISH")
