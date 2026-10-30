#!/usr/bin/env python3
"""Offline fake-bot and cross-repo denial, without credentials or dispatch."""
import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "actor", Path("scripts/issue311-coordinator-actor-pilot.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
context = {
    "GITHUB_REPOSITORY": "pgextwin/orafce",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_ACTOR": m.APP_BOT,
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_SHA": "1" * 40,
    "GITHUB_RUN_ID": "123456",
}
event = {
    "repository": {"full_name": "pgextwin/orafce"},
    "ref": "refs/heads/main",
    "sender": {"login": m.APP_BOT, "id": m.BOT_USER_ID, "type": "Bot"},
    "inputs": {"request_id": m.REQUEST_ID},
}
assert m.verify(event, context)["publicReleaseAuthorized"] is False

def denied(ev, ctx):
    try:
        m.verify(ev, ctx)
    except m.Rejected:
        return
    raise AssertionError("forged event accepted")

for name, value in [
    ("GITHUB_ACTOR", "ShutenOishi"),
    ("GITHUB_REPOSITORY", "pgextwin/build"),
    ("GITHUB_EVENT_NAME", "push"),
    ("GITHUB_REF", "refs/tags/v1"),
    ("GITHUB_RUN_ATTEMPT", "2"),
]:
    ctx = dict(context, **{name: value})
    denied(event, ctx)
for name, value in [
    ("sender", {"login": m.APP_BOT, "id": 350058023, "type": "Bot"}),
    ("ref", "refs/heads/feature"),
    ("inputs", {"request_id": "PUBLISH"}),
    ("inputs", {"request_id": m.REQUEST_ID, "publish": "true"}),
]:
    ev = copy.deepcopy(event)
    ev[name] = value
    denied(ev, context)
print("ISSUE311_BOT_ACTOR_OFFLINE_DENY_PASS")
