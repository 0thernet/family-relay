#!/usr/bin/env python3
"""Stage only the relay configuration on an existing Railway service.

Requires an authenticated Railway CLI. Secret JSON is passed over stdin and
never appears in command arguments or normal output. This command does not
create a project, deploy, or restart a service.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("family_relay_config", _ROOT / "relay.py")
relay = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(relay)

CLI_TIMEOUT_SECONDS = 45
TARGET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")


def project_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Project must be its UUID from Railway Project Settings.") from exc
    if str(parsed) != value or parsed.int == 0:
        raise argparse.ArgumentTypeError("Project must be its canonical lowercase UUID from Railway Project Settings.")
    return value


def target_name(value: str) -> str:
    if not TARGET_NAME.fullmatch(value):
        raise argparse.ArgumentTypeError("Use a service/environment name or UUID containing letters, digits, dots, underscores or hyphens.")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--project", required=True, type=project_id, help="existing Railway project UUID")
    result.add_argument("--service", default="relay", type=target_name, help="existing service name or UUID (default: relay)")
    result.add_argument("--environment", default="production", type=target_name, help="existing environment name or UUID (default: production)")
    result.add_argument("--state", default=relay.DEFAULT_STATE, help="private Railway state file (default: .relay/state.json)")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        state = relay.load_state(args.state)
        if state["provider"] != "railway":
            raise relay.RelayError("This helper requires Railway state. OVH deployments use render instead.")
        payload = json.dumps(relay.server_config(state), separators=(",", ":"))
    except relay.RelayError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: Could not read the private state file. Check its path and permissions.", file=sys.stderr)
        return 1

    executable = shutil.which("railway")
    if executable is None:
        print("Error: Railway CLI was not found. Install it, run railway login, then retry.", file=sys.stderr)
        return 1

    print(f"Target: Railway project {args.project}, service {args.service}, environment {args.environment}.", flush=True)
    print("Staging RELAY_CONFIG_JSON only; deployment is a separate step.", flush=True)
    command = [
        executable, "variable", "set", "RELAY_CONFIG_JSON", "--stdin", "--skip-deploys",
        "--project", args.project, "--service", args.service, "--environment", args.environment,
    ]
    try:
        result = subprocess.run(command, input=payload, text=True, capture_output=True, timeout=CLI_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        print("Error: Railway did not finish within 45 seconds. The variable update may have succeeded. Reconcile this target in the Railway dashboard before retrying.", file=sys.stderr)
        return 1
    except OSError:
        print("Error: Railway CLI could not run. Check the CLI installation and login status.", file=sys.stderr)
        return 1
    if result.returncode != 0:
        # Provider/CLI output may contain the submitted configuration. It stays
        # in memory and must never be forwarded into terminal or CI logs.
        print("Error: Railway did not confirm the variable update. Check CLI login, target access, and this target in the Railway dashboard before retrying. Raw CLI output was withheld because it may contain credentials.", file=sys.stderr)
        return 1
    print("Relay configuration staged. Deploy the same project, service and environment with railway up when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
