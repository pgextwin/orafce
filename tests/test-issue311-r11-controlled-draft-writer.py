#!/usr/bin/env python3
"""R11 controlled Draft: no historic stable may be mislabeled a new candidate."""
import importlib.util
from pathlib import Path
mfile=Path(__file__).resolve().parents[1]/"scripts/issue311-r11-controlled-draft-writer.py"
s=importlib.util.spec_from_file_location("r11draft",mfile)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
ctx={"rid":"r11d-20261101-testcase0001","sourceHead":"a"*40,
     "baseTree":"b"*40,"tree":"c"*40,"commit":"d"*40,
     "proofPath":"docs/r11-controlled-draft-proof/r11d-20261101-testcase0001.md",
     "proof":"proof","message":"test","title":"CONTROLLED",
     "body":"NO PUBLISH"}
cases=[("git/trees",{"base_tree":"b"*40,"tree":[{
   "path":ctx["proofPath"],"mode":"100644","type":"blob","content":"proof"}]}),
   ("git/commits",{"message":"test","tree":"c"*40,"parents":["a"*40]}),
   ("git/refs",{"ref":"refs/heads/r11-controlled-draft/"+ctx["rid"],"sha":"d"*40}),
   ("pulls",{"title":"CONTROLLED","head":"r11-controlled-draft/"+ctx["rid"],
    "base":"main","body":"NO PUBLISH","draft":True})]
for path,body in cases:
    m.verify_create("POST",path,body,ctx)
    bad=dict(body);bad["publicationAuthorized"]=True
    try:m.verify_create("POST",path,bad,ctx)
    except m.Denied:pass
    else:raise AssertionError("unbounded writer passed "+path)
for path in ("issues","releases","git/refs/heads/main"):
    try:m.verify_create("POST",path,{},ctx)
    except m.Denied:pass
    else:raise AssertionError("unexpected writer endpoint")
for stage in ("PATCH","PUT","DELETE"):
    try:m.verify_create(stage,"pulls",cases[-1][1],ctx)
    except m.Denied:pass
    else:raise AssertionError("mutation allowed")
assert m.PREFIX==".github/r11-controlled-draft-intents/"
assert m.MARKER.startswith("<!-- pgextwin-r11-controlled-draft:")
assert not any("config/extension.json" in str(body) for _,body in cases)
print("R11_CONTROLLED_DRAFT_HOSTILE_PASS_NO_PROVIDER_WRITE")
