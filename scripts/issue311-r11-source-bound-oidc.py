#!/usr/bin/env python3
"""Issue311 W11-A: immutable real operator-source bound, read-only OIDC eligibility/audit.

This module has no writer. Successful eligibility permits a NONPUBLISHING signed
build only, never Publisher, CAS, schedule removal or R11 acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

REPO = "pgextwin/orafce"
SOURCE_RUN = 41163177685
SOURCE_HEAD = "6f116c27380ff489a65fdf4eaff579d556f2907e"
SOURCE_ARTIFACT = 13027868207
SOURCE_DIGEST = "1f21ed4d3c65356b3d709ff29c9fedc76ed3977b213a2895169f800ed5e82d7a"
SOURCE_RECEIPT_HASH = "6fe9956849ab1fc8d848e9a3a7e800a16c9c9ee446b80bfeef1904a43e88f5b3"
CANDIDATE_RECEIPT_HASH = "5c5f071e055fe2b559d4773e275fada07588a8955f0ea5ee9df8df238c154057"
SOURCE_PATH = ".github/workflows/issue311-r11-event-source.yml"
CALLER = ".github/workflows/issue311-r11-source-bound-signed.yml"
SIGNER = ".github/workflows/build-extension-attested.yml"
SIGNER_SHA = "5756b3c5136a8bf4db710016cfe97555f0a71c6d"
SOURCE_KIND = "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
REQUEST_ID = "r11-20261031-orafce03"
EXPECTED_CANDIDATE = 8
EXPECTED_MERGE = "9f09147b86703efd09e1ae1d5b23bd6c92c6b9b2"
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")

class Denied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Denied(reason)

def decode(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)

def gh_get(path):
    need(bool(re.fullmatch(
         r"repos/pgextwin/orafce/(?:actions/runs/[1-9][0-9]*(?:/(?:jobs|artifacts)\?per_page=100)?|branches/main|compare/[a-f0-9]{40}\.\.\.[a-f0-9]{40})",path)),
         "disallowed GitHub endpoint")
    need(os.environ.get("GH_TOKEN"), "GitHub read token absent")
    p = subprocess.run(["gh", "api", "--method", "GET", path],
                       capture_output=True, text=True, timeout=60, check=False)
    need(p.returncode == 0 and 0 < len(p.stdout) < 2_000_000, "authenticated GET failed")
    return decode(p.stdout)

def actual_source_zip(artifact):
    need(type(artifact) is dict and artifact.get("id") == SOURCE_ARTIFACT
         and artifact.get("name") == "issue311-r11-operator-candidate-original"
         and artifact.get("expired") is False
         and artifact.get("digest") == "sha256:" + SOURCE_DIGEST
         and (artifact.get("workflow_run") or {}).get("id") == SOURCE_RUN
         and (artifact.get("workflow_run") or {}).get("head_sha") == SOURCE_HEAD,
         "original source ZIP metadata mismatch")
    token = os.environ.get("GH_TOKEN")
    need(bool(token), "missing authenticated ZIP GET credential")
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, url):
            src, dest = urllib.parse.urlparse(request.full_url), urllib.parse.urlparse(url)
            need(dest.scheme == "https", "insecure download redirect")
            if src.hostname != dest.hostname:
                return urllib.request.Request(url, headers={"User-Agent": "pgextwin-r11-source-readonly"})
            return super().redirect_request(request, fp, code, msg, headers, url)
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/artifacts/{SOURCE_ARTIFACT}/zip",
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"})
    with urllib.request.build_opener(SafeRedirect()).open(req, timeout=90) as response:
        raw = response.read(500_000)
    need(hashlib.sha256(raw).hexdigest() == SOURCE_DIGEST, "original ZIP actual bytes mismatch")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None and set(z.namelist()) == {
            "issue311-r11-source-admission.json", "issue311-r11-candidate-admission.json"
        }, "original ZIP CRC or file set wrong")
        receipts = [z.read(n) for n in
                    ("issue311-r11-source-admission.json", "issue311-r11-candidate-admission.json")]
    need(hashlib.sha256(receipts[0]).hexdigest() == SOURCE_RECEIPT_HASH
         and hashlib.sha256(receipts[1]).hexdigest() == CANDIDATE_RECEIPT_HASH,
         "source inner receipt bytes differ")
    return decode(receipts[0]), decode(receipts[1])

def verify_source(run, source_run, source_job, artifact, branch, compare, source, candidate, env):
    need(env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_ACTOR") == "ShutenOishi", "not a real protected operator push")
    head = env.get("GITHUB_SHA")
    need(type(head) is str and SHA.fullmatch(head)
         and head != SOURCE_HEAD
         and type(env.get("GITHUB_RUN_ID")) is str and env["GITHUB_RUN_ID"].isdigit(),
         "invalid new signed-run identity")
    need(run.get("id") == int(env["GITHUB_RUN_ID"]) and run.get("head_sha") == head
         and run.get("run_attempt") == 1 and run.get("event") == "push"
         and run.get("path") == CALLER and run.get("actor", {}).get("id") == 27071164
         and run.get("status") in ("in_progress", "queued")
         and run.get("conclusion") is None, "new root original run mismatch")
    need(source_run.get("id") == SOURCE_RUN and source_run.get("head_sha") == SOURCE_HEAD
         and source_run.get("head_branch") == "main" and source_run.get("event") == "push"
         and source_run.get("path") == SOURCE_PATH and source_run.get("run_attempt") == 1
         and source_run.get("status") == "completed" and source_run.get("conclusion") == "success"
         and source_run.get("actor", {}).get("id") == 27071164, "historical source not genuine")
    need(type(source_job) is dict and source_job.get("total_count") == 2
         and len(source_job.get("jobs", [])) == 2
         and len([j for j in source_job["jobs"]
                  if j.get("id") == 124424997720 and j.get("conclusion") == "success"]) == 1
         and len([j for j in source_job["jobs"] if j.get("conclusion") == "skipped"]) == 1,
         "original source job incomplete")
    need(artifact.get("id") == SOURCE_ARTIFACT and artifact.get("digest") == "sha256:" + SOURCE_DIGEST,
         "source artifact replaced")
    checks = (((branch.get("protection") or {}).get("required_status_checks") or {}).get("checks") or [])
    need(branch.get("name") == "main" and branch.get("protected") is True
         and (branch.get("commit") or {}).get("sha") == head
         and any(c.get("context") == "Windows required summary" and c.get("app_id") == 15368
                 for c in checks), "not protected required-CI main")
    need(compare.get("status") == "ahead" and type(compare.get("ahead_by")) is int
         and 1 <= compare["ahead_by"] <= 20 and compare.get("behind_by") == 0
         and type(compare.get("commits")) is list
         and compare["commits"][-1].get("sha") == head, "source is not a protected ancestor")
    need(source.get("schemaVersion") == 1 and source.get("requestId") == REQUEST_ID
         and source.get("sourceKind") == SOURCE_KIND
         and source.get("repository") == REPO
         and source.get("originalRun") == SOURCE_RUN and source.get("attempt") == 1
         and source.get("originalAfter") == SOURCE_HEAD
         and source.get("mergedPr") == 63 and source.get("candidatePr") == EXPECTED_CANDIDATE
         and source.get("candidateMergeSha") == EXPECTED_MERGE
         and source.get("protectedSourceVerified") is True
         and source.get("candidateVerified") is False, "invalid immutable original source receipt")
    need(candidate.get("schemaVersion") == 1 and candidate.get("requestId") == REQUEST_ID
         and candidate.get("sourceHead") == SOURCE_HEAD
         and candidate.get("sourceAttempt") == 1
         and candidate.get("originalOperatorRun") == SOURCE_RUN
         and candidate.get("originalCandidatePr") == EXPECTED_CANDIDATE
         and candidate.get("originalCandidateMerge") == EXPECTED_MERGE
         and candidate.get("centralRegistryBlob") == "d6161c4bd374d3860a1c0adbeb73ed392f25a12f"
         and candidate.get("candidateVerified") is True
         and candidate.get("historicalNativeWindowsVerified") is True
         and candidate.get("historicalOriginalZipByteRehashPerformed") is False
         and candidate.get("originalCentralScanRunVerified") is False
         and candidate.get("newOIDCSigningRun") is None
         and candidate.get("independentSigstoreAudits") == 0, "candidate admission forged")
    for receipt in (source, candidate):
        need(all(receipt.get(k) is False for k in (
            "candidateWriterCalled", "signingPerformed", "appCasPerformed",
            "scheduleRemoved", "publicationAuthorized", "runtimeEnabled")),
            "source exceeds nonpublishing permissions")
    need(candidate.get("publisherSourceKindAuthorized") is False,
         "publisher privilege leaked into candidate")
    return {"schemaVersion": 1, "status": "SOURCE_BOUND_OIDC_ELIGIBLE_NONPUBLISHING",
            "sourceKind": SOURCE_KIND, "repository": REPO, "requestId": REQUEST_ID,
            "sourceRun": SOURCE_RUN, "sourceAttempt": 1, "sourceHead": SOURCE_HEAD,
            "sourceArtifact": SOURCE_ARTIFACT, "sourceArtifactOuterSha256": SOURCE_DIGEST,
            "sourceReceiptSha256": SOURCE_RECEIPT_HASH,
            "candidateReceiptSha256": CANDIDATE_RECEIPT_HASH,
            "newSigningRun": int(env["GITHUB_RUN_ID"]), "newSigningHead": head,
            "originalCandidatePr": EXPECTED_CANDIDATE,
            "publicationAuthorized": False, "runtimeEnabled": False,
            "appCasPerformed": False, "scheduleRemoved": False}

def source_main():
    env = os.environ
    need(env.get("GH_TOKEN"), "missing GET credential")
    source_run = gh_get(f"repos/{REPO}/actions/runs/{SOURCE_RUN}")
    original_job = gh_get(f"repos/{REPO}/actions/runs/{SOURCE_RUN}/jobs?per_page=100")
    artset = gh_get(f"repos/{REPO}/actions/runs/{SOURCE_RUN}/artifacts?per_page=100")
    need(artset.get("total_count") == 1 and len(artset.get("artifacts", [])) == 1,
         "source artifact set mismatch")
    art = artset["artifacts"][0]
    source, candidate = actual_source_zip(art)
    head = env.get("GITHUB_SHA", "")
    need(bool(SHA.fullmatch(head)), "malformed current commit input")
    current = gh_get(f"repos/{REPO}/actions/runs/{env['GITHUB_RUN_ID']}")
    branch = gh_get(f"repos/{REPO}/branches/main")
    compare = gh_get(f"repos/{REPO}/compare/{SOURCE_HEAD}...{head}")
    result = verify_source(current, source_run, original_job, art, branch, compare,
                           source, candidate, env)
    Path("issue311-r11-oidc-eligibility.json").write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print("R11_AUTHENTIC_IMMUTABLE_SOURCE_BOUND; NEW_OIDC_BUILD_ELIGIBLE; PUBLISH_DENY")

def safe_signed_receipt(item, env):
    need(item.get("status") == "SOURCE_BOUND_OIDC_ELIGIBLE_NONPUBLISHING"
         and item.get("sourceRun") == SOURCE_RUN and item.get("sourceHead") == SOURCE_HEAD
         and item.get("sourceArtifact") == SOURCE_ARTIFACT
         and item.get("sourceArtifactOuterSha256") == SOURCE_DIGEST
         and item.get("sourceReceiptSha256") == SOURCE_RECEIPT_HASH
         and item.get("candidateReceiptSha256") == CANDIDATE_RECEIPT_HASH
         and item.get("newSigningRun") == int(env.get("GITHUB_RUN_ID","0"))
         and item.get("newSigningHead") == env.get("GITHUB_SHA")
         and item.get("requestId") == REQUEST_ID
         and all(item.get(x) is False for x in
                 ("publicationAuthorized", "runtimeEnabled", "appCasPerformed", "scheduleRemoved")),
         "auditor intent not bound to true source")
    return True

def signed_file_names(version_ref):
    need(type(version_ref) is str
         and bool(re.fullmatch(r"VERSION_[0-9]+_[0-9]+_[0-9]+", version_ref)),
         "malformed signed upstream version")
    return {f"orafce-{version_ref}-pg{n}-windows-x64.{extension}"
            for n in range(14,19)
            for extension in ("zip", "spdx.json", "vulnerabilities.json")}

def audit_signed_main_lineage(orig, branch, head, run_id, compare=None):
    """Keep the original signer SHA immutable while allowing protected main to advance.

    The original source gate already authenticated this exact push when main
    equaled head. An independent auditor may finish after another protected
    merge; only a GET-proven fast-forward from signed head is acceptable.
    """
    need(orig.get("id") == run_id and orig.get("run_attempt") == 1
         and orig.get("head_sha") == head and orig.get("path") == CALLER
         and orig.get("event") == "push" and orig.get("status") == "in_progress"
         and orig.get("conclusion") is None, "signed root Run changed")
    current = (branch.get("commit") or {}).get("sha")
    checks = (((branch.get("protection") or {}).get("required_status_checks") or {}).get("checks") or [])
    need(branch.get("name") == "main" and branch.get("protected") is True
         and type(current) is str and SHA.fullmatch(current)
         and any(c.get("context") == "Windows required summary"
                 and c.get("app_id") == 15368 for c in checks),
         "current main is not protected by required App CI")
    if current == head:
        return "SIGNED_HEAD_CURRENT"
    need(type(compare) is dict and compare.get("status") == "ahead"
         and type(compare.get("ahead_by")) is int
         and 1 <= compare["ahead_by"] <= 20
         and compare.get("behind_by") == 0
         and (compare.get("base_commit") or {}).get("sha") == head
         and (compare.get("merge_base_commit") or {}).get("sha") == head
         and type(compare.get("commits")) is list
         and len(compare["commits"]) == compare["ahead_by"]
         and compare["commits"][-1].get("sha") == current,
         "signed HEAD is not an ancestor of protected current main")
    return "SIGNED_HEAD_PROTECTED_ANCESTOR"


def audit_main(folder, intent_path):
    env = os.environ
    need(env.get("GITHUB_REPOSITORY") == REPO
         and env.get("GITHUB_EVENT_NAME") == "push"
         and env.get("GITHUB_REF") == "refs/heads/main"
         and env.get("GITHUB_RUN_ATTEMPT") == "1"
         and env.get("GITHUB_JOB") == "independent_audit"
         and env.get("GH_TOKEN"), "not the real independent push auditor")
    intent = decode(Path(intent_path).read_text("utf-8"))
    safe_signed_receipt(intent, env)
    head, run_id = env["GITHUB_SHA"], int(env["GITHUB_RUN_ID"])
    orig = gh_get(f"repos/{REPO}/actions/runs/{run_id}")
    branch = gh_get(f"repos/{REPO}/branches/main")
    current_main = (branch.get("commit") or {}).get("sha")
    comparison = (gh_get(f"repos/{REPO}/compare/{head}...{current_main}")
                  if type(current_main) is str and SHA.fullmatch(current_main)
                  and current_main != head else None)
    audit_signed_main_lineage(orig, branch, head, run_id, comparison)
    # actions/download-artifact merge-multiple extracts the *inner* file names,
    # not the outer Actions artifact names. The immutable signer uses the
    # versioned name: orafce-VERSION_4_17_1-pg17-windows-x64.zip.
    config = decode(Path("config/extension.json").read_text("utf-8"))
    version_ref = (config.get("upstream") or {}).get("ref")
    need(version_ref == "VERSION_4_17_1" and
         (config.get("upstream") or {}).get("commit") ==
             "542aed2e0297898cc9844fede3c4452f894b37ed",
         "source-bound upstream version/ref changed")
    names = {p.name for p in folder.iterdir() if p.is_file()}
    expected = signed_file_names(version_ref)
    need(names == expected, "signed ZIP/SPDX/Grype PG14-18 missing or added")
    results = {}
    for n in range(14,19):
        base = f"orafce-{version_ref}-pg{n}-windows-x64"
        z, s, g = (folder / (base+ext) for ext in
                   (".zip", ".spdx.json", ".vulnerabilities.json"))
        need(all(0 < p.stat().st_size < 1_000_000_000 for p in (z,s,g)),
             "missing or oversized signed bytes")
        sbom = decode(s.read_text("utf-8-sig"))
        grype = decode(g.read_text("utf-8-sig"))
        need(sbom.get("spdxVersion") == "SPDX-2.3" and type(grype.get("matches")) is list,
             "SBOM or Grype missing")
        with zipfile.ZipFile(z) as archive:
            need(archive.testzip() is None, "signed inner ZIP CRC mismatch")
            pkg = decode(archive.read("PACKAGE-INFO.json").decode("utf-8-sig"))
        wf = pkg.get("workflowRun", {})
        bi = pkg.get("buildInfrastructure", {})
        need(pkg.get("buildMode") == "release-attested"
             and pkg.get("package", {}).get("name") == "orafce"
             and pkg.get("postgresql", {}).get("major") == n
             and pkg.get("source", {}).get("packagingRepository") == REPO
             and pkg.get("source", {}).get("packagingCommit") == head
             and bi.get("repository") == "pgextwin/build"
             and bi.get("workflow") == SIGNER and bi.get("commit") == SIGNER_SHA
             and wf.get("id") == run_id and wf.get("attempt") == 1
             and wf.get("event") == "push" and wf.get("ref") == "refs/heads/main",
             "signed package OIDC source/PG/run mismatch")
        digest = hashlib.sha256(z.read_bytes()).hexdigest()
        for predicate in ("https://slsa.dev/provenance/v1","https://spdx.dev/Document/v2.3"):
            command = ["gh","attestation","verify",str(z),"--repo",REPO,
                       "--signer-workflow","pgextwin/build/"+SIGNER,
                       "--signer-digest",SIGNER_SHA,"--source-digest",head,
                       "--source-ref","refs/heads/main",
                       "--predicate-type",predicate,"--format","json"]
            cp = subprocess.run(command, text=True, capture_output=True,
                                timeout=180, check=False)
            need(cp.returncode == 0 and cp.stdout, "real gh Sigstore verification failed")
            verification = decode(cp.stdout)
            need(type(verification) is list and len(verification) == 1
                 and type(verification[0].get("verificationResult")) is dict,
                 "missing independent cryptographic result")
            v = verification[0]["verificationResult"]
            st, cert = v.get("statement",{}), v.get("signature",{}).get("certificate",{})
            signer_uri = f"https://github.com/pgextwin/build/{SIGNER}@{SIGNER_SHA}"
            run_uri = f"https://github.com/{REPO}/actions/runs/{run_id}/attempts/1"
            need(st.get("predicateType") == predicate
                 and st.get("subject") == [{"name":z.name,"digest":{"sha256":digest}}]
                 and cert.get("issuer") == "https://token.actions.githubusercontent.com"
                 and cert.get("runInvocationURI") == run_uri
                 and cert.get("buildSignerURI") == signer_uri
                 and cert.get("sourceRepositoryDigest") == head
                 and cert.get("sourceRepositoryRef") == "refs/heads/main"
                 and cert.get("buildConfigURI") ==
                     f"https://github.com/{REPO}/{CALLER}@refs/heads/main"
                 and cert.get("buildTrigger") == "push"
                 and type(v.get("verifiedTimestamps")) is list
                 and len(v["verifiedTimestamps"]) > 0, "signed certificate identity wrong")
            if predicate.endswith("v2.3"):
                need(st.get("predicate") == sbom, "signed SBOM differs from real SPDX")
        results[str(n)] = {
            "zipSha256": digest,
            "spdxSha256": hashlib.sha256(s.read_bytes()).hexdigest(),
            "grypeSha256": hashlib.sha256(g.read_bytes()).hexdigest()}
    need(all(hashlib.sha256((folder/(f"orafce-{version_ref}-pg{n}-windows-x64.zip")).read_bytes()).hexdigest()
             == results[str(n)]["zipSha256"] for n in range(14,19)),
         "signed bytes changed after verification")
    receipt = {"schemaVersion":1,"result":"TWO_REQUIRED_REAL_AUDIT_JOBS_NONPUBLISHING",
               "sourceRun":SOURCE_RUN,"sourceArtifact":SOURCE_ARTIFACT,
               "newSigningRun":run_id,"newSigningHead":head,
               "job":env["GITHUB_JOB"],"auditInstance":env.get("PGEXTWIN_AUDIT_INSTANCE"),
               "signedOriginalByMajor":results,
               "cryptographicVerification":"REAL_GH_SIGSTORE",
               "publicationAuthorized":False, "runtimeEnabled":False, "appCasPerformed":False,
               "scheduleRemoved":False}
    need(receipt["auditInstance"] in ("first","second"), "missing distinct auditor")
    Path(f"r11-source-bound-sigstore-{receipt['auditInstance']}.json").write_text(
        json.dumps(receipt,sort_keys=True,separators=(",",":"))+"\n","utf-8")
    print("REAL_INDEPENDENT_SOURCE_BOUND_SIGSTORE", receipt["auditInstance"],"NO_PUBLISH")

def join_main(first_path, second_path):
    a,b = (decode(Path(p).read_text("utf-8")) for p in (first_path,second_path))
    need(a.get("auditInstance") == "first" and b.get("auditInstance") == "second"
         and a.get("job") == b.get("job") == "independent_audit",
         "not two distinct auditor jobs")
    for key in ("schemaVersion","result","sourceRun","sourceArtifact",
                "newSigningRun","newSigningHead","signedOriginalByMajor",
                "cryptographicVerification","publicationAuthorized","runtimeEnabled",
                "appCasPerformed","scheduleRemoved"):
        need(a.get(key) == b.get(key), "auditor original-byte mismatch: "+key)
    need(a.get("sourceRun") == SOURCE_RUN and a.get("sourceArtifact") == SOURCE_ARTIFACT
         and a.get("newSigningRun") == int(os.environ.get("GITHUB_RUN_ID","0"))
         and a.get("newSigningHead") == os.environ.get("GITHUB_SHA")
         and a.get("cryptographicVerification") == "REAL_GH_SIGSTORE"
         and set(a.get("signedOriginalByMajor",{})) == set(map(str,range(14,19)))
         and all(a.get(k) is False for k in
                 ("publicationAuthorized","runtimeEnabled","appCasPerformed","scheduleRemoved")),
         "not genuine new signed original")
    result = dict(a)
    result.pop("job"); result.pop("auditInstance")
    result["independentSigstoreAudits"] = 2
    result["status"] = "DUAL_REAL_SIGSTORE_NONPUBLISHING_ONLY"
    Path("r11-source-bound-dual-sigstore.json").write_text(
        json.dumps(result,sort_keys=True,separators=(",",":"))+"\n","utf-8")
    print("R11_NEW_SIGNED_RUN_TWO_INDEPENDENT_VERIFIERS; PUBLISH_DENY")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("source","audit","join"))
    p.add_argument("--dist")
    p.add_argument("--intent")
    p.add_argument("--first")
    p.add_argument("--second")
    args=p.parse_args()
    try:
        if args.mode=="source": source_main()
        elif args.mode=="audit":
            need(args.dist and args.intent,"audit paths required")
            audit_main(Path(args.dist),args.intent)
        else:
            need(args.first and args.second,"join receipts required")
            join_main(args.first,args.second)
        return 0
    except (Denied, ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired,
            zipfile.BadZipFile, urllib.error.URLError) as ex:
        print("R11_SOURCE_BOUND_DENY:",str(ex),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
