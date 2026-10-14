#!/usr/bin/env python3
"""Generate private, per-person Xray relay configurations using Python's stdlib.

This tool never connects to a provider or installs software on a server. Credential
files are explicit outputs; normal command output is safe to share.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import urlencode

SCHEMA_VERSION = 1
MAX_USERS = 32
MAX_STATE_BYTES = 128 * 1024
DEFAULT_STATE = ".relay/state.json"
SLUG = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")
PRIVATE_DER_PREFIX = bytes.fromhex("302e020100300506032b656e04220420")
PUBLIC_DER_PREFIX = bytes.fromhex("302a300506032b656e032100")
PRIVATE_NETWORKS = [
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.168.0.0/16",
    "198.18.0.0/15", "224.0.0.0/4", "240.0.0.0/4",
    "::/128", "::1/128", "fc00::/7", "fe80::/10", "ff00::/8",
]


class RelayError(ValueError):
    """A safe-to-display user or configuration error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def user_name(value: object) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise RelayError("Names must start with a lowercase letter and contain 1–32 lowercase letters, digits or hyphens.")
    return value


def endpoint(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 253:
        raise RelayError("Host must be a public IPv4 address or DNS hostname without a URL, port or path.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        address = None
    if address is not None:
        if address.version != 4 or not address.is_global:
            raise RelayError("Use a public IPv4 address for the server endpoint.")
        return str(address)
    if value != value.lower() or value.endswith(".") or re.fullmatch(r"[0-9.]+", value):
        raise RelayError("Use a lowercase DNS hostname or valid public IPv4 address.")
    labels = value.split(".")
    if len(labels) < 2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        raise RelayError("Host must be a DNS hostname without a URL, port, wildcard or path.")
    if labels[-1] in {"localhost", "local", "internal", "test", "invalid"}:
        raise RelayError("Use a publicly reachable DNS hostname.")
    return value


def _raw_key(value: object) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
        raise RelayError("Reality keys must be canonical base64url-encoded 32-byte keys.")
    try:
        raw = base64.urlsafe_b64decode(value + "=")
    except ValueError as exc:
        raise RelayError("Invalid Reality key encoding.") from exc
    if len(raw) != 32 or base64.urlsafe_b64encode(raw).decode().rstrip("=") != value:
        raise RelayError("Invalid Reality key encoding.")
    return raw


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def generate_reality_keys() -> tuple[str, str]:
    executable = shutil.which("openssl")
    if not executable:
        raise RelayError("OpenSSL is required for OVH key generation. Install OpenSSL and retry.")
    try:
        private_der = subprocess.run([executable, "genpkey", "-algorithm", "X25519", "-outform", "DER"], capture_output=True, check=True, timeout=15).stdout
        public_der = subprocess.run([executable, "pkey", "-inform", "DER", "-pubout", "-outform", "DER"], input=private_der, capture_output=True, check=True, timeout=15).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise RelayError("OpenSSL could not generate X25519 keys; check your OpenSSL installation.") from exc
    if len(private_der) != len(PRIVATE_DER_PREFIX) + 32 or not private_der.startswith(PRIVATE_DER_PREFIX):
        raise RelayError("OpenSSL returned an unsupported X25519 private-key format.")
    if len(public_der) != len(PUBLIC_DER_PREFIX) + 32 or not public_der.startswith(PUBLIC_DER_PREFIX):
        raise RelayError("OpenSSL returned an unsupported X25519 public-key format.")
    return _b64(private_der[-32:]), _b64(public_der[-32:])


def validate_state(state: object) -> dict:
    if not isinstance(state, dict) or type(state.get("schema_version")) is not int or state["schema_version"] != SCHEMA_VERSION:
        raise RelayError("Unsupported state schema; expected schema_version 1.")
    if not isinstance(state.get("provider"), str) or state["provider"] not in {"railway", "ovh"}:
        raise RelayError("Provider must be railway or ovh.")
    host = endpoint(state.get("host"))
    if state["provider"] == "railway":
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise RelayError("Railway requires its public HTTPS DNS hostname, not an IP address.")
    users = state.get("users")
    if not isinstance(users, list) or not 1 <= len(users) <= MAX_USERS:
        raise RelayError(f"A deployment must have 1–{MAX_USERS} users.")
    names, identities = set(), set()
    for user in users:
        if not isinstance(user, dict):
            raise RelayError("Each user must be an object.")
        name = user_name(user.get("name"))
        identity = user.get("id")
        try:
            parsed = uuid.UUID(identity) if isinstance(identity, str) else None
        except ValueError:
            parsed = None
        if parsed is None or parsed.version != 4 or str(parsed) != identity:
            raise RelayError("User identities must be canonical random UUIDv4 values.")
        if name in names or identity in identities:
            raise RelayError("User names and identities must be unique.")
        names.add(name)
        identities.add(identity)
    if state["provider"] == "ovh":
        reality = state.get("reality")
        if not isinstance(reality, dict):
            raise RelayError("OVH state needs Reality keys and handshake settings.")
        _raw_key(reality.get("private_key"))
        _raw_key(reality.get("public_key"))
        if not isinstance(reality.get("short_id"), str) or not re.fullmatch(r"[0-9a-f]{16}", reality["short_id"]):
            raise RelayError("Reality short_id must contain exactly 16 lowercase hexadecimal characters.")
        server_name = endpoint(reality.get("server_name"))
        try:
            ipaddress.ip_address(server_name)
        except ValueError:
            pass
        else:
            raise RelayError("Reality handshake server_name must be a DNS hostname.")
        if reality.get("target") != server_name + ":443":
            raise RelayError("Reality target must match server_name on port 443.")
    elif "reality" in state:
        raise RelayError("Railway state must not contain unused Reality settings.")
    return state


def _no_symlink(path: Path) -> None:
    if path.is_symlink():
        raise RelayError("Refusing a symbolic-link input or output path.")


def _parent(path: Path, *, private: bool = False) -> None:
    # Inspect each lexical component before mkdir, rather than resolving an
    # attacker-controlled link and silently writing somewhere else.
    absolute = Path(os.path.abspath(path.parent))
    for part in reversed([absolute, *absolute.parents]):
        _no_symlink(part)
        if not part.exists():
            part.mkdir(mode=0o700)
        if not part.is_dir():
            raise RelayError("Output parent must be a directory.")
    if private:
        absolute.chmod(0o700)
    _no_symlink(path)


def write_private(path: Path | str, data: str, *, fresh: bool = False, private_parent: bool = False) -> None:
    path = Path(path)
    _parent(path, private=private_parent)
    if path.exists() and not path.is_file():
        raise RelayError("Output must be a regular file.")
    if fresh and path.exists():
        raise RelayError("State already exists. Use user commands or choose a new --state path.")
    fd, temporary = tempfile.mkstemp(prefix=".relay-write-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _no_symlink(path)
        if fresh:
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                raise RelayError("State already exists; no credentials were replaced.") from exc
        else:
            os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise RelayError("State contains duplicate JSON fields.")
        result[key] = value
    return result


def load_state(path: Path | str = DEFAULT_STATE) -> dict:
    path = Path(path)
    _no_symlink(path)
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise RelayError("State must be a regular file.")
            if os.name != "nt" and info.st_mode & 0o077:
                raise RelayError("State permissions are too open. Run chmod 600 on the state file.")
            raw = handle.read(MAX_STATE_BYTES + 1)
        if len(raw) > MAX_STATE_BYTES:
            raise RelayError("State file exceeds the size limit.")
        return validate_state(json.loads(raw, object_pairs_hook=_unique_fields))
    except FileNotFoundError as exc:
        raise RelayError("State not found. Run init first or supply --state.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RelayError("State is not valid JSON.") from exc


def save_state(state: dict, path: Path | str, *, fresh: bool = False) -> None:
    validate_state(state)
    write_private(path, json.dumps(state, indent=2) + "\n", fresh=fresh, private_parent=True)


@contextlib.contextmanager
def state_lock(path: Path):
    _parent(path, private=True)
    lock_path = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError as exc:
        raise RelayError("Another operation holds the state lock. If interrupted, confirm no relay.py process is running before removing the .lock file.") from exc
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()) + "\n")
        yield
    finally:
        lock_path.unlink()


def new_user(name: str) -> dict:
    return {"name": user_name(name), "id": str(uuid.uuid4()), "created_at": utc_now()}


def initial_state(provider: str, host: str, names: list[str]) -> dict:
    if len(names) > MAX_USERS or not names:
        raise RelayError(f"Supply 1–{MAX_USERS} comma-separated user names.")
    # Reject invalid names and endpoint before invoking external key generation.
    for name in names:
        user_name(name)
    endpoint(host)
    if len(set(names)) != len(names):
        raise RelayError("User names must be unique.")
    state = {"schema_version": SCHEMA_VERSION, "provider": provider, "host": host, "created_at": utc_now(), "users": [new_user(name) for name in names]}
    if provider == "ovh":
        private, public = generate_reality_keys()
        state["reality"] = {"private_key": private, "public_key": public, "short_id": secrets.token_hex(8), "target": "www.bing.com:443", "server_name": "www.bing.com"}
    return validate_state(state)


def find_user(state: dict, name: str) -> dict:
    user_name(name)
    for user in state["users"]:
        if user["name"] == name:
            return user
    raise RelayError("No user with that name exists.")


def mutate_user(state: dict, operation: str, name: str) -> dict:
    validate_state(state)
    user_name(name)
    # Work on a copy; a rejected mutation cannot partially alter caller state.
    result = json.loads(json.dumps(state))
    if operation == "add":
        if any(user["name"] == name for user in result["users"]):
            raise RelayError("That user already exists.")
        if len(result["users"]) >= MAX_USERS:
            raise RelayError(f"This template supports at most {MAX_USERS} users per deployment.")
        result["users"].append(new_user(name))
    else:
        user = find_user(result, name)
        if operation == "revoke":
            if len(result["users"]) == 1:
                raise RelayError("Cannot revoke the last user. Add a replacement first or stop the server.")
            result["users"].remove(user)
        elif operation == "rotate":
            user["id"] = str(uuid.uuid4())
            user["rotated_at"] = utc_now()
        else:
            raise RelayError("Unknown user operation.")
    return validate_state(result)


def server_config(state: dict) -> dict:
    validate_state(state)
    railway = state["provider"] == "railway"
    clients = [{"id": user["id"], "email": "family." + user["name"], **({} if railway else {"flow": "xtls-rprx-vision"})} for user in state["users"]]
    if railway:
        stream = {"network": "ws", "security": "none", "wsSettings": {"path": "/relay-ws"}}
    else:
        reality = state["reality"]
        stream = {"network": "tcp", "security": "reality", "realitySettings": {"show": False, "target": reality["target"], "xver": 0, "serverNames": [reality["server_name"]], "privateKey": reality["private_key"], "shortIds": [reality["short_id"]]}}
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{"tag": "family-relay", "listen": "0.0.0.0", "port": 8080 if railway else 443, "protocol": "vless", "settings": {"clients": clients, "decryption": "none"}, "streamSettings": stream, "sniffing": {"enabled": True, "destOverride": ["http", "tls"], "routeOnly": True}}],
        "outbounds": [{"tag": "internet", "protocol": "freedom", "settings": {"domainStrategy": "UseIPv4"}}, {"tag": "blocked", "protocol": "blackhole"}],
        "routing": {"domainStrategy": "IPIfNonMatch", "rules": [{"type": "field", "ip": PRIVATE_NETWORKS, "outboundTag": "blocked"}, {"type": "field", "port": "25,465,587", "outboundTag": "blocked"}]},
    }


