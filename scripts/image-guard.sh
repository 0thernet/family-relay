#!/usr/bin/env bash
# Sourced by the installer. Never pull or rebuild a recovery image.
record_release_image() {
  local directory=$1 identity
  [[ ! -e $directory/.image-id && ! -L $directory/.image-id ]] || return 1
  identity=$(docker image inspect --format '{{.Id}}' "family-relay:${directory##*/}") || return 1
  [[ $identity =~ ^sha256:[0-9a-f]{64}$ ]] || return 1
  printf '%s\n' "$identity" >"$directory/.image-id"
}

require_release_image() {
  local directory=$1 expected actual
  if [[ ! -f $directory/.image-id || -L $directory/.image-id ]]; then
    printf '%s\n' 'Recovery image identity is missing. Preserve the release files; do not rebuild them as a rollback.' >&2
    return 1
  fi
  expected=$(<"$directory/.image-id")
  [[ $expected =~ ^sha256:[0-9a-f]{64}$ ]] || return 1
  actual=$(docker image inspect --format '{{.Id}}' "family-relay:${directory##*/}" 2>/dev/null) || actual=
  if [[ $actual != "$expected" ]]; then
    printf '%s\n' 'The recorded local recovery image is missing or changed. Preserve release files and restore the exact image before retrying.' >&2
    return 1
  fi
}
