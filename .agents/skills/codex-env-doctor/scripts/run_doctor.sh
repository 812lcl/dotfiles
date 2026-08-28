#!/usr/bin/env bash
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

candidates=()
if [[ -n "${CODEX_ENV_DOCTOR_PYTHON:-}" ]]; then
  candidates+=("$CODEX_ENV_DOCTOR_PYTHON")
fi
candidates+=(
  python3
  python3.14
  python3.13
  python3.12
  python3.11
  /opt/homebrew/bin/python3
  /usr/local/bin/python3
  /usr/bin/python3
)

selected=""
for candidate in "${candidates[@]}"; do
  if [[ "$candidate" == */* ]]; then
    resolved="$candidate"
  else
    resolved=$(command -v "$candidate" 2>/dev/null || true)
  fi
  [[ -n "$resolved" && -x "$resolved" ]] || continue
  if "$resolved" -c 'import tomllib' >/dev/null 2>&1; then
    selected="$resolved"
    break
  fi
done

if [[ -z "$selected" ]]; then
  echo "codex-env-doctor requires an available Python 3.11+ interpreter" >&2
  exit 2
fi

if [[ "${1:-}" == "--print-python" ]]; then
  printf '%s\n' "$selected"
  exit 0
fi

exec "$selected" "$script_dir/codex_env_doctor.py" "$@"
