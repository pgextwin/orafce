#!/usr/bin/env python3
"""Offline guard for two nonpublishing, exact-request GitHub Actions negatives.

A skipped job and a timed-out step are real Actions outcomes only when
subsequent protected one-shot originals prove them. This test does not itself
claim any original run or natural GitHub transport failure.
"""
from pathlib import Path
workflow=Path(".github/workflows/issue311-request-local-prepare.yml").read_text()
skip="r-20261030-r06preparelocalskip08"
timeout="r-20261030-r06preparelocaltimeout09"
assert workflow.count(skip)==1, "skip must be scoped to one immutable central request"
assert workflow.count(timeout)==1, "timeout must be scoped to one immutable central request"
assert f"github.event.inputs.central_request_id != '{skip}'" in workflow
assert f"github.event.inputs.central_request_id == '{timeout}'" in workflow
assert 'timeout-minutes: 1\n        run: python -c "import time; time.sleep(90)"' in workflow
assert "github.actor == 'pgextwin-issue311-prepare-coord[bot]'" in workflow
assert "github.ref == 'refs/heads/main'" in workflow
assert "github.run_attempt == 1" in workflow
assert "no RELEASE" in workflow.lower() or "NO RELEASE" in workflow
assert 'workflow_dispatch:' in workflow
assert "Strict actual App event" in workflow
assert "issue311-app-local-prepare-receipt.json" in workflow
print("R06_ORAFCE_REAL_LOCAL_SKIP_TIMEOUT_CANARY_OFFLINE_POLICY_PASS")
