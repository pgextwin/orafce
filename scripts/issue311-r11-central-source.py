#!/usr/bin/env python3
"""W11-A: bind a real central fleet snapshot to an authenticated R11 candidate.

Historical central original only. This is not a fresh signing cycle, a candidate
writer, a State CAS call, a Publisher admission, or permission to remove cron.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

CENTRAL = "pgextwin/build"
REPO = "pgextwin/orafce"
RUN_ID = 41154463639
RUN_HEAD = "f4f1c4160fbf37fb6dbc1b1e0d8bae09a912d527"
ARTIFACTS = {
    "fleet-upstream-watch": (13025090337, "313fec3152af91c77b5f5e3119d6243bf82aa72cc2a6486c565cef4ad78dbf9e"),
    "merged-native-requalification-provenance-only": (13024577335, "27812dd4f50347605b229fc4f2a09c4978dce31640548e6b2cbf2d8ba6add9ff"),
}
SHA = re.compile(r"[0-9a-f]{40}\Z")

class Denied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Denied(reason)

def unique(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, "duplicate JSON key")
        out[key] = value
    return out

def read_json(path):
    p = Path(path)
    need(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size < 1000000,
         "missing or unsafe original JSON")
    return json.loads(p.read_text("utf-8"), object_pairs_hook=unique)

def get(endpoint):
    need(endpoint in (
        f"repos/{CENTRAL}/actions/runs/{RUN_ID}",
        f"repos/{CENTRAL}/actions/runs/{RUN_ID}/artifacts?per_page=100",
    ) or re.fullmatch(
        r"repos/pgextwin/orafce/contents/config/extension\.json\?ref=[0-9a-f]{40}",
        endpoint), "GET outside historical source allowlist")
    need(bool(os.environ.get("GH_TOKEN")), "missing authenticated read-only token")
    p = subprocess.run(["gh", "api", "--method", "GET", endpoint],
                       capture_output=True, text=True, timeout=60, check=False)
    need(p.returncode == 0 and 0 < len(p.stdout) < 3000000,
         "original GitHub GET failure")
    return json.loads(p.stdout, object_pairs_hook=unique)

def when(s):
    need(type(s) is str, "missing GitHub timestamp")
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Denied("malformed GitHub time") from exc
    need(dt.tzinfo is not None, "naive timestamp")
    return dt.astimezone(timezone.utc)

def validate(candidate, run, artifacts, scan, scanned_manifest):
    need(type(candidate) is dict
         and candidate.get("repository") == REPO
         and candidate.get("sourceKind") == "R11_PROTECTED_OPERATOR_PUSH_INTENT_NONPUBLISHING"
         and candidate.get("candidateVerified") is True
         and candidate.get("historicalNativeWindowsVerified") is True
         and candidate.get("historicalOriginalZipByteRehashPerformed") is False
         and candidate.get("originalCentralScanRunVerified") is False
         and candidate.get("originalCandidatePr") == 8
         and candidate.get("originalCandidateMerge") ==
             "9f09147b86703efd09e1ae1d5b23bd6c92c6b9b2"
         and type(candidate.get("manifestBlob")) is str
         and SHA.fullmatch(candidate["manifestBlob"])
         and type(candidate.get("sourceHead")) is str
         and SHA.fullmatch(candidate["sourceHead"])
         and type(candidate.get("originalOperatorRun")) is int
         and candidate["originalOperatorRun"] > 0
         and all(candidate.get(k) is False for k in
             ("candidateWriterCalled", "signingPerformed", "appCasPerformed",
              "scheduleRemoved", "publicationAuthorized", "runtimeEnabled")),
         "candidate admission absent or elevated")
    need(type(run) is dict and run.get("id") == RUN_ID
         and run.get("event") == "schedule"
         and run.get("path") == ".github/workflows/fleet-upstream-watch.yml"
         and run.get("head_branch") == "main" and run.get("head_sha") == RUN_HEAD
         and run.get("run_attempt") == 1
         and run.get("status") == "completed" and run.get("conclusion") == "success"
         and (run.get("repository") or {}).get("full_name") == CENTRAL,
         "not the original successful central schedule")
    start, end = when(run.get("created_at")), when(run.get("updated_at"))
    need(start <= end and end - start < timedelta(hours=3),
         "inconsistent original central run time")
    need(type(artifacts) is dict and artifacts.get("total_count") == len(ARTIFACTS)
         and type(artifacts.get("artifacts")) is list
         and len(artifacts["artifacts"]) == len(ARTIFACTS),
         "central original artifacts incomplete")
    observed = {}
    for item in artifacts["artifacts"]:
        name = item.get("name")
        need(type(name) is str and name in ARTIFACTS and name not in observed,
             "unknown or duplicate central artifact")
        expected_id, expected_hash = ARTIFACTS[name]
        need(item.get("id") == expected_id
             and item.get("digest") == "sha256:" + expected_hash
             and item.get("expired") is False
             and type(item.get("size_in_bytes")) is int and item["size_in_bytes"] > 0
             and (item.get("workflow_run") or {}).get("id") == RUN_ID
             and (item.get("workflow_run") or {}).get("head_sha") == RUN_HEAD,
             "central original artifact provenance mismatch")
        observed[name] = {"id": expected_id, "providerDigest": item["digest"]}
    need(type(scan) is dict and scan.get("schemaVersion") == 1
         and scan.get("scope") == "STABLE_UPSTREAM_GET_ONLY"
         and scan.get("publication") == "DENY"
         and scan.get("candidatePrCreated") is False
         and scan.get("fleetSize") == 17 and scan.get("indeterminate") == 0
         and type(scan.get("extensions")) is list
         and len(scan["extensions"]) == 17,
         "original fleet snapshot incomplete")
    scan_time = when(scan.get("generatedAt"))
    need(start - timedelta(minutes=5) <= scan_time <= end + timedelta(minutes=5),
         "scan not generated inside original schedule")
    members = scan["extensions"]
    need(all(type(x) is dict and type(x.get("repository")) is str for x in members)
         and len({x["repository"] for x in members}) == 17
         and all(x.get("status") in ("up-to-date", "update-available") for x in members),
         "untrusted original 17-fleet coverage")
    matched = [x for x in members if x["repository"] == REPO]
    need(len(matched) == 1 and matched[0]["status"] == "up-to-date"
         and type(matched[0].get("mainSha")) is str
         and SHA.fullmatch(matched[0]["mainSha"]),
         "original orafce scan not a single protected up-to-date candidate")
    need(type(scanned_manifest) is dict
         and scanned_manifest.get("path") == "config/extension.json"
         and scanned_manifest.get("type") == "file"
         and scanned_manifest.get("sha") == candidate["manifestBlob"],
         "original scan-main manifest not identical to original candidate")
    return {
        "schemaVersion": 1, "repository": REPO,
        "requestId": candidate["requestId"],
        "originalOperatorRun": candidate["originalOperatorRun"],
        "sourceHead": candidate["sourceHead"],
        "originalCandidatePr": candidate["originalCandidatePr"],
        "originalCandidateMerge": candidate["originalCandidateMerge"],
        "originalCandidateManifestBlob": candidate["manifestBlob"],
        "originalCentralRun": RUN_ID, "originalCentralHead": RUN_HEAD,
        "originalCentralScannedOrafceMain": matched[0]["mainSha"],
        "originalCentralArtifactMetadata": observed,
        "historicalCentralOriginalJsonVerified": True,
        "centralOuterZipBytesIndependentlyRehashedHere": False,
        "newOIDCSigningRun": None, "independentSigstoreAudits": 0,
        "candidateWriterCalled": False, "signingPerformed": False,
        "appCasPerformed": False, "scheduleRemoved": False,
        "publicationAuthorized": False, "runtimeEnabled": False
    }

def main():
    try:
        need(os.environ.get("GITHUB_REPOSITORY") == REPO
             and os.environ.get("GITHUB_EVENT_NAME") == "push"
             and os.environ.get("GITHUB_REF") == "refs/heads/main"
             and os.environ.get("GITHUB_RUN_ATTEMPT") == "1",
             "not genuine original operator push")
        candidate = read_json("issue311-r11-candidate-admission.json")
        need(os.environ.get("GITHUB_SHA") == candidate.get("sourceHead")
             and int(os.environ.get("GITHUB_RUN_ID", "0")) ==
                 candidate.get("originalOperatorRun"),
             "central source not joined to current authenticated operator run")
        run = get(f"repos/{CENTRAL}/actions/runs/{RUN_ID}")
        artifacts = get(f"repos/{CENTRAL}/actions/runs/{RUN_ID}/artifacts?per_page=100")
        with TemporaryDirectory(prefix="r11-central-original-") as tmp:
            need(bool(os.environ.get("GH_TOKEN")), "missing token for original download")
            p = subprocess.run(["gh", "run", "download", str(RUN_ID), "--repo", CENTRAL,
                                "--name", "fleet-upstream-watch", "--dir", tmp],
                               capture_output=True, text=True, timeout=180, check=False)
            need(p.returncode == 0, "original central snapshot download failed")
            scan = read_json(Path(tmp) / "fleet-upstream-watch.json")
        rows = scan.get("extensions") or []
        item = [v for v in rows if type(v) is dict and v.get("repository") == REPO]
        need(len(item) == 1, "original fleet row missing")
        sha = item[0].get("mainSha")
        need(type(sha) is str and SHA.fullmatch(sha), "unsafe scan main SHA")
        manifest = get(f"repos/{REPO}/contents/config/extension.json?ref={sha}")
        result = validate(candidate, run, artifacts, scan, manifest)
        Path("issue311-r11-central-original.json").write_text(
            json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print("R11_CENTRAL_HISTORICAL_SCAN_AUTHENTICATED; NEW_SIGNING_CAS_PUBLISH_DENY")
        return 0
    except (Denied, ValueError, KeyError, TypeError, OSError,
            subprocess.TimeoutExpired) as exc:
        print("R11_CENTRAL_SOURCE_DENY: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
