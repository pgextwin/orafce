#!/usr/bin/env python3
"""Offline hostile cases: do not substitute for original provider POST/readback."""
import importlib.util
from pathlib import Path
import json
s=importlib.util.spec_from_file_location("r11controlled",
    Path(__file__).resolve().parents[1]/"scripts/issue311-r11-controlled-issue-writer.py")
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base={"name":"orafce","upstream":{"repository":m.UPSTREAM,"ref":m.TAG,
      "version":"4.17.1","commit":m.COMMIT}}
release={"tag_name":m.TAG,"draft":False,"prerelease":False,
         "published_at":"2026-10-14T00:00:00Z",
         "html_url":"https://github.com/orafce/orafce/releases/tag/"+m.TAG}
ref={"ref":"refs/tags/"+m.TAG,"object":{"type":"tag","sha":m.TAG_SHA}}
tag={"tag":m.TAG,"sha":m.TAG_SHA,"object":{"type":"commit","sha":m.COMMIT}}
m.verify_upstream(base,release,ref,tag)
def reject(fn):
    try: fn()
    except (m.Denied,ValueError): return
    raise AssertionError("hostile case accepted")
for obj,key,val in ((base,"name","fake"),(release,"draft",True),
                    (release,"prerelease",True),(ref,"ref","refs/tags/moved"),
                    (tag,"sha","0"*40)):
    copy=json.loads(json.dumps(obj));copy[key]=val
    args=[base,release,ref,tag];args[[base,release,ref,tag].index(obj)]=copy
    reject(lambda args=args:m.verify_upstream(*args))
reject(lambda:m.api(m.REPO,"releases",method="GET"))
reject(lambda:m.api(m.REPO,"issues/1",method="PATCH",fields={"state":"closed"}))
reject(lambda:m.api(m.REPO,"git/refs",method="POST",fields={"ref":"abc"}))
assert m.MARKER not in "<!-- pgextwin-update-watch:v1:upstream:orafce -->"

# GitHub Contents API standard LF-wrapped base64 is genuine and must decode.
import base64
payload=b'{"source":"original"}'
encoded=base64.b64encode(payload).decode("ascii")
assert m.decode_contents({"encoding":"base64",
    "content":encoded[:6]+"\n"+encoded[6:]+"\n"}) == payload
for corrupt in (encoded[:6]+"\r\n"+encoded[6:],encoded[:6]+"\t"+encoded[6:],
                encoded[:6]+"!"+encoded[6:],"abc!", ""):
    reject(lambda corrupt=corrupt:m.decode_contents({"encoding":"base64","content":corrupt}))
reject(lambda:m.decode_contents({"encoding":"none","content":encoded}))
print("R11_CONTROLLED_HOSTILE_PASS; NO LIVE WRITE")
