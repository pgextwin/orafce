#!/usr/bin/env python3
"""One-shot genuine coordinator App actor probe. Read-only, no PREPARE/Release."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess

REPOSITORY = "pgextwin/orafce"
APP_BOT = "pgextwin-issue311-prepare-coord[bot]"
BOT_USER_ID = 350058024
REQUEST_ID = "r-20261030-r06coordactorpilot01"
SHA = re.compile(r"^[0-9a-f]{40}$")


class Rejected(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Rejected(reason)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate event field")
        result[key] = value
    return result


def verify(event, context):
    require(context.get("GITHUB_REPOSITORY") == REPOSITORY and
            context.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and
            context.get("GITHUB_REF") == "refs/heads/main" and
            context.get("GITHUB_ACTOR") == APP_BOT and
            context.get("GITHUB_RUN_ATTEMPT") == "1",
            "not original trusted App bot workflow_dispatch")
    require(event.get("repository", {}).get("full_name") == REPOSITORY and
            event.get("ref") == "refs/heads/main",
            "untrusted repository/ref")
    sender = event.get("sender", {})
    require(sender.get("login") == APP_BOT and sender.get("type") == "Bot" and
            sender.get("id") == BOT_USER_ID, "real sender bot ID mismatch")
    require(event.get("inputs") == {"request_id": REQUEST_ID}, "wrong one-shot request or added inputs")
    require(SHA.fullmatch(context.get("GITHUB_SHA", "")), "invalid original event HEAD")
    run_id = context.get("GITHUB_RUN_ID", "")
    require(run_id.isdecimal() and int(run_id) > 0, "missing original Run ID")
    return {
        "schemaVersion": 1, "mode": "AUDIT_ONLY", "workflowDispatch": True,
        "actorLogin": APP_BOT, "actorUserId": BOT_USER_ID,
        "requestId": REQUEST_ID, "eventName": "workflow_dispatch",
        "repository": REPOSITORY, "headSha": context["GITHUB_SHA"],
        "runId": int(run_id), "runAttempt": 1,
        "publisherAuthorized": False, "publicReleaseAuthorized": False,
        "localPrepareExecuted": False, "credentialAvailable": False,
    }


def main():
    raw = Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes()
    event = json.loads(raw, object_pairs_hook=unique)
    receipt = verify(event, os.environ)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    require(receipt["headSha"] == head, "checkout/event SHA mismatch")
    path = Path("issue311-coordinator-actor-original.json")
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("ISSUE311_REAL_COORDINATOR_BOT_WORKFLOW_DISPATCH", json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
