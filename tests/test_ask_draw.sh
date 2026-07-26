#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_tmp="$(mktemp -d)"
trap 'rm -rf "$test_tmp"' EXIT

assert_codex_does_not_create_venv() {
  local name="$1"
  shift
  local venv_path="$test_tmp/$name"
  DRAW_VENV="$venv_path" "$repo_dir/scripts/ask_draw.sh" "$@" --help >/dev/null
  [[ ! -e "$venv_path" ]] || {
    printf 'Codex bootstrap unexpectedly created %s\n' "$venv_path" >&2
    exit 1
  }
}

assert_codex_does_not_create_venv separated --provider codex
assert_codex_does_not_create_venv equals --provider=codex
assert_codex_does_not_create_venv repeated --provider zenmux --provider=codex

env_venv="$test_tmp/env-default"
DRAW_PROVIDER=codex DRAW_VENV="$env_venv" "$repo_dir/scripts/ask_draw.sh" --help >/dev/null
[[ ! -e "$env_venv" ]] || {
  printf 'Codex environment default unexpectedly created %s\n' "$env_venv" >&2
  exit 1
}

for bad_args in "--provider" "--provider=" "--provider unknown"; do
  bad_venv="$test_tmp/bad-${bad_args//[^a-zA-Z0-9]/-}"
  set +e
  # shellcheck disable=SC2086
  DRAW_VENV="$bad_venv" "$repo_dir/scripts/ask_draw.sh" $bad_args >/dev/null 2>&1
  status=$?
  set -e
  [[ "$status" -eq 2 ]] || {
    printf 'Expected exit 2 for %s, got %s\n' "$bad_args" "$status" >&2
    exit 1
  }
  [[ ! -e "$bad_venv" ]] || {
    printf 'Invalid provider unexpectedly created %s\n' "$bad_venv" >&2
    exit 1
  }
done

printf 'ask_draw.sh bootstrap tests passed\n'
