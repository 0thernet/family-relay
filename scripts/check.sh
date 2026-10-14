#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -v
bash -n scripts/ovh-install.sh scripts/image-guard.sh
docker info >/dev/null
image="family-relay:check-$(date -u +%s)-$$"
cleanup() { docker image rm "$image" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker build --pull -t "$image" .
python3 scripts/check-container.py --image "$image"
