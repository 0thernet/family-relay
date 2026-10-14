"""Offline coverage for explicit Railway targeting and secret-only stdin."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("railway_apply", ROOT / "scripts" / "railway-apply.py")
apply = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apply)
PROJECT = "12345678-1234-4234-8234-123456789abc"


class RailwayApplyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.state_path = Path(self.directory.name).resolve() / "private" / "state.json"
        self.state = apply.relay.initial_state("railway", "relay.example.com", ["owner", "mom"])
        apply.relay.save_state(self.state, self.state_path)
        self.base_args = ["--project", PROJECT, "--state", str(self.state_path)]

    def tearDown(self):
        self.directory.cleanup()

    def invoke(self, extra=()):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = apply.main(self.base_args + list(extra))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_sets_only_relay_config_via_stdin_with_explicit_target_and_no_deploy(self):
        expected_payload = apply.relay.server_config(self.state)
        secret = self.state["users"][0]["id"]
        result = subprocess.CompletedProcess([], 0, stdout=secret, stderr=secret)
        with mock.patch.object(apply.shutil, "which", return_value="/tools/railway"), mock.patch.object(apply.subprocess, "run", return_value=result) as run:
            code, out, err = self.invoke(["--service", "my-relay", "--environment", "staging"])
        self.assertEqual((code, err), (0, ""))
        run.assert_called_once()
        positional, options = run.call_args
        self.assertEqual(positional[0], ["/tools/railway", "variable", "set", "RELAY_CONFIG_JSON", "--stdin", "--skip-deploys", "--project", PROJECT, "--service", "my-relay", "--environment", "staging"])
        self.assertEqual(json.loads(options["input"]), expected_payload)
        self.assertTrue(options["capture_output"])
        self.assertTrue(options["text"])
        self.assertEqual(options["timeout"], 45)
        self.assertNotIn("shell", options)
        self.assertIn(PROJECT, out)
        self.assertIn("my-relay", out)
        self.assertNotIn(secret, repr(positional))
        self.assertNotIn(secret, out + err)

    def test_defaults_service_and_environment(self):
        with mock.patch.object(apply.shutil, "which", return_value="railway"), mock.patch.object(apply.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            code, _, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(run.call_args.args[0][-4:], ["--service", "relay", "--environment", "production"])

    def test_failed_cli_output_is_never_printed(self):
        secret = self.state["users"][0]["id"]
        with mock.patch.object(apply.shutil, "which", return_value="railway"), mock.patch.object(apply.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, secret, secret)):
            code, out, err = self.invoke()
        self.assertEqual(code, 1)
        self.assertNotIn(secret, out + err)
        self.assertIn("dashboard before retrying", err)

    def test_timeout_reports_unknown_outcome_without_leaking_captured_output(self):
        secret = self.state["users"][0]["id"]
        error = subprocess.TimeoutExpired("railway", 45, output=secret, stderr=secret)
        with mock.patch.object(apply.shutil, "which", return_value="railway"), mock.patch.object(apply.subprocess, "run", side_effect=error):
            code, out, err = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("may have succeeded", err)
        self.assertIn("before retrying", err)
        self.assertNotIn(secret, out + err)

    def test_missing_cli_has_readable_error_and_no_provider_call(self):
        with mock.patch.object(apply.shutil, "which", return_value=None), mock.patch.object(apply.subprocess, "run") as run:
            code, _, err = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("Install it", err)
        run.assert_not_called()

    def test_operating_system_error_is_sanitized(self):
        secret = self.state["users"][0]["id"]
        with mock.patch.object(apply.shutil, "which", return_value="railway"), mock.patch.object(apply.subprocess, "run", side_effect=OSError(secret)):
            code, out, err = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("could not run", err)
        self.assertNotIn(secret, out + err)

    def test_wrong_provider_and_invalid_state_stop_before_cli_call(self):
        # Provider validation happens after canonical state validation. Mock a
        # validated OVH result to avoid requiring OpenSSL in this helper test.
        for state in [{"provider": "ovh"}, None]:
            load = mock.patch.object(apply.relay, "load_state", return_value=state) if state else mock.patch.object(apply.relay, "load_state", side_effect=apply.relay.RelayError("Invalid state."))
            with load, mock.patch.object(apply.subprocess, "run") as run:
                code, _, _ = self.invoke()
            self.assertEqual(code, 1)
            run.assert_not_called()

    def test_target_validation_prevents_option_or_shell_injection(self):
        for extra in [["--project", "not-a-uuid"], ["--project", "00000000-0000-0000-0000-000000000000"], ["--service=--delete"], ["--environment", "production;touch bad"], ["--service", "relay\n--other"]]:
            with self.subTest(extra=extra), mock.patch.object(apply.subprocess, "run") as run:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    apply.main(self.base_args + extra)
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
