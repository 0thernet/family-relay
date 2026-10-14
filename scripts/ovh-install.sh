#!/usr/bin/env bash
# Run on the VPS, after Docker Engine and Compose v2 are installed.
set -euo pipefail
umask 077

ROOT=/opt/family-relay
SOURCE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
source "$SOURCE/scripts/image-guard.sh"

die() { printf '%s\n' "$*" >&2; exit 1; }
[[ ${EUID} == 0 ]] || die 'Run this command with sudo on the VPS.'
[[ $(uname -s) == Linux ]] || die 'Run this installer on the Linux VPS, not your computer.'
command -v docker >/dev/null || die 'Install Docker Engine using the official Ubuntu guide first.'
docker compose version >/dev/null || die 'Docker Compose v2 is required.'
docker info >/dev/null 2>&1 || die 'Docker Engine is not running.'
[[ ! -L $ROOT ]] || die 'The installation directory must not be a symlink.'

release_path() {
  local path
  path=$(readlink -f -- "$ROOT/$1") || return 1
  [[ $path == "$ROOT/releases/"* && -f $path/.family-relay-release ]] || return 1
  printf '%s\n' "$path"
}
compose() {
  # A shell-exported tag must not defeat an exact-release rollback.
  (unset RELAY_RELEASE; docker compose --env-file "$1/.env" --project-name family-relay --project-directory "$1" -f "$1/compose.yaml" "${@:2}")
}
acquire_lock() {
  command -v flock >/dev/null || die 'The util-linux flock command is required.'
  exec 9>"$ROOT/install.lock"
  flock -n 9 || die 'Another relay deployment is running. Wait for it to finish.'
  [[ ! -e $ROOT/current.new && ! -e $ROOT/previous.new && ! -L $ROOT/current.new && ! -L $ROOT/previous.new ]] || die 'Interrupted pointer update found. Preserve the directory and inspect before continuing.'
}
point_to() {
  local label=$1 target=$2
  ln -s -- "$target" "$ROOT/$label.new"
  mv -Tf -- "$ROOT/$label.new" "$ROOT/$label"
}

case ${1:-} in
  --status)
    [[ $# == 1 ]] || die 'Usage: ovh-install.sh --status'
    current=$(release_path current) || die 'No successful relay deployment found.'
    compose "$current" ps
    printf '%s\n' 'This shows container health only. Test an imported profile from your device too.'
    exit 0
    ;;
  --rollback)
    [[ $# == 1 ]] || die 'Usage: ovh-install.sh --rollback'
    [[ -d $ROOT ]] || die 'No successful relay deployment found.'
    acquire_lock
    previous=$(release_path previous) || die 'No previous successful release exists.'
    current=$(release_path current) || die 'No current successful release exists.'
    require_release_image "$previous"
    require_release_image "$current"
    if ! compose "$previous" up -d --no-build --pull never --wait --wait-timeout 45; then
      require_release_image "$current"
      compose "$current" up -d --no-build --pull never --wait --wait-timeout 45 || die 'Rollback and automatic restore failed. Preserve /opt/family-relay and inspect Docker service health.'
      die 'Rollback failed; the current successful release was restored.'
    fi
    point_to current "$previous"
    point_to previous "$current"
    printf '%s\n' 'Previous release restored. It also restores the credentials in that release.'
    exit 0
    ;;
  --*|'') die 'Usage: sudo ./scripts/ovh-install.sh PATH_TO_RENDERED_SERVER_JSON | --status | --rollback' ;;
esac

[[ $# == 1 ]] || die 'Supply exactly one rendered server JSON file.'
[[ -f $1 && ! -L $1 ]] || die 'Configuration must be a regular file, not a symlink.'
[[ $(stat -c %s -- "$1") -le 131072 ]] || die 'Configuration exceeds 128 KiB.'
for file in Dockerfile .dockerignore compose.yaml docker/entrypoint.py scripts/ovh-install.sh scripts/image-guard.sh; do
  [[ -f $SOURCE/$file && ! -L $SOURCE/$file ]] || die 'Required source file missing or linked.'
done

install -d -m 700 "$ROOT" "$ROOT/releases"
# Serialize only this installer's own operations; never take over an active one.
acquire_lock
current=$(release_path current || true)
if [[ -n $current ]]; then require_release_image "$current"; fi
if [[ -z $current ]]; then
  [[ ! -e $ROOT/current && ! -L $ROOT/current ]] || die 'The current release pointer is invalid. Preserve the installation and repair it before continuing.'
  existing=$(docker ps -aq --filter label=com.docker.compose.project=family-relay)
  [[ -z $existing ]] || die 'Existing containers use the family-relay project name without a managed release. Preserve them and resolve the name conflict before installing.'
fi

release=$(date -u +%Y%m%dT%H%M%S)-${RANDOM}
directory=$ROOT/releases/$release
mkdir -m 700 -- "$directory"
install -d -m 700 "$directory/docker" "$directory/scripts"
for file in Dockerfile .dockerignore compose.yaml docker/entrypoint.py scripts/ovh-install.sh scripts/image-guard.sh; do
  install -m 600 -- "$SOURCE/$file" "$directory/$file"
done
chmod 700 "$directory/scripts/ovh-install.sh"
install -o 10001 -g 10001 -m 600 -- "$1" "$directory/server.json"
printf 'RELAY_RELEASE=%s\n' "$release" >"$directory/.env"
printf '%s\n' "$release" >"$directory/.family-relay-release"

# The private file is excluded from the Docker build context by .dockerignore.
compose "$directory" build --pull
record_release_image "$directory"
compose "$directory" run --rm --no-deps relay --check
require_release_image "$directory"
if ! compose "$directory" up -d --no-build --pull never --wait --wait-timeout 45; then
  if [[ -n $current ]]; then
    printf '%s\n' 'New release did not become healthy; restoring the previous deployment.' >&2
    require_release_image "$current"
    compose "$current" up -d --no-build --pull never --wait --wait-timeout 45 || die 'Automatic restore failed. Preserve /opt/family-relay and inspect Docker service health.'
  else
    compose "$directory" down
  fi
  die 'New release was not activated. Its files were preserved for diagnosis.'
fi
if [[ -n $current ]]; then point_to previous "$current"; fi
point_to current "$directory"
printf '%s\n' 'Relay is listening on TCP port 443. Import your personal profile and test it from your device.'
