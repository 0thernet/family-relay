#!/usr/bin/env python3
"""Validate one private configuration, then replace PID 1 with Xray.

Railway supplies RELAY_CONFIG_JSON; Docker Compose mounts /run/relay/config.json.
Health means the local listener accepts TCP, not that a user's network works.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import uuid

MAX_BYTES = 128 * 1024
MOUNT = Path("/run/relay/config.json")
RUNTIME = Path("/tmp/relay-runtime")
XRAY = "/usr/bin/xray"


class ConfigurationError(ValueError):
    pass


def unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError("Duplicate configuration keys are not allowed.")
        result[key] = value
    return result


def read_config(mount: Path) -> dict:
    # Pop before validating so neither Xray nor its validator inherits the secret.
    value = os.environ.pop("RELAY_CONFIG_JSON", None)
    if value is not None and mount.exists():
        raise ConfigurationError("Use one configuration source, not both environment and a mounted file.")
    if value is None:
        fd = os.open(mount, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise ConfigurationError("Mounted configuration must be a private regular file (mode 600).")
            raw = handle.read(MAX_BYTES + 1)
    else:
        raw = value.encode("utf-8")
    if not 0 < len(raw) <= MAX_BYTES:
        raise ConfigurationError("Configuration is empty or exceeds 128 KiB.")
    try:
        config = json.loads(raw, object_pairs_hook=unique_fields)
    except (ValueError, UnicodeError) as exc:
        raise ConfigurationError("Configuration is not valid JSON.") from exc
    if not isinstance(config, dict):
        raise ConfigurationError("Configuration must be a JSON object.")
    inbounds = config.get("inbounds")
    if not isinstance(inbounds, list) or len(inbounds) != 1 or not isinstance(inbounds[0], dict):
        raise ConfigurationError("Expected one authenticated relay listener.")
    inbound = inbounds[0]
    if inbound.get("protocol") != "vless" or inbound.get("listen") != "0.0.0.0":
        raise ConfigurationError("Expected an authenticated VLESS listener.")
    clients = inbound.get("settings", {}).get("clients")
    if not isinstance(clients, list) or not 1 <= len(clients) <= 32:
        raise ConfigurationError("Expected 1–32 authenticated users.")
    try:
        ids = [str(uuid.UUID(client["id"])) for client in clients]
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ConfigurationError("Every user needs a valid UUID.") from exc
    if len(set(ids)) != len(ids):
        raise ConfigurationError("User credentials must be unique.")
    stream = inbound.get("streamSettings", {})
    port = inbound.get("port")
    railway = port == 8080 and stream.get("network") == "ws" and stream.get("security") == "none" and stream.get("wsSettings", {}).get("path") == "/relay-ws"
    vps = port == 443 and stream.get("network") in {"tcp", "raw"} and stream.get("security") == "reality"
    if not (railway or vps):
        raise ConfigurationError("Expected Railway WebSocket on 8080 or VPS REALITY on 443.")
    if config.get("api") or config.get("metrics"):
        raise ConfigurationError("Public management listeners are not supported.")
    # Never log destination names, access records, credentials, or engine errors.
    config["log"] = {"loglevel": "none", "access": "none", "error": "none"}
    return config


def prepare(config: dict, runtime: Path) -> Path:
    os.umask(0o077)
    runtime.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = runtime.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ConfigurationError("Runtime directory is not private.")
    fd, temporary_name = tempfile.mkstemp(prefix="config-", suffix=".new", dir=runtime)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(config, handle, separators=(",", ":"))
            handle.write("\n")
        destination = runtime / "config.json"
        os.replace(temporary, destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def health(runtime: Path) -> int:
    try:
        config = json.loads((runtime / "config.json").read_text())
        port = config["inbounds"][0]["port"]
        if port not in (443, 8080):
            return 1
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return 1


def run(*, mount: Path = MOUNT, runtime: Path = RUNTIME, xray: str = XRAY, check_only: bool = False) -> int:
    try:
        path = prepare(read_config(mount), runtime)
        check = subprocess.run([xray, "run", "-test", "-config", str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
        if check.returncode:
            raise ConfigurationError("Xray rejected the generated configuration; render it again with relay.py.")
        if check_only:
            print("Relay configuration validated. No live connection was tested.")
            return 0
        print("Relay starting with authenticated access and destination logging disabled.", flush=True)
        os.execv(xray, [xray, "run", "-config", str(path)])
    except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired):
        # Even engine/parser errors can include secrets; deliberately emit none.
        print("Relay startup failed. Check configuration permissions and regenerate with relay.py.", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--health"]:
        raise SystemExit(health(RUNTIME))
    if sys.argv[1:] not in ([], ["--check"]):
        print("Supported options: --check, --health", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(run(check_only=sys.argv[1:] == ["--check"]))
