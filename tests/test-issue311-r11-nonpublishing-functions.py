#!/usr/bin/env python3
"""Read-only R11 functional adapter hostile contract; cannot prove live acceptance."""
from pathlib import Path
import re

body=Path(".github/workflows/issue311-r11-event-source.yml").read_text("utf-8")
PIN="19477b9440ce809fbadbd4fc0c7fadfd40a4a78f"
def check(yml):
    assert "  schedule:" not in yml and "workflow_dispatch:" not in yml
    assert '      - ".github/issue311-r11-intents/*.json"' in yml
    assert "github.actor == 'ShutenOishi'" in yml and "github.run_attempt == 1" in yml
    assert "Authentic" not in yml or "R11" in yml
    m=re.search(r"(?ms)^  operator_readonly_functions:\n(.*)\Z",yml)
    assert m
    x=m.group(1)
    assert "needs: source_observation" in x
    assert "needs.source_observation.result == 'success'" in x
    assert "ref: "+PIN in x
    assert "scripts/check-upstream-update.py" in x
    assert "scripts/reconcile-update-issue.py" in x
    assert "scripts/candidate-update.py plan" in x
    assert "scripts/fleet-control.py" in x
    assert " --dry-run" in x
    assert " --action candidate" in x
    assert " steps.candidate_gate.outputs.allowed == 'true'" in x
    assert " steps.watch_gate.outputs.allowed == 'true'" in x
    assert "persist-credentials: false" in x
    assert not re.search(r"^\s+(issues|contents|pull-requests|actions): write\s*$", x, re.M)
    assert "candidate-update.py propose" not in x
    assert "scheduleRemoved" not in x and "--action publish" not in x
    assert '--output "$RUNNER_TEMP/candidate-plan.json"' in x
    assert "r11-operator-functions-readonly-original" in x
check(body)
for old,new in (
    (" --dry-run"," --not-dry-run"),
    ("needs: source_observation","needs: offline_negatives"),
    ("      issues: read","      issues: write"),
    ("ref: "+PIN,"ref: main"),
    ("      - \".github/issue311-r11-intents/*.json\"","      - \"README.md\""),
    ("--action candidate","--action publish"),
    ("--output \"$RUNNER_TEMP/candidate-plan.json\"","--output \"./candidate-plan.json\""),
):
    changed=body.replace(old,new,1)
    if changed==body: continue
    try: check(changed)
    except AssertionError: pass
    else: raise AssertionError("hostile adapter mutation admitted: "+old)
print("R11_FUNCTIONAL_PILOT_READONLY_HOSTILE_PASS")
