#!/usr/bin/env python3
"""Offline image admission: validate and start both transports, without cloud traffic."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("relay", ROOT / "relay.py")
assert spec is not None and spec.loader is not None
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def command(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, capture_output=True, timeout=60, **kwargs)


@contextmanager
def owned_container():
    # Know the cleanup target before a timed-out launch could leave it running.
    name = "family-relay-check-" + uuid.uuid4().hex
    try:
        yield name
    finally:
        present = command(["docker", "ps", "--all", "--quiet", "--filter", "name=^/" + name + "$"])
        if present.returncode:
            raise RuntimeError(f"Could not reconcile owned container {name}")
        if present.stdout.strip():
            try:
                stopped = command(["docker", "stop", "--time", "5", name])
            finally:
                removed = command(["docker", "rm", "--force", name])
                if removed.returncode:
                    raise RuntimeError(f"Cleanup failed for owned container {name}")
            if stopped.returncode:
                raise RuntimeError(f"Graceful shutdown failed for owned container {name}")


def check_image(image: str) -> None:
    for provider in ("railway", "ovh"):
        # Fresh disposable identities exist only in this test process/container.
        state = relay.initial_state(provider, "relay.example.com", ["alice", "bob"])
        environment = dict(os.environ, RELAY_CONFIG_JSON=json.dumps(relay.server_config(state)))
        arguments = ["docker", "run", "--network", "none", "--read-only",
                     "--cap-drop", "ALL", "--cap-add", "NET_BIND_SERVICE",
                     "--security-opt", "no-new-privileges:true", "--tmpfs",
                     "/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777"]
        with owned_container() as name:
            validated = command([*arguments, "--name", name, "--env", "RELAY_CONFIG_JSON", image, "--check"], env=environment)
            if validated.returncode:
                raise RuntimeError(f"{provider}: container rejected generated configuration; raw output suppressed")
        for user in ("alice", "bob"):
            with owned_container() as name:
                validated = command([*arguments, "--name", name, "--interactive", "--entrypoint", "/usr/bin/xray", image, "run", "-test", "-format", "json", "-config", "stdin:"], input=json.dumps(relay.client_config(state, user)))
                if validated.returncode:
                    raise RuntimeError(f"{provider}: container rejected generated client configuration; raw output suppressed")
        with owned_container() as name:
            launched = command([*arguments, "--name", name, "--env", "RELAY_CONFIG_JSON", "--detach", image], env=environment)
            if launched.returncode:
                raise RuntimeError(f"{provider}: container failed to start; raw output suppressed")
            healthy = False
            for _ in range(30):
                result = command(["docker", "exec", name, "python3", "/opt/relay/entrypoint.py", "--health"])
                if result.returncode == 0:
                    healthy = True
                    break
                time.sleep(1)
            if not healthy:
                raise RuntimeError(f"{provider}: local listener did not become healthy")
            environment_check = command(["docker", "exec", name, "python3", "-c", "import pathlib; print(b'RELAY_CONFIG_JSON=' in pathlib.Path('/proc/1/environ').read_bytes())"])
            if environment_check.returncode or environment_check.stdout.strip() != "False":
                raise RuntimeError(f"{provider}: runtime configuration environment was not removed")
            print(f"{provider}: server and both client configs, non-root startup, secret environment removal passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="family-relay:check")
    args = parser.parse_args()
    check_image(args.image)
