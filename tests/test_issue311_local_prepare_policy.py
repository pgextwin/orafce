#!/usr/bin/env python3
"""Security invariant checks for the dedicated nonpublishing PREPARE pilot."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LocalPreparePolicy(unittest.TestCase):
    def test_local_workflow_is_readonly_and_exact(self):
        text = (ROOT / ".github/workflows/issue311-local-prepare.yml").read_text()
        self.assertIn("r-20261029-r06localpilot01.json", text)
        self.assertIn("05d78b6cb1eebfdb671aca382431fb0c89cf43e2", text)
        self.assertIn("persist-credentials: false", text)
        for forbidden in ("schedule:", "workflow_dispatch:", "contents: write",
                          "pull-requests: write", "secrets.", "id-token: write",
                          "gh release ", "PUBLISH=ALLOW", "repository_dispatch:"):
            active_lines = [line.strip() for line in text.splitlines()
                            if line.strip() and not line.lstrip().startswith("#")]
            self.assertNotIn(forbidden, active_lines)

    def test_local_proof_never_grants_candidate_writer(self):
        text = (ROOT / "scripts/issue311-local-prepare.py").read_text()
        for evidence in ("bridge.original_zip(", "contract.validate_declaration(",
                         'data["mode"] == "PREPARE"', "authenticate_local",
                         "authenticate_original", "protected", "SHA40",
                         "candidateAdmissionAuthorized", "publisherSourceKindAuthorized"):
            self.assertIn(evidence, text)
        for forbidden in ("workflow_dispatch", "create_pull_request", "GITHUB_TOKEN_WRITE",
                          "candidate-update.py", "git push", "PUBLISH=ALLOW"):
            self.assertNotIn(forbidden, text)

if __name__ == "__main__":
    unittest.main()
