#!/usr/bin/env bash
set -euo pipefail

# Exits non-zero on first missing path; prints OK otherwise.
# Note: This script is intentionally quiet to keep Workbench output readable.
# It should be safe to pipe or call from Typer without flooding logs.

usage() {
  echo "Usage: $(basename "$0") <kit_file>"
  echo
  echo "Env:"
  echo "  FAIL_MISSING=0|1   Exit non-zero if any paths are missing (default: 1)"
  exit 2
}

[[ ${1-} ]] || usage
KIT_FILE="$1"

if [[ ! -f "$KIT_FILE" ]]; then
  echo "[validate] error: kit file not found: $KIT_FILE" >&2
  exit 2
fi

# default hard-fail ON
FAIL_MISSING="${FAIL_MISSING:-1}"

# repo root (prefer git, fallback to dirname hack)
if REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi

missing=()

# read kit lines; ignore comments / blanks; support inline trailing comments
# 1) trim leading/trailing whitespace
# 2) strip trailing inline comment: everything after first '#' (if not at start)
# 3) re-trim trailing whitespace after strip
while IFS= read -r raw || [ -n "${raw-}" ]; do
  # trim
  line="$(printf '%s' "$raw" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"

  # full-line comment or blank
  case "$line" in
    ''|'#'*) continue ;;
  esac

  # strip inline comment (keep left side), then trim again
  line="${line%%#*}"
  line="$(printf '%s' "$line" | sed 's/[[:space:]]*$//')"
  [ -z "$line" ] && continue

  path="$REPO_ROOT/$line"
  if [[ ! -e "$path" ]]; then
    missing+=("$line")
  fi
done < "$KIT_FILE"

if ((${#missing[@]} > 0)); then
  echo "[validate] Missing paths:"
  for m in "${missing[@]}"; do
    echo "  - $m"
  done
  if [[ "$FAIL_MISSING" == "1" ]]; then
    exit 1
  fi
else
  echo "[validate] OK — all paths exist."
fi
