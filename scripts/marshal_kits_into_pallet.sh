#!/usr/bin/env bash
# Build a symlink pallet from a kit file.
set -euo pipefail
shopt -s extglob

usage(){
  echo "Usage: $(basename "$0") --kit <kit.txt> --out-dir <pallet_dir> [--dry-run] [--clean] [--fail-missing] [--quiet]"
}

KIT=""
OUT_DIR=""
DRY=0
CLEAN=0
QUIET=0
FAIL_MISSING=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --kit) KIT="$2"; shift 2;;
    --out-dir) OUT_DIR="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    --clean) CLEAN=1; shift;;
    --quiet) QUIET=1; shift;;
    --fail-missing) FAIL_MISSING=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown: $1" >&2; usage; exit 2;;
  esac
done

[[ -n "$KIT" && -f "$KIT" ]] || { echo "[pallet] error: kit not found: $KIT" >&2; exit 2; }
[[ -n "$OUT_DIR" ]] || { echo "[pallet] error: --out-dir required" >&2; exit 2; }

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Derive kit stem for directory naming when OUT_DIR is the pallets root.
kit_base="$(basename -- "$KIT")"
kit_stem="${kit_base%%.*}"

# Normalize OUT_DIR; if it looks like the pallets root, put the pallet under <root>/<kit_stem>.
# If OUT_DIR already ends with <kit_stem>, keep as-is (idempotent with Python caller).
out_basename="$(basename -- "$OUT_DIR")"
parent_basename="$(basename -- "$(dirname -- "$OUT_DIR")")"

PALLET_DIR="$OUT_DIR"
# Heuristic: if OUT_DIR equals "pallets" or its parent equals "pallets" and OUT_DIR isn't already kit_stem,
# create/use OUT_DIR/<kit_stem>.
if [[ "$out_basename" == "pallets" ]]; then
  PALLET_DIR="$OUT_DIR/$kit_stem"
elif [[ "$parent_basename" == "pallets" && "$out_basename" != "$kit_stem" ]]; then
  PALLET_DIR="$(dirname -- "$OUT_DIR")/$kit_stem"
fi

# Also handle the case where OUT_DIR is the repo root pallets path with trailing slashes
case "$OUT_DIR" in
  */warehouse/yard/pallets|*/warehouse/yard/pallets/) PALLET_DIR="${OUT_DIR%/}/$kit_stem" ;;
esac

[[ $DRY -eq 1 ]] || mkdir -p "$PALLET_DIR"

if [[ $CLEAN -eq 1 && $DRY -eq 0 && -d "$PALLET_DIR" ]]; then
  find "$PALLET_DIR" -mindepth 1 -exec rm -rf {} + 2>/dev/null || true
fi

mapfile -t LINES < <(sed -e 's/#.*$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$KIT" | sed '/^$/d')

missing=0
for line in "${LINES[@]}"; do
  src="$REPO_ROOT/$line"
  # Skip yard artifacts entirely — they’re build outputs.
  if [[ "$line" == tools/warehouse/yard/* ]]; then
    [[ $QUIET -eq 1 ]] || echo "[pallet] skip: $line (yard artifact)"
    continue
  fi
  if [[ ! -e "$src" ]]; then
    ((missing++))
    [[ $QUIET -eq 1 ]] || echo "[pallet] missing: $line" >&2
    continue
  fi
  if [[ -d "$src" ]]; then
    [[ $QUIET -eq 1 ]] || echo "[pallet] warn: directory in kit (skipped): $line" >&2
    [[ $FAIL_MISSING -eq 1 ]] && { echo "[pallet] fail: directory encountered" >&2; exit 3; }
    continue
  fi
  dst="$PALLET_DIR/$line"
  if [[ $DRY -eq 1 ]]; then
    echo "[dry] ln -sfn '$src' '$dst'"
    continue
  fi
  mkdir -p "$(dirname "$dst")"
  ln -sfn "$src" "$dst"
  [[ $QUIET -eq 1 ]] || echo "[pallet] linked: $line"
done

if (( missing > 0 )) && [[ $FAIL_MISSING -eq 1 ]]; then
  echo "[pallet] fail-missing: $missing path(s) missing" >&2
  exit 3
fi

[[ $DRY -eq 1 ]] && echo "[pallet] (dry-run) would build -> $PALLET_DIR" || echo "[pallet] built -> $PALLET_DIR"
