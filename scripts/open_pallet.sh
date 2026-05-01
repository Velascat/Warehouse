#!/usr/bin/env bash
# file: tools/warehouse/scripts/open_pallet.sh

set -euo pipefail

TARGET="${1:?usage: $0 <path-to-open>}"

preferred="${WORKBENCH_EDITOR:-${EDITOR:-}}"
if [[ -n "${preferred}" ]] && command -v "${preferred}" >/dev/null 2>&1; then
  OPEN_CMD=("${preferred}")
elif command -v code >/dev/null 2>&1; then
  OPEN_CMD=(code)
elif command -v windsurf >/dev/null 2>&1 && [[ -z "${WINDSURF_DISABLE:-}" ]]; then
  OPEN_CMD=(windsurf)
else
  case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
    darwin*) OPEN_CMD=(open) ;;
    mingw*|msys*|cygwin*) OPEN_CMD=(cmd.exe /c start "") ;;
    *) OPEN_CMD=(xdg-open) ;;
  esac
fi

echo "[pallet] ${OPEN_CMD[0]} \"${TARGET}\""
exec "${OPEN_CMD[@]}" "$TARGET"
