#!/usr/bin/env python3
"""R11-B01: original public upstream tag proof, controlled READ-ONLY boundary.

This is NOT update discovery, an eligible new stable, candidate Writer, State
transition, signing, or publication acceptance. The three real authenticated
GitHub GETs cannot be replaced by mock evidence for the original receipt.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

UPSTREAM = "orafce/orafce"
REPOSITORY = "pgextwin/orafce"
TAG = "VERSION_4_17_1"
TAG_OBJECT_SHA = "4003faf7b57d2a97d56051e06f9af677a6c42405"
PINNED_COMMIT = "542aed2e0297898cc9844fede3c4452f894b37ed"
OUTPUT = Path("r11-controlled-upstream-readonly-original.json")
ENDPOINTS = {
    "release": "releases/tags/" + TAG,
    "ref": "git/ref/tags/" + TAG,
    "tag": "git/tags/" + TAG_OBJECT_SHA,
}
SHA = re.compile(r"[0-9a-f]{40}\Z")


class Denied(ValueError):
    pass


def require(value, message):
    if not value:
        raise Denied(message)


def unique(items):
    out = {}
    for name, value in items:
        require(name not in out, "duplicate JSON field")
        out[name] = value
    return out


def github_get(endpoint):
    require(endpoint in ENDPOINTS.values(), "endpoint outside exact GET allowlist")
    require(bool(os.environ.get("GH_TOKEN")), "authenticated GET token missing")
    result = subprocess.run(
        ["gh", "api", "--method", "GET", "repos/" + UPSTREAM + "/" + endpoint],
        capture_output=True, text=True, timeout=40, check=False)
    require(result.returncode == 0 and 0 < len(result.stdout) < 1000000,
            "upstream authenticated GET failed")
    return json.loads(result.stdout, object_pairs_hook=unique)


def validate(config, release, ref, tag, env):
    require(env.get("GITHUB_REPOSITORY") == REPOSITORY
            and env.get("GITHUB_EVENT_NAME") == "pull_request"
            and env.get("GITHUB_RUN_ATTEMPT") == "1"
            and bool(SHA.fullmatch(env.get("GITHUB_SHA", "")))
            and str(env.get("GITHUB_RUN_ID", "")).isdigit()
            and int(env["GITHUB_RUN_ID"]) > 0,
            "not an original protected-PR controlled read-only run")
    require(type(config) is dict and config.get("name") == "orafce"
            and config.get("upstream", {}).get("repository") == UPSTREAM
            and config["upstream"].get("ref") == TAG
            and config["upstream"].get("version") == "4.17.1"
            and config["upstream"].get("commit") == PINNED_COMMIT,
            "configured original upstream is not the pinned historic stable")
    require(type(release) is dict and release.get("tag_name") == TAG
            and release.get("draft") is False
            and release.get("prerelease") is False
            and type(release.get("published_at")) is str
            and release["published_at"].endswith("Z")
            and release.get("id", 0) > 0
            and release.get("html_url") ==
                 "https://github.com/orafce/orafce/releases/tag/" + TAG,
            "upstream public Release identity not verified")
    require(type(ref) is dict and ref.get("ref") == "refs/tags/" + TAG
            and type(ref.get("object")) is dict
            and ref["object"].get("type") == "tag"
            and ref["object"].get("sha") == TAG_OBJECT_SHA,
            "annotated tag ref moved or mutated")
    require(type(tag) is dict and tag.get("tag") == TAG
            and tag.get("sha") == TAG_OBJECT_SHA
            and type(tag.get("object")) is dict
            and tag["object"].get("type") == "commit"
            and tag["object"].get("sha") == PINNED_COMMIT,
            "annotated tag object does not pin configured commit")
    return {
        "schemaVersion": 1,
        "classification": "CONTROLLED_INTEGRATION_READONLY_ONLY",
        "repository": REPOSITORY, "upstream": UPSTREAM,
        "originalCiRun": int(env["GITHUB_RUN_ID"]),
        "originalCiAttempt": 1, "originalWorkflowCheckoutSha": env["GITHUB_SHA"],
        "sourceEvent": "pull_request",
        "release": TAG, "releaseId": release["id"],
        "releasePublishedAt": release["published_at"],
        "tagObjectSha": TAG_OBJECT_SHA, "pinnedCommitSha": PINNED_COMMIT,
        "providerGetEndpoints": list(ENDPOINTS.values()),
        "realProviderGetCount": 3,
        "newStableVerified": False,
        "nonemptyIssueWriteVerified": False,
        "nonemptyDraftWriteVerified": False,
        "nativeCandidateDispatchVerified": False,
        "legacyNewWriterCollisionVerified": False,
        "publicationAuthorized": False, "runtimeEnabled": False,
        "writesPerformed": 0,
    }


def main():
    try:
        require(Path("config/extension.json").is_file(), "manifest unavailable")
        config = json.loads(Path("config/extension.json").read_text("utf-8"),
                            object_pairs_hook=unique)
        values = {name: github_get(endpoint)
                  for name, endpoint in ENDPOINTS.items()}
        receipt = validate(config, values["release"], values["ref"],
                           values["tag"], os.environ)
        OUTPUT.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                          encoding="utf-8")
        print("R11_CONTROLLED_UPSTREAM_TRUE_PROVIDER_READONLY_PASS")
    except (Denied, ValueError, KeyError, TypeError, OSError,
            subprocess.SubprocessError) as exc:
        print("R11_CONTROLLED_UPSTREAM_DENY: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
