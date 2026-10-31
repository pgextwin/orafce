#!/usr/bin/env python3
"""R11 W11-A: read-only authentic merged candidate adapter for operator push intent.

Uses the already proven, SHA-pinned central PR/Windows verifier. Never admits
Writer, State App, signing or publishing. Historical ZIP metadata is NOT a
re-download of original bytes; neither is this a central original scan.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = "pgextwin/orafce"
CENTRAL = "pgextwin/build"
CENTRAL_SHA = "12e9c809d963c82735e23680ac1838693a6de356"
REGISTRY_BLOB = "d6161c4bd374d3860a1c0adbeb73ed392f25a12f"
CENTRAL_ROOT = Path(".pgextwin-build")
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")

class Denied(ValueError):
    pass

def need(condition, reason):
    if not condition:
        raise Denied(reason)

def get(repo, endpoint):
    need((repo == CENTRAL and endpoint in ("branches/main",
          "contents/metadata/merged-candidate-requalification.json?ref=" + CENTRAL_SHA))
         or (repo == REPO and re.fullmatch(
           r"actions/runs/[1-9][0-9]*/artifacts\?per_page=100", endpoint)),
         "GET endpoint denied")
    need(bool(os.environ.get("GH_TOKEN")), "authenticated GET required")
    p = subprocess.run(["gh", "api", "--method", "GET", "repos/" + repo + "/" + endpoint],
                       capture_output=True, text=True, timeout=60, check=False)
    need(p.returncode == 0 and 0 < len(p.stdout) < 3000000, "GitHub GET failed")
    def unique(pairs):
        out = {}
        for k, v in pairs:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    return json.loads(p.stdout, object_pairs_hook=unique)

def validate(source, row, registry, central_branch, central_file, proof, artifacts):
    need(type(source) is dict and source.get("sourceKind") ==
         "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
         and source.get("repository") == REPO
         and source.get("protectedSourceVerified") is True
         and source.get("attempt") == 1
         and type(source.get("originalRun")) is int and source["originalRun"] > 0
         and type(source.get("requestId")) is str
         and all(type(source.get(k)) is str and SHA.fullmatch(source[k])
                 for k in ("originalBefore", "originalAfter", "originalRequestBlob"))
         and source.get("candidateVerified") is False
         and all(source.get(k) is False for k in
                 ("candidateWriterCalled","signingPerformed","appCasPerformed",
                  "scheduleRemoved","publicationAuthorized","runtimeEnabled")),
         "untrusted original operator source")
    need(type(registry) is dict and registry.get("schemaVersion") == 1
         and registry.get("publication") == "DENY"
         and type(registry.get("entries")) is list
         and len([x for x in registry["entries"]
                  if type(x) is dict and x.get("repository") == REPO]) == 1,
         "untrusted central registry")
    expected = [x for x in registry["entries"] if x.get("repository") == REPO][0]
    need(row == expected and row.get("pr") == source.get("candidatePr")
         and row.get("mergeSha") == source.get("candidateMergeSha"),
         "caller-selected candidate differs from protected central registry")
    need(central_branch.get("name") == "main"
         and central_branch.get("protected") is True
         and type(central_branch.get("commit")) is dict
         and type(central_branch["commit"].get("sha")) is str
         and SHA.fullmatch(central_branch["commit"]["sha"]),
         "central main not protected")
    need(central_file.get("path") == "metadata/merged-candidate-requalification.json"
         and central_file.get("type") == "file"
         and central_file.get("sha") == REGISTRY_BLOB,
         "pinned central registry blob moved or was rewritten")
    need(type(proof) is dict and proof.get("repository") == REPO
         and proof.get("status") == "MERGED_BOT_PR_REQUALIFICATION_NONPUBLISHING"
         and proof.get("originalPr") == row["pr"]
         and proof.get("originalHead") == row["candidateHead"]
         and proof.get("mergedAncestor") == row["mergeSha"]
         and proof.get("manifestBlob") == row["manifestBlob"]
         and proof.get("originalNativeWindowsRun") == row["nativeRun"]
         and proof.get("currentProtectedMain") == source["originalAfter"]
         and proof.get("verifiedOriginalNativeCi") is True
         and type(proof.get("requiredCheckRun")) is int
         and proof["requiredCheckRun"] > 0
         and proof.get("originalNativeZipBytesRehashed") is False
         and proof.get("publicationAuthorized") is False
         and proof.get("publisherSourceKindAuthorized") is False,
         "historical candidate verifier not satisfied")
    need(type(artifacts) is dict and type(artifacts.get("artifacts")) is list
         and len(artifacts["artifacts"]) == 5
         and artifacts.get("total_count") == 5,
         "native original Windows five-artifact set incomplete")
    got = {}
    for a in artifacts["artifacts"]:
        need(type(a) is dict and a.get("expired") is False
             and type(a.get("id")) is int and a["id"] > 0
             and type(a.get("digest")) is str and DIGEST.fullmatch(a["digest"])
             and type(a.get("size_in_bytes")) is int and a["size_in_bytes"] > 0
             and (a.get("workflow_run") or {}).get("id") == row["nativeRun"]
             and (a.get("workflow_run") or {}).get("head_sha") == row["candidateHead"],
             "original native artifact identity/digest denied")
        name = a.get("name")
        need(type(name) is str and name not in got, "duplicate/malformed native artifact")
        got[name] = {"id":a["id"],"providerDigest":a["digest"],
                     "sizeBytes":a["size_in_bytes"]}
    need(set(got) == {f"orafce-pg{major}-windows-x64" for major in (14,15,16,17,18)},
         "required native PG14-18 artifacts missing or swapped")
    return {"schemaVersion":1, "requestId":source["requestId"],"repository":REPO,
            "sourceKind":source["sourceKind"],"originalOperatorRun":source["originalRun"],
            "sourceAttempt":1,"sourceHead":source["originalAfter"],
            "sourceRequestBlob":source["originalRequestBlob"],
            "centralRegistryProtectedMain":central_branch["commit"]["sha"],
            "centralPinnedVerifier":CENTRAL_SHA,"centralRegistryBlob":REGISTRY_BLOB,
            "originalCandidatePr":row["pr"],"originalCandidateHead":row["candidateHead"],
            "originalCandidateMerge":row["mergeSha"],
            "originalNativeWindowsRun":row["nativeRun"],
            "originalRequiredWindowsCheckRun":proof["requiredCheckRun"],
            "manifestBlob":row["manifestBlob"], "nativeArtifactMetadata":got,
            "candidateVerified":True,"historicalNativeWindowsVerified":True,
            "historicalOriginalZipByteRehashPerformed":False,
            "originalCentralScanRunVerified":False,
            "newOIDCSigningRun":None,"independentSigstoreAudits":0,
            "candidateWriterCalled":False,"signingPerformed":False,
            "appCasPerformed":False,"scheduleRemoved":False,
            "publicationAuthorized":False,"publisherSourceKindAuthorized":False,
            "runtimeEnabled":False}

def main():
    try:
        source = json.loads(Path("issue311-r11-source-admission.json").read_text("utf-8"))
        need(os.environ.get("GITHUB_REPOSITORY") == REPO
             and os.environ.get("GITHUB_EVENT_NAME") == "push"
             and os.environ.get("GITHUB_REF") == "refs/heads/main"
             and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
             and os.environ.get("GITHUB_SHA") == source.get("originalAfter")
             and int(os.environ.get("GITHUB_RUN_ID","0")) == source.get("originalRun"),
             "candidate not linked to authenticated original main push")
        root = CENTRAL_ROOT / "scripts" / "verify-merged-candidate-requalification.py"
        need(root.is_file(), "missing immutable central verifier")
        spec = importlib.util.spec_from_file_location("r11_central_origin", root)
        origin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(origin)
        registry = json.loads((CENTRAL_ROOT / "metadata" /
             "merged-candidate-requalification.json").read_text("utf-8"))
        row = [x for x in registry["entries"] if x.get("repository") == REPO]
        need(len(row) == 1, "ambiguous protected registry")
        row = row[0]
        branch = origin.github(REPO, "branches/main")
        n, head, merge, native = (row["pr"],row["candidateHead"],row["mergeSha"],row["nativeRun"])
        proof = origin.validate_merged(row, current=branch,
             pr=origin.github(REPO,"pulls/"+str(n)),
             changed=origin.github(REPO,"pulls/"+str(n)+"/files?per_page=100"),
             associated=origin.github(REPO,"commits/"+head+"/pulls?per_page=100"),
             compare=origin.github(REPO,"compare/"+merge+"...main"),
             candidate_contents=origin.github(REPO,"contents/config/extension.json?ref="+head),
             main_contents=origin.github(REPO,"contents/config/extension.json?ref="+source["originalAfter"]),
             native_run=origin.github(REPO,"actions/runs/"+str(native)),
             checks=origin.github(REPO,"commits/"+head+"/check-runs?per_page=100"))
        result = validate(source, row, registry,
            get(CENTRAL,"branches/main"),
            get(CENTRAL,"contents/metadata/merged-candidate-requalification.json?ref="+CENTRAL_SHA),
            proof, get(REPO,"actions/runs/"+str(native)+"/artifacts?per_page=100"))
        need(origin.github(REPO,"branches/main") == branch
             and origin.github(REPO,"branches/main")["commit"]["sha"] == source["originalAfter"],
             "protected source HEAD moved during candidate verification")
        Path("issue311-r11-candidate-admission.json").write_text(
            json.dumps(result,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
        print("R11_ORIGINAL_CANDIDATE_PROVENANCE_VERIFIED; HISTORICAL_ZIP_METADATA_ONLY; SIGNING_CAS_PUBLISH_DENY")
        return 0
    except (Denied,ValueError,TypeError,KeyError,OSError,subprocess.TimeoutExpired) as exc:
        print("R11_CANDIDATE_DENY: "+str(exc),file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