def _client_stream(state: dict) -> dict:
    if state["provider"] == "railway":
        return {"network": "ws", "security": "tls", "tlsSettings": {"serverName": state["host"], "allowInsecure": False, "alpn": ["http/1.1"]}, "wsSettings": {"path": "/relay-ws", "headers": {"Host": state["host"]}}}
    reality = state["reality"]
    return {"network": "tcp", "security": "reality", "realitySettings": {"serverName": reality["server_name"], "fingerprint": "chrome", "publicKey": reality["public_key"], "shortId": reality["short_id"], "spiderX": "/"}}


def client_config(state: dict, name: str) -> dict:
    validate_state(state)
    user = find_user(state, name)
    credentials = {"id": user["id"], "encryption": "none"}
    if state["provider"] == "ovh":
        credentials["flow"] = "xtls-rprx-vision"
    return {"log": {"loglevel": "warning"}, "inbounds": [{"tag": "local-socks", "listen": "127.0.0.1", "port": 10808, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}], "outbounds": [{"tag": "relay", "protocol": "vless", "settings": {"vnext": [{"address": state["host"], "port": 443, "users": [credentials]}]}, "streamSettings": _client_stream(state)}]}


def client_uri(state: dict, name: str) -> str:
    validate_state(state)
    user = find_user(state, name)
    parameters = {"encryption": "none", "security": "tls" if state["provider"] == "railway" else "reality"}
    if state["provider"] == "railway":
        parameters.update({"type": "ws", "host": state["host"], "path": "/relay-ws", "sni": state["host"], "alpn": "http/1.1", "allowInsecure": "0"})
    else:
        reality = state["reality"]
        parameters.update({"type": "tcp", "flow": "xtls-rprx-vision", "sni": reality["server_name"], "fp": "chrome", "pbk": reality["public_key"], "sid": reality["short_id"], "spx": "/"})
    return f"vless://{user['id']}@{state['host']}:443?{urlencode(parameters)}#family-relay-{name}"


