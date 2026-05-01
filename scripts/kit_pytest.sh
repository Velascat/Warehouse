#!/usr/bin/env bash
set -euo pipefail
KIT_FILE="${1:?usage: $0 tools/warehouse/yard/kits/<kit>.txt}"
mapfile -t FILES < <(grep -v '^\s*#' "$KIT_FILE" | sed '/^\s*$/d')
pytest -q "${FILES[@]}"
