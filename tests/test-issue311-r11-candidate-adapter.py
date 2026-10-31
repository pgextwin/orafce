#!/usr/bin/env python3
"""W11-A candidate adapter hostile offline tests; no credentials or network."""
import copy
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("r11_adapter",
    "scripts/issue311-r11-candidate-adapter.py")
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

head="b"*40
source={"sourceKind":"R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING",
 "repository":g.REPO,"protectedSourceVerified":True,"attempt":1,
 "originalRun":11,"requestId":"r11-20261031-orafce01",
 "originalBefore":"a"*40,"originalAfter":head,
 "originalRequestBlob":"c"*40,"candidatePr":8,
 "candidateMergeSha":"d"*40,"candidateVerified":False,
 "candidateWriterCalled":False,"signingPerformed":False,
 "appCasPerformed":False,"scheduleRemoved":False,
 "publicationAuthorized":False,"runtimeEnabled":False}
row={"repository":g.REPO,"pr":8,"candidateHead":"e"*40,
 "mergeSha":"d"*40,"nativeRun":23,"manifestBlob":"f"*40}
registry={"schemaVersion":1,"publication":"DENY","entries":[row]}
central={"name":"main","protected":True,"commit":{"sha":"1"*40}}
central_file={"path":"metadata/merged-candidate-requalification.json",
 "type":"file","sha":g.REGISTRY_BLOB}
proof={"repository":g.REPO,
 "status":"MERGED_BOT_PR_REQUALIFICATION_NONPUBLISHING",
 "originalPr":8,"originalHead":row["candidateHead"],
 "mergedAncestor":row["mergeSha"],"manifestBlob":row["manifestBlob"],
 "originalNativeWindowsRun":23,"currentProtectedMain":head,
 "verifiedOriginalNativeCi":True,"requiredCheckRun":71,
 "originalNativeZipBytesRehashed":False,"publicationAuthorized":False,
 "publisherSourceKindAuthorized":False}
artifacts={"total_count":5,"artifacts":[
 {"name":f"orafce-pg{n}-windows-x64","id":100+n,
  "digest":"sha256:"+"2"*64,"expired":False,"size_in_bytes":1024,
  "workflow_run":{"id":23,"head_sha":row["candidateHead"]}}
 for n in (14,15,16,17,18)]}
base=[source,row,registry,central,central_file,proof,artifacts]
def verify(parts):
 return g.validate(*parts)
receipt=verify(base)
assert receipt["candidateVerified"] is True
assert receipt["historicalNativeWindowsVerified"] is True
assert receipt["historicalOriginalZipByteRehashPerformed"] is False
assert receipt["originalCentralScanRunVerified"] is False
for key in ("candidateWriterCalled","signingPerformed","appCasPerformed",
            "scheduleRemoved","publicationAuthorized","runtimeEnabled",
            "publisherSourceKindAuthorized"):
 assert receipt[key] is False

cases=[
 (0,["sourceKind"],"FAKE_SCHEDULE"),
 (0,["repository"],"pgextwin/build"),
 (0,["protectedSourceVerified"],False),
 (0,["attempt"],2),
 (0,["originalRun"],0),
 (0,["requestId"],None),
 (0,["originalBefore"],"wrong"),
 (0,["originalAfter"],"wrong"),
 (0,["originalRequestBlob"],"wrong"),
 (0,["candidatePr"],99),
 (0,["candidateMergeSha"],"0"*40),
 (0,["candidateVerified"],True),
 (0,["candidateWriterCalled"],True),
 (0,["signingPerformed"],True),
 (0,["appCasPerformed"],True),
 (0,["scheduleRemoved"],True),
 (0,["publicationAuthorized"],True),
 (0,["runtimeEnabled"],True),
 (1,["pr"],9),
 (1,["nativeRun"],30),
 (2,["schemaVersion"],2),
 (2,["publication"],"ALLOW"),
 (2,["entries"],[]),
 (3,["protected"],False),
 (3,["commit","sha"],"wrong"),
 (4,["sha"],"f"*40),
 (4,["path"],"malicious.json"),
 (5,["status"],"MERGED_SIGNING_AUTHORIZED"),
 (5,["originalPr"],9),
 (5,["originalHead"],"f"*40),
 (5,["mergedAncestor"],"0"*40),
 (5,["manifestBlob"],"0"*40),
 (5,["originalNativeWindowsRun"],1),
 (5,["currentProtectedMain"],"f"*40),
 (5,["verifiedOriginalNativeCi"],False),
 (5,["requiredCheckRun"],0),
 (5,["originalNativeZipBytesRehashed"],True),
 (5,["publicationAuthorized"],True),
 (5,["publisherSourceKindAuthorized"],True),
 (6,["total_count"],4),
 (6,["artifacts",0,"expired"],True),
 (6,["artifacts",0,"digest"],"fake"),
 (6,["artifacts",0,"name"],"orafce-pg15-windows-x64"),
 (6,["artifacts",0,"workflow_run","id"],777),
 (6,["artifacts",0,"workflow_run","head_sha"],"f"*40),
 (6,["artifacts",0,"size_in_bytes"],0),
 (6,["artifacts",0,"id"],0),
]
for index,chain,value in cases:
 args=copy.deepcopy(base)
 item=args[index]
 for field in chain[:-1]:
  item=item[field]
 item[chain[-1]]=value
 try:
  verify(args)
 except (g.Denied,ValueError,TypeError,KeyError):
  continue
 raise AssertionError("unsafe accepted input "+str((index,chain)))
wf=Path(".github/workflows/issue311-r11-event-source.yml").read_text()
assert "schedule:" not in wf and "workflow_dispatch:" not in wf
source_job = wf.split("  source_observation:\n", 1)[1].split("  operator_readonly_functions:\n", 1)[0]
assert "contents: write" not in source_job and "pull-requests: write" not in source_job
assert "id-token: write" not in wf
assert "id-token: write" not in wf
assert "issue311-r11-candidate-adapter.py" in wf
assert "issue311-r11-candidate-admission.json" in wf
assert g.CENTRAL_SHA in wf
print("R11_CANDIDATE_ADAPTER_HOSTILE_PASS",len(cases),
      "NO_WRITER_NO_SIGNER_NO_CAS_NO_PUBLISH")

