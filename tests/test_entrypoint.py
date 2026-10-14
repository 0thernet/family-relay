"""Offline runtime contracts; no production credentials or provider access."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid


SOURCE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("relay_entrypoint", SOURCE / "docker" / "entrypoint.py")
assert SPEC and SPEC.loader
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


def configuration() -> dict:
    return {"log": {"loglevel": "debug", "access": "/tmp/leak"}, "inbounds": [{"listen": "0.0.0.0", "port": 8080, "protocol": "vless", "settings": {"clients": [{"id": str(uuid.uuid4())}], "decryption": "none"}, "streamSettings": {"network": "ws", "security": "none", "wsSettings": {"path": "/relay-ws"}}}], "outbounds": [{"protocol": "freedom"}]}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="relay-runtime-test-")
        self.root = Path(self.temp.name)
        self.mount = self.root / "mounted.json"
        self.runtime = self.root / "runtime"
        self.config = configuration()
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def mounted(self, config=None):
        self.mount.write_text(json.dumps(self.config if config is None else config))
        self.mount.chmod(0o600)

    def test_environment_removed_and_logs_disabled_before_engine(self):
        secret = json.dumps(self.config)
        os.environ["RELAY_CONFIG_JSON"] = secret
        calls = []
        def validate(argv, **kwargs):
            self.assertNotIn("RELAY_CONFIG_JSON", os.environ)
            path = Path(argv[-1])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(json.loads(path.read_text())["log"], {"loglevel": "none", "access": "none", "error": "none"})
            calls.append("validate")
            return type("Result", (), {"returncode": 0})()
        def execute(binary, argv):
            self.assertEqual(calls, ["validate"])
            self.assertNotIn("RELAY_CONFIG_JSON", os.environ)
            calls.append("exec")
            raise SystemExit(0)
        output = io.StringIO()
        with patch.object(entry.subprocess, "run", side_effect=validate), patch.object(entry.os, "execv", side_effect=execute), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit):
                entry.run(mount=self.mount, runtime=self.runtime, xray="/fake/xray")
        self.assertEqual(calls, ["validate", "exec"])
        self.assertNotIn(secret, output.getvalue())

    def test_engine_rejection_never_executes_or_leaks(self):
        self.mounted()
        error = io.StringIO()
        with patch.object(entry.subprocess, "run", return_value=type("Result", (), {"returncode": 1})()), patch.object(entry.os, "execv") as execute, contextlib.redirect_stderr(error):
            self.assertEqual(entry.run(mount=self.mount, runtime=self.runtime), 1)
            execute.assert_not_called()
        self.assertNotIn(self.config["inbounds"][0]["settings"]["clients"][0]["id"], error.getvalue())

    def test_conflicting_sources_fail_closed(self):
        self.mounted()
        os.environ["RELAY_CONFIG_JSON"] = json.dumps(self.config)
        with self.assertRaises(entry.ConfigurationError):
            entry.read_config(self.mount)
        self.assertNotIn("RELAY_CONFIG_JSON", os.environ)

    def test_open_permissions_symlinks_and_oversized_files_rejected(self):
        self.mounted()
        self.mount.chmod(0o644)
        with self.assertRaises(entry.ConfigurationError): entry.read_config(self.mount)
        self.mount.unlink()
        self.mount.symlink_to(self.root / "elsewhere")
        with self.assertRaises(OSError): entry.read_config(self.mount)
        self.mount.unlink()
        self.mount.write_bytes(b" " * (entry.MAX_BYTES + 1))
        self.mount.chmod(0o600)
        with self.assertRaises(entry.ConfigurationError): entry.read_config(self.mount)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO is a Unix filesystem object")
    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        os.mkfifo(self.mount, 0o600)
        with self.assertRaises(entry.ConfigurationError): entry.read_config(self.mount)

    def test_interrupted_write_does_not_block_restart(self):
        self.runtime.mkdir(mode=0o700)
        (self.runtime / "config.new").write_text("interrupted previous write")
        path = entry.prepare(self.config, self.runtime)
        self.assertEqual(json.loads(path.read_text()), self.config)
        self.assertFalse(list(self.runtime.glob("config-*.new")))

    def test_duplicate_keys_and_unauthenticated_listener_rejected(self):
        for value in ['{"inbounds":[],"inbounds":[]}', '{"inbounds":[{"protocol":"socks"}]}', '[1]', '{}']:
            with self.subTest(value=value):
                os.environ["RELAY_CONFIG_JSON"] = value
                with self.assertRaises(entry.ConfigurationError): entry.read_config(self.mount)

    def test_reality_shape_accepted(self):
        self.config["inbounds"][0].update(port=443, streamSettings={"network": "tcp", "security": "reality"})
        self.mounted()
        self.assertEqual(entry.read_config(self.mount)["inbounds"][0]["port"], 443)

    def test_health_is_local_listener_only(self):
        path = entry.prepare(self.config, self.runtime)
        with patch.object(entry.socket, "create_connection") as connect:
            self.assertEqual(entry.health(self.runtime), 0)
            connect.assert_called_once_with(("127.0.0.1", 8080), timeout=1)
        with patch.object(entry.socket, "create_connection", side_effect=OSError):
            self.assertEqual(entry.health(self.runtime), 1)
        path.unlink()
        self.assertEqual(entry.health(self.runtime), 1)

    def test_check_only_validates_without_listening(self):
        self.mounted()
        with patch.object(entry.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()), patch.object(entry.os, "execv") as execute, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(entry.run(mount=self.mount, runtime=self.runtime, check_only=True), 0)
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
