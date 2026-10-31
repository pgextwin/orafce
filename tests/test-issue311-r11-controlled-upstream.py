#!/usr/bin/env python3
"""Hostile offline controls for the read-only original upstream GitHub pilot."""
import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "controlled_upstream", Path("scripts/issue311-r11-controlled-upstream.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

config = {"name": "orafce", "upstream": {
    "repository": "orafce/orafce", "ref": m.TAG,
    "version": "4.17.1", "commit": m.PINNED_COMMIT}}
release = {"tag_name": m.TAG, "id": 123, "draft": False,
           "prerelease": False, "published_at": "2026-10-14T07:08:12Z",
           "html_url": "https://github.com/orafce/orafce/releases/tag/" + m.TAG}
ref = {"ref": "refs/tags/" + m.TAG,
       "object": {"type": "tag", "sha": m.TAG_OBJECT_SHA}}
tag = {"sha": m.TAG_OBJECT_SHA, "tag": m.TAG,
       "object": {"type": "commit", "sha": m.PINNED_COMMIT}}
env = {"GITHUB_REPOSITORY": "pgextwin/orafce",
       "GITHUB_EVENT_NAME": "pull_request",
       "GITHUB_RUN_ATTEMPT": "1",
       "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "41220000001"}

def accept(c=config, r=release, f=ref, t=tag, e=env):
    return m.validate(c, r, f, t, e)

result = accept()
assert result["classification"] == "CONTROLLED_INTEGRATION_READONLY_ONLY"
assert result["realProviderGetCount"] == 3
assert result["writesPerformed"] == 0
assert all(result[x] is False for x in (
    "newStableVerified", "nonemptyIssueWriteVerified",
    "nonemptyDraftWriteVerified", "nativeCandidateDispatchVerified",
    "legacyNewWriterCollisionVerified", "publicationAuthorized",
    "runtimeEnabled"))
assert set(m.ENDPOINTS) == {"release", "ref", "tag"}

def denied(c=config, r=release, f=ref, t=tag, e=env):
    try:
        accept(c, r, f, t, e)
    except (m.Denied, ValueError, KeyError, TypeError):
        return
    raise AssertionError("dangerous source mutation accepted")

for key, value in (("repository", "attacker/repo"),
                   ("ref", "VERSION_4_18_0"),
                   ("commit", "b" * 40)):
    v = copy.deepcopy(config)
    v["upstream"][key] = value
    denied(c=v)
for key, value in (("tag_name", "VERSION_4_18_0"),
                   ("draft", True), ("prerelease", True),
                   ("id", 0), ("published_at", "n/a"),
                   ("html_url", "https://evil.example")):
    v = copy.deepcopy(release)
    v[key] = value
    denied(r=v)
for key, value in (("ref", "refs/heads/main"),
                   ("object", {"type": "commit", "sha": m.PINNED_COMMIT})):
    v = copy.deepcopy(ref)
    v[key] = value
    denied(f=v)
for key, value in (("tag", "VERSION_4_18_0"), ("sha", "b" * 40),
                   ("object", {"type": "commit", "sha": "b" * 40})):
    v = copy.deepcopy(tag)
    v[key] = value
    denied(t=v)
for key, value in (("GITHUB_EVENT_NAME", "schedule"),
                   ("GITHUB_RUN_ATTEMPT", "2"),
                   ("GITHUB_SHA", "bad"), ("GITHUB_RUN_ID", "0"),
                   ("GITHUB_REPOSITORY", "pgextwin/build")):
    v = dict(env)
    v[key] = value
    denied(e=v)
try:
    m.unique([("tag", 1), ("tag", 2)])
except m.Denied:
    pass
else:
    raise AssertionError("duplicate JSON keys accepted")
try:
    m.github_get("actions/workflows/promote.yml/dispatches")
except m.Denied:
    pass
else:
    raise AssertionError("write endpoint escaped exact read-only allowlist")
print("R11_REAL_TAG_CONTROLLED_READONLY_HOSTILE_PASS")
