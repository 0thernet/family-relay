"""Offline contracts for identity isolation, safe output and real Xray config."""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("relay", ROOT / "relay.py")
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name).resolve()
        self.state_path = self.root / "private" / "state.json"
        self.state = relay.initial_state("railway", "relay.example.com", ["owner", "mom", "dad"])

    def tearDown(self):
        self.directory.cleanup()

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = relay.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_native_windows_setup_refuses_before_creating_files(self):
        with mock.patch.object(relay.os, "name", "nt"), mock.patch.object(relay, "state_lock") as lock:
            code, out, err = self.invoke("init", "--provider", "railway", "--host", "relay.example.com", "--users", "owner,mom", "--state", str(self.state_path))
        self.assertEqual(code, 1)
        self.assertIn("Ubuntu on WSL", err)
        self.assertIn("not /mnt/c", err)
        self.assertEqual(out, "")
        lock.assert_not_called()
        self.assertFalse(self.state_path.parent.exists())

    def test_state_roundtrip_is_private_and_fresh_init_never_overwrites(self):
        relay.save_state(self.state, self.state_path, fresh=True)
        before = self.state_path.read_bytes()
        self.assertEqual(relay.load_state(self.state_path), self.state)
        self.assertEqual(stat.S_IMODE(self.state_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.state_path.parent.stat().st_mode), 0o700)
        with self.assertRaises(relay.RelayError):
            relay.save_state(relay.initial_state("railway", "other.example.com", ["owner"]), self.state_path, fresh=True)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_state_lock_rejects_concurrent_mutation_and_cleans_up(self):
        with relay.state_lock(self.state_path):
            with self.assertRaises(relay.RelayError):
                with relay.state_lock(self.state_path):
                    self.fail("A second writer acquired the lock")
        self.assertFalse(self.state_path.with_name("state.json.lock").exists())

    def test_state_rejects_public_permissions(self):
        relay.save_state(self.state, self.state_path)
        self.state_path.chmod(0o644)
        with self.assertRaises(relay.RelayError):
            relay.load_state(self.state_path)

    def test_duplicate_json_fields_and_oversized_state_are_rejected(self):
        relay.write_private(self.state_path, '{"schema_version":1,"schema_version":1}')
        with self.assertRaises(relay.RelayError):
            relay.load_state(self.state_path)
        relay.write_private(self.state_path, " " * (relay.MAX_STATE_BYTES + 1))
        with self.assertRaises(relay.RelayError):
            relay.load_state(self.state_path)

    def test_symlink_output_and_state_are_rejected_without_target_changes(self):
        target = self.root / "original"
        target.write_text("untouched")
        linked = self.root / "link"
        linked.symlink_to(target)
        with self.assertRaises(relay.RelayError):
            relay.write_private(linked, "replacement")
        with self.assertRaises(relay.RelayError):
            relay.load_state(linked)
        self.assertEqual(target.read_text(), "untouched")
        parent_link = self.root / "linked-dir"
        parent_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(relay.RelayError):
            relay.write_private(parent_link / "another", "secret")
        self.assertFalse((self.root / "another").exists())

    def test_failed_write_leaves_old_file_and_no_partial_secret(self):
        relay.save_state(self.state, self.state_path)
        before = self.state_path.read_bytes()
        with mock.patch.object(relay.os, "replace", side_effect=OSError("test failure")):
            with self.assertRaises(OSError):
                relay.save_state(relay.mutate_user(self.state, "rotate", "mom"), self.state_path)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertEqual(list(self.state_path.parent.glob(".relay-write-*")), [])

    def test_revoke_removes_only_intended_auth_identity(self):
        revoked_id = relay.find_user(self.state, "mom")["id"]
        changed = relay.mutate_user(self.state, "revoke", "mom")
        clients = relay.server_config(changed)["inbounds"][0]["settings"]["clients"]
        self.assertEqual(len(clients), 2)
        self.assertNotIn(revoked_id, [client["id"] for client in clients])
        self.assertEqual(relay.find_user(changed, "dad"), relay.find_user(self.state, "dad"))
        with self.assertRaises(relay.RelayError):
            relay.client_uri(changed, "mom")
        self.assertEqual(len(self.state["users"]), 3)

    def test_rotate_revokes_previous_identity_and_keeps_other_users(self):
        original_id = relay.find_user(self.state, "mom")["id"]
        changed = relay.mutate_user(self.state, "rotate", "mom")
        self.assertNotEqual(original_id, relay.find_user(changed, "mom")["id"])
        self.assertEqual(relay.find_user(changed, "dad"), relay.find_user(self.state, "dad"))
        self.assertNotIn(original_id, json.dumps(relay.server_config(changed)))

    def test_add_duplicate_unknown_and_last_user_safety(self):
        changed = relay.mutate_user(self.state, "add", "sister")
        self.assertEqual(len(changed["users"]), 4)
        self.assertNotEqual(relay.find_user(changed, "sister")["id"], relay.find_user(changed, "mom")["id"])
        for operation, name in [("add", "mom"), ("revoke", "missing"), ("rotate", "missing")]:
            with self.subTest(operation=operation):
                with self.assertRaises(relay.RelayError):
                    relay.mutate_user(self.state, operation, name)
        single = relay.initial_state("railway", "relay.example.com", ["owner"])
        with self.assertRaises(relay.RelayError):
            relay.mutate_user(single, "revoke", "owner")
        self.assertEqual(len(single["users"]), 1)

    def test_bounded_user_count_and_untrusted_names(self):
        for name in ["", "Mom", "../mom", "mom;touch-pwned", "mom\nother", "$(id)", "a'", "é", "a" * 33]:
            with self.subTest(name=name):
                with self.assertRaises(relay.RelayError):
                    relay.initial_state("railway", "relay.example.com", [name])
        for names in [[], ["mom", "mom"], ["user" + str(i) for i in range(33)]]:
            with self.assertRaises(relay.RelayError):
                relay.initial_state("railway", "relay.example.com", names)
        full = relay.initial_state("railway", "relay.example.com", ["user" + str(i) for i in range(32)])
        with self.assertRaises(relay.RelayError):
            relay.mutate_user(full, "add", "extra")

    def test_host_validation_rejects_urls_paths_ports_and_injection(self):
        bad = ["https://relay.example.com", "relay.example.com/path", "relay.example.com:443", "relay.example.com?x=1", "relay.example.com#fragment", "relay.example.com;id", "relay.example.com\nOTHER=1", "$(id).example.com", "localhost", "127.0.0.1", "10.1.2.3", "169.254.169.254", "0.0.0.0", "::1", "2001:4860:4860::8888", "8.8.8.999", "123.456", "*.example.com", "-bad.example.com", "UPPER.example.com", "node.internal"]
        for host in bad:
            with self.subTest(host=host):
                with self.assertRaises(relay.RelayError):
                    relay.endpoint(host)
        self.assertEqual(relay.endpoint("8.8.8.8"), "8.8.8.8")
        self.assertEqual(relay.endpoint("family-relay-production.up.railway.app"), "family-relay-production.up.railway.app")
        with self.assertRaises(relay.RelayError):
            relay.initial_state("railway", "8.8.8.8", ["owner"])

    def test_invalid_schema_duplicate_uuid_and_canonical_uuid_validation(self):
        for value in [None, [], {}, {"schema_version": True}, {"schema_version": 2}, {"schema_version": 1, "provider": []}]:
            with self.assertRaises(relay.RelayError):
                relay.validate_state(value)
        wrong = copy.deepcopy(self.state)
        wrong["users"][1]["id"] = wrong["users"][0]["id"]
        with self.assertRaises(relay.RelayError):
            relay.validate_state(wrong)
        for value in ["not-an-id", self.state["users"][0]["id"].upper(), "00000000-0000-0000-0000-000000000000"]:
            wrong = copy.deepcopy(self.state)
            wrong["users"][0]["id"] = value
            with self.assertRaises(relay.RelayError):
                relay.validate_state(wrong)

    def test_railway_transport_and_certificate_verification_across_exports(self):
        uri = urlparse(relay.client_uri(self.state, "owner"))
        parameters = parse_qs(uri.query)
        self.assertEqual(uri.port, 443)
        self.assertEqual(uri.hostname, self.state["host"])
        self.assertEqual(parameters["path"], ["/relay-ws"])
        self.assertEqual(parameters["security"], ["tls"])
        self.assertEqual(parameters["allowInsecure"], ["0"])
        self.assertNotIn("flow", parameters)
        xray = relay.client_config(self.state, "owner")
        stream = xray["outbounds"][0]["streamSettings"]
        self.assertFalse(stream["tlsSettings"]["allowInsecure"])
        self.assertEqual(stream["wsSettings"]["headers"]["Host"], self.state["host"])
        self.assertEqual(xray["inbounds"][0]["listen"], "127.0.0.1")
        clash = relay.clash_config(self.state, "owner")
        self.assertFalse(clash["proxies"][0]["skip-cert-verify"])
        self.assertFalse(clash["allow-lan"])
        self.assertEqual(clash["rules"], ["MATCH,family relay"])
        server = relay.server_config(self.state)
        inbound = server["inbounds"][0]
        self.assertEqual(inbound["port"], 8080)
        self.assertEqual(inbound["streamSettings"]["security"], "none")
        self.assertEqual(inbound["streamSettings"]["wsSettings"]["path"], "/relay-ws")
        self.assertTrue(all("flow" not in user for user in inbound["settings"]["clients"]))

    def test_client_export_contains_only_intended_user(self):
        exports = [relay.client_uri(self.state, "mom"), json.dumps(relay.client_config(self.state, "mom")), json.dumps(relay.clash_config(self.state, "mom"))]
        for export in exports:
            self.assertIn(relay.find_user(self.state, "mom")["id"], export)
            self.assertNotIn(relay.find_user(self.state, "owner")["id"], export)
            self.assertNotIn(relay.find_user(self.state, "dad")["id"], export)

    def test_config_blocks_private_destinations_and_mail_without_broad_ad_filters(self):
        config = relay.server_config(self.state)
        rules = config["routing"]["rules"]
        self.assertEqual(len(rules), 2)
        self.assertIn("169.254.0.0/16", rules[0]["ip"])
        self.assertIn("fc00::/7", rules[0]["ip"])
        self.assertEqual(rules[1]["port"], "25,465,587")
        self.assertEqual(config["routing"]["domainStrategy"], "IPIfNonMatch")
        self.assertEqual(config["log"]["loglevel"], "warning")
        self.assertNotIn("geosite", json.dumps(config))

    @unittest.skipUnless(shutil.which("openssl"), "OpenSSL not installed")
    def test_reality_key_der_and_client_server_agreement(self):
        state = relay.initial_state("ovh", "8.8.8.8", ["owner", "mom"])
        keys = state["reality"]
        private = relay._raw_key(keys["private_key"])
        public = relay._raw_key(keys["public_key"])
        derived = subprocess.run([shutil.which("openssl"), "pkey", "-inform", "DER", "-pubout", "-outform", "DER"], input=relay.PRIVATE_DER_PREFIX + private, capture_output=True, check=True).stdout
        self.assertEqual(derived, relay.PUBLIC_DER_PREFIX + public)
        self.assertNotEqual(private, public)
        self.assertEqual(len(keys["short_id"]), 16)
        server = relay.server_config(state)["inbounds"][0]
        self.assertEqual(server["port"], 443)
        self.assertEqual(server["streamSettings"]["realitySettings"]["privateKey"], keys["private_key"])
        self.assertTrue(all(user["flow"] == "xtls-rprx-vision" for user in server["settings"]["clients"]))
        query = parse_qs(urlparse(relay.client_uri(state, "mom")).query)
        self.assertEqual(query["pbk"], [keys["public_key"]])
        self.assertEqual(query["sid"], [keys["short_id"]])
        self.assertEqual(query["flow"], ["xtls-rprx-vision"])
        self.assertEqual(query["fp"], ["chrome"])
        client = relay.client_config(state, "mom")
        self.assertEqual(client["outbounds"][0]["streamSettings"]["realitySettings"]["publicKey"], keys["public_key"])
        for exported in [relay.client_uri(state, "mom"), json.dumps(client), json.dumps(relay.clash_config(state, "mom"))]:
            self.assertNotIn(keys["private_key"], exported)
        self.assertEqual(relay.clash_config(state, "mom")["proxies"][0]["reality-opts"]["public-key"], keys["public_key"])
        for key, value in [("private_key", "a" * 42), ("public_key", "!" * 43), ("short_id", "00"), ("target", "evil.example.com:443")]:
            invalid = copy.deepcopy(state)
            invalid["reality"][key] = value
            with self.subTest(key=key), self.assertRaises(relay.RelayError):
                relay.validate_state(invalid)

    def test_unexpected_openssl_der_is_rejected(self):
        with mock.patch.object(relay.shutil, "which", return_value="/openssl"), mock.patch.object(relay.subprocess, "run", return_value=mock.Mock(stdout=b"unexpected")):
            with self.assertRaises(relay.RelayError):
                relay.generate_reality_keys()

    def test_cli_secrets_are_file_only_and_env_is_valid_dotenv(self):
        code, out, err = self.invoke("init", "--provider", "railway", "--host", "relay.example.com", "--users", "owner,mom", "--state", str(self.state_path))
        self.assertEqual((code, err), (0, ""))
        state = relay.load_state(self.state_path)
        for user in state["users"]:
            self.assertNotIn(user["id"], out)
        for format_name in ["uri", "clash", "xray"]:
            output = self.root / ("mom." + format_name)
            code, out, err = self.invoke("--state", str(self.state_path), "export", "mom", "--format", format_name, "--output", str(output))
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertIn(relay.find_user(state, "mom")["id"], output.read_text())
            self.assertNotIn(relay.find_user(state, "mom")["id"], out)
        env = self.root / "railway.env"
        code, out, err = self.invoke("env", "--state", str(self.state_path), "--output", str(env))
        self.assertEqual((code, err), (0, ""))
        payload = env.read_text().removeprefix("RELAY_CONFIG_JSON='").removesuffix("'\n")
        self.assertEqual(json.loads(payload), relay.server_config(state))
        self.assertNotIn("'", payload)
        for command in ["status", "validate"]:
            code, out, err = self.invoke(command, "--state", str(self.state_path))
            self.assertEqual((code, err), (0, ""))
            for user in state["users"]:
                self.assertNotIn(user["id"], out)

    def test_cli_does_not_overwrite_state_with_an_export(self):
        relay.save_state(self.state, self.state_path)
        before = self.state_path.read_bytes()
        code, _, _ = self.invoke("export", "owner", "--state", str(self.state_path), "--format", "uri", "--output", str(self.state_path))
        self.assertEqual(code, 1)
        self.assertEqual(self.state_path.read_bytes(), before)
        code, _, _ = self.invoke("render", "--state", str(self.state_path), "--output", str(self.state_path) + ".lock")
        self.assertEqual(code, 1)
        self.assertFalse(self.state_path.with_name("state.json.lock").exists())

    def test_cli_user_mutation_requires_deploy_and_all_state_flag_positions_work(self):
        relay.save_state(self.state, self.state_path)
        code, out, err = self.invoke("user", "--state", str(self.state_path), "add", "sister")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("redeploy", out)
        code, _, _ = self.invoke("user", "revoke", "sister", "--state", str(self.state_path))
        self.assertEqual(code, 0)
        code, _, _ = self.invoke("--state", str(self.state_path), "user", "rotate", "mom")
        self.assertEqual(code, 0)

    @unittest.skipUnless(shutil.which("xray") and shutil.which("openssl"), "Xray/OpenSSL not installed")
    def test_real_xray_accepts_server_and_client_configs_for_both_providers(self):
        for provider, host in [("railway", "relay.example.com"), ("ovh", "8.8.8.8")]:
            state = relay.initial_state(provider, host, ["owner", "mom"])
            relay.validate_xray(state, shutil.which("xray"))
            client_path = self.root / (provider + "-client.json")
            relay.write_private(client_path, json.dumps(relay.client_config(state, "mom")))
            result = subprocess.run([shutil.which("xray"), "run", "-test", "-config", str(client_path)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, "Xray rejected the client configuration (raw output withheld to protect secrets)")


if __name__ == "__main__":
    unittest.main()