def clash_config(state: dict, name: str) -> dict:
    validate_state(state)
    user = find_user(state, name)
    proxy = {"name": "family-relay-" + name, "type": "vless", "server": state["host"], "port": 443, "uuid": user["id"], "udp": True, "tls": True, "skip-cert-verify": False}
    if state["provider"] == "railway":
        proxy.update({"network": "ws", "servername": state["host"], "alpn": ["http/1.1"], "ws-opts": {"path": "/relay-ws", "headers": {"Host": state["host"]}}})
    else:
        reality = state["reality"]
        proxy.update({"network": "tcp", "flow": "xtls-rprx-vision", "servername": reality["server_name"], "client-fingerprint": "chrome", "reality-opts": {"public-key": reality["public_key"], "short-id": reality["short_id"]}})
    return {"mixed-port": 7890, "allow-lan": False, "bind-address": "127.0.0.1", "mode": "rule", "log-level": "warning", "ipv6": False, "proxies": [proxy], "proxy-groups": [{"name": "family relay", "type": "select", "proxies": [proxy["name"]]}], "rules": ["MATCH,family relay"]}


def safe_status(state: dict) -> dict:
    validate_state(state)
    return {"schema_version": SCHEMA_VERSION, "provider": state["provider"], "host": state["host"], "users": [user["name"] for user in state["users"]], "user_count": len(state["users"]), "transport": "VLESS WebSocket over HTTPS" if state["provider"] == "railway" else "VLESS Reality", "public_port": 443, "note": "Local configuration only; this does not confirm a live deployment."}


