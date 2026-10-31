#!/usr/bin/env python3
"""Bounded static guard for R11 functional dry-run migration. NOT live acceptance."""
from pathlib import Path
import re

PATH = Path(".github/workflows/issue311-r11-event-source.yml")
body = PATH.read_text(encoding="utf-8")
SOURCE = "source_observation"
PIN = "19477b9440ce809fbadbd4fc0c7fadfd40a4a78f"

def check(yml: str) -> None:
    assert "  schedule:" not in yml and "workflow_dispatch:" not in yml
    assert '      - ".github/issue311-r11-intents/*.json"' in yml
    assert "github.actor == 'ShutenOishi'" in yml
    assert "github.run_attempt == 1" in yml
    assert "      - name: Authenticate real protected push and exact immutable one-file intent" in yml
    for job, workflow in (
        ("operator_issue_reconcile_dry_run", "check-extension-updates.yml"),
        ("operator_candidate_plan_dry_run", "candidate-update.yml"),
    ):
        m = re.search(r"(?ms)^  " + job + r":\n(.*?)(?=^  [a-z][a-z0-9_]*:|\Z)", yml)
        assert m, "missing real functional pilot: " + job
        section = m.group(1)
        assert "needs: " + SOURCE in section
        assert "needs.source_observation.result == 'success'" in section
        assert "uses: pgextwin/build/.github/workflows/" + workflow + "@" + PIN in section
        assert "dry_run: true" in section
        assert not re.search(r"\b(contents|issues|pull-requests|actions): write\b", section)
        assert not re.search(r"\b(dry_run: false|github.event_name == 'schedule')\b", section)
    assert "          python tests/test-issue311-r11-nonpublishing-functions.py" in yml

check(body)
for bad in (
    body.replace("dry_run: true", "dry_run: false", 1),
    body.replace("needs: source_observation", "needs: offline_negatives", 1),
    body.replace("      issues: read", "      issues: write", 1),
    body.replace('      - ".github/issue311-r11-intents/*.json"', '      - "README.md"', 1),
):
    try:
        check(bad)
    except AssertionError:
        pass
    else:
        raise AssertionError("hostile contract mutation admitted")
print("R11_OPERATOR_FUNCTIONAL_READONLY_CONTRACT_PASS; NO_CRON_NO_WRITER_NO_PUBLISH")
