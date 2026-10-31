#!/usr/bin/env python3
"""Offline receipt retention/authentication regression. No actual dispatch."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
m = load("dispatch_observation", "scripts/issue311-dispatch-input-observation.py")
gate = m.gate

def fixture():
    env = {"GITHUB_REPOSITORY": gate.REPO, "GITHUB_WORKFLOW": gate.WORKFLOW,
           "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
           "GITHUB_ACTOR": gate.BOT, "GITHUB_RUN_ATTEMPT": "1",
           "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "1234", "SECRET_SENTINEL": "never-copy"}
    event = {"repository": {"full_name": gate.REPO}, "ref": "refs/heads/main",
             "sender": {"login": gate.BOT, "id": gate.BOT_ID, "type": "Bot"},
             "untrustedExtra": "never-copy",
             "inputs": {"request_id": gate.REQUEST_ID, "source_run_id": "123",
                        "source_head_sha": "b" * 40, "source_artifact_id": "456",
                        "source_zip_sha256": "c" * 64,
                        "central_request_id": "r-20261030-r06preparecoord001",
                        "local_main_sha": "a" * 40}}
    return event, env

class ObservationTests(unittest.TestCase):
    def test_exact_seven_inputs_no_grant_or_secret(self):
        event, env = fixture(); out = m.observe(event, env)
        self.assertEqual(out["inputs"], event["inputs"])
        self.assertEqual(out["inputsSha256"], hashlib.sha256(m.canonical(event["inputs"])).hexdigest())
        self.assertEqual(out["runId"], 1234)
        self.assertFalse(out["centralSourceAdmissionVerified"])
        self.assertFalse(out["childPrepareCompleted"])
        self.assertFalse(out["publicationAuthorized"])
        self.assertNotIn(b"never-copy", m.canonical(out))
        self.assertEqual(m.canonical(out), m.canonical(m.observe(event, env)))

    def test_forged_event_attempt_head_extra_input_and_missing_input_denied(self):
        event, env = fixture()
        for key, value in (("GITHUB_ACTOR", "ShutenOishi"), ("GITHUB_RUN_ATTEMPT", "2"),
                           ("GITHUB_EVENT_NAME", "schedule"), ("GITHUB_SHA", "f" * 40),
                           ("GITHUB_REF", "refs/heads/dev")):
            with self.subTest(key=key), self.assertRaises(gate.Denied):
                m.observe(event, dict(env, **{key: value}))
        for key in gate.FIELDS:
            bad = copy.deepcopy(event); del bad["inputs"][key]
            with self.subTest(missing=key), self.assertRaises(gate.Denied):
                m.observe(bad, env)
        bad = copy.deepcopy(event); bad["inputs"]["mode"] = "PUBLISH"
        with self.assertRaises(gate.Denied): m.observe(bad, env)
        bad = copy.deepcopy(event); bad["sender"]["id"] = 1
        with self.assertRaises(gate.Denied): m.observe(bad, env)

    def test_receipt_uploaded_before_prepare_and_postmerge_tests_exist(self):
        workflow = (ROOT / ".github/workflows/issue311-request-local-prepare.yml").read_text()
        observation = workflow.split("\n  dispatch_input_observation:", 1)[1].split("\n  app_local_prepare:", 1)[0]
        prepare = workflow.split("\n  app_local_prepare:", 1)[1].split("\n  # R08:", 1)[0]
        self.assertIn("needs: dispatch_input_observation", prepare)
        self.assertIn("needs.dispatch_input_observation.result == 'success'", prepare)
        for required in ("github.event_name == 'workflow_dispatch'", "github.run_attempt == 1",
                         "scripts/issue311-dispatch-input-observation.py", "if-no-files-found: error",
                         "name: issue311-dispatch-input-observation"):
            self.assertIn(required, observation)
        self.assertNotIn("id-token: write", observation)
        self.assertNotIn("contents: write", observation)
        self.assertIn("github.event_name == 'push'", workflow.split("\n  offline_policy:", 1)[1].split("\n  dispatch_input_observation:", 1)[0])

if __name__ == "__main__": unittest.main()