def validate_xray(state: dict, executable: str) -> None:
    resolved = shutil.which(executable)
    if resolved is None:
        raise RelayError("Xray executable not found. Install the pinned Xray version or pass --xray /path/to/xray.")
    with tempfile.TemporaryDirectory(prefix="family-relay-check-") as directory:
        config = Path(directory).resolve() / "config.json"
        write_private(config, json.dumps(server_config(state)))
        try:
            subprocess.run([resolved, "run", "-test", "-config", str(config)], capture_output=True, check=True, timeout=20)
        except (subprocess.SubprocessError, OSError) as exc:
            # Xray diagnostics can quote credentials: never forward raw output.
            raise RelayError("Xray rejected the generated server configuration or could not run. Check that the pinned Xray version is installed.") from exc


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", default=argparse.SUPPRESS, help="private state file (default: .relay/state.json)")
    result = argparse.ArgumentParser(description=__doc__, parents=[common])
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", parents=[common], help="create fresh per-user credentials")
    init.add_argument("--provider", choices=["railway", "ovh"], required=True)
    init.add_argument("--host", required=True, help="DNS hostname or public IPv4; no scheme, port or path")
    init.add_argument("--users", required=True, help="comma-separated lowercase names, e.g. owner,mom,dad")
    user = commands.add_parser("user", parents=[common], help="change local user credentials; redeploy to apply")
    operations = user.add_subparsers(dest="operation", required=True)
    for operation in ["add", "revoke", "rotate"]:
        item = operations.add_parser(operation, parents=[common])
        item.add_argument("name")
    export = commands.add_parser("export", parents=[common], help="write one person's secret client configuration")
    export.add_argument("name")
    export.add_argument("--format", choices=["uri", "clash", "xray"], required=True)
    export.add_argument("--output", required=True)
    for command in ["render", "env"]:
        item = commands.add_parser(command, parents=[common], help="write private server JSON" if command == "render" else "write private Railway dotenv variables")
        item.add_argument("--output", required=True)
    commands.add_parser("status", parents=[common], help="show safe local configuration summary")
    check = commands.add_parser("validate", parents=[common], help="validate local state, optionally with the Xray core")
    check.add_argument("--xray", metavar="EXECUTABLE")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if os.name == "nt":
        print("Error: Native Windows setup is not supported. Run this command in Ubuntu on WSL, keeping this repository and private state in your Linux home directory, not /mnt/c. Native Windows client apps are supported.", file=sys.stderr)
        return 1
    args.state = getattr(args, "state", DEFAULT_STATE)
    try:
        state_path = Path(args.state)
        if args.command == "init":
            with state_lock(state_path):
                if state_path.exists():
                    raise RelayError("State already exists; no credentials were replaced.")
                state = initial_state(args.provider, args.host, args.users.split(","))
                save_state(state, state_path, fresh=True)
            print(f"Created {len(state['users'])} users. State saved privately. Export client files, then deploy the rendered server configuration.")
        elif args.command == "user":
            with state_lock(state_path):
                state = mutate_user(load_state(state_path), args.operation, args.name)
                save_state(state, state_path)
            print("Local user configuration updated. Render and redeploy the server configuration to apply it; existing live access is unchanged until then.")
        else:
            state = load_state(state_path)
            if args.command == "status":
                print(json.dumps(safe_status(state), indent=2))
            elif args.command == "validate":
                if args.xray:
                    validate_xray(state, args.xray)
                print("Local state and generated Xray configuration are valid." if args.xray else "Local state is valid. No live connectivity test was performed.")
            else:
                destination = Path(args.output)
                protected = [state_path, state_path.with_name(state_path.name + ".lock")]
                if any(destination.resolve() == item.resolve() for item in protected):
                    raise RelayError("Output cannot overwrite the state file or its lock.")
                if args.command == "export":
                    if args.format == "uri":
                        output = client_uri(state, args.name) + "\n"
                    else:
                        config = clash_config(state, args.name) if args.format == "clash" else client_config(state, args.name)
                        output = json.dumps(config, indent=2) + "\n"
                elif args.command == "env":
                    if state["provider"] != "railway":
                        raise RelayError("env is only for Railway; use render for OVH.")
                    # Every string in the rendered config is validated; single
                    # quotes never occur. This is safe dotenv and shell syntax.
                    output = "RELAY_CONFIG_JSON='" + json.dumps(server_config(state), separators=(",", ":")) + "'\n"
                else:
                    output = json.dumps(server_config(state), indent=2) + "\n"
                write_private(destination, output)
                print("Private configuration written. Share client exports only with their intended user; keep server/state files private.")
        return 0
    except (RelayError, OSError) as exc:
        # OSError can contain file paths, but never raw secret file contents.
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
