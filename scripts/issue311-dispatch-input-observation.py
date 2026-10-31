#!/usr/bin/env python3
"""Retain exact authenticated transport inputs before PREPARE can skip/timeout.

This is an observation, NEVER central ZIP/source admission, a successful child
receipt, signing intent, publication permission or an authenticated State CAS.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("app_input_gate", ROOT / "scripts/issue311-app-local-prepare.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
OUTPUT = "issue311-dispatch-input-observation.json"

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")

def observe(event, env):
    inputs = gate.authenticate_event(event, env)
    # Copy only the seven declared non-secret string inputs and fixed identity.
    # Do not archive arbitrary event/environment fields or credentials.
    original = {key: inputs[key] for key in sorted(gate.FIELDS)}
    return {"schemaVersion": 1, "scope": "AUTHENTICATED_DISPATCH_INPUT_OBSERVATION_ONLY",
            "repository": gate.REPO, "workflow": gate.WORKFLOW,
            "runId": int(env["GITHUB_RUN_ID"]), "attempt": 1,
            "headSha": env["GITHUB_SHA"], "event": "workflow_dispatch",
            "sender": {"login": gate.BOT, "id": gate.BOT_ID, "type": "Bot"},
            "inputs": original, "inputsSha256": hashlib.sha256(canonical(original)).hexdigest(),
            "centralSourceAdmissionVerified": False, "childPrepareCompleted": False,
            "candidateAdmissionAuthorized": False, "publicationAuthorized": False,
            "runtimeEnabled": False}

def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes(), object_pairs_hook=gate.unique)
    raw = canonical(observe(event, os.environ))
    path = Path(OUTPUT)
    gate.need(not path.exists(), "never overwrite original dispatch observation")
    path.write_bytes(raw)
    print("DISPATCH_INPUT_OBSERVATION_ONLY_SHA256", hashlib.sha256(raw).hexdigest())

if __name__ == "__main__":
    main()
