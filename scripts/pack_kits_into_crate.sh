#!/usr/bin/env bash
# /tools/warehouse/scripts/pack_kits_into_crate.sh
# Bash ≥ 4.0 required (associative arrays, mapfile).

# Create a *crate* file by concatenating the contents listed in a *kit* (.txt).
# - Kits support comments (# ...) and blank lines.
# - Kit entries may include globs (* ? **), expanded relative to --base-dir (or kit file dir).
# - De-duplicates by default (preserves first occurrence).
# - Optional lexicographic sort of the final resolved file list.
# - Skips missing/dirs with warnings, or fail-fast with --fail-missing.
# - Ensures exactly one trailing newline per file content to avoid double blank lines.
#
# Exit codes:
#   0  success
#   2  CLI usage error
#   3  --fail-missing triggered
#   4  --fail-empty triggered

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Never touch pallets from the crate packer.

# ------------------------------ defaults --------------------------------------

KIT_PATH=""
OUTPUT_PATH=""
OUTPUT_BASE=""        # without part suffix
OUTPUT_EXT=""         # .txt or provided extension
PART_INDEX=1
CUR_OUT=""            # current output path
CUR_LINES=0           # current output line counter
declare -a OUTPUTS=() # all emitted output files (in order)

# New limits/labels
MAX_LINES_PER_OUTPUT=3000
HEADER_LABEL="KIT MEMBER"   # was "KIT FILE"
BASE_DIR=""
PATH_STYLE="auto"   # auto|abs|rel
HEADER_TEMPLATE="===== {label} {index}/{total}: {path}"
UNIQUE=1
DO_SORT=0
FAIL_MISSING=0
FAIL_EMPTY=0
TREE=1
TREE_DISABLE=0
TREE_OUTPUT=""
TREE_ROOT=""

# ------------------------------- helpers --------------------------------------

err() { printf '%s\n' "$*" >&2; }

trim() {
  sed \
    -e 's/^[[:space:]]\{1,\}//' \
    -e 's/[[:space:]]\{1,\}$//' \
    <<<"$1"
}

is_glob() {
  case "$1" in
    *'*'*|*'?'*|*'['*']'*) return 0 ;;
    *) return 1 ;;
  esac
}

abspath() {
  local p="$1"
  local d b
  d=$(dirname "$p") || return 1
  b=$(basename "$p") || return 1
  (cd "$d" 2>/dev/null && printf '%s/%s\n' "$PWD" "$b") || return 1
}

relpath() {
  local target="$1" base="$2"
  if command -v realpath >/dev/null 2>&1; then
    realpath --relative-to="$base" "$target" 2>/dev/null && return 0
  fi
  case "$target" in
    "$base"/*) printf '%s\n' "${target#"$base/"}" ;;
    *) printf '%s\n' "$target" ;;
  esac
}

print_path_for_header() {
  local p="$1" base="$2" style="$3"
  local abs rp
  abs=$(abspath "$p") || abs="$p"
  case "$style" in
    abs) printf '%s\n' "$abs" ;;
    rel) rp=$(relpath "$abs" "$base"); printf '%s\n' "$rp" ;;
    auto)
      case "$abs" in
        "$base"/*) rp=$(relpath "$abs" "$base"); printf '%s\n' "$rp" ;;
        *) printf '%s\n' "$abs" ;;
      esac
      ;;
    *) printf '%s\n' "$abs" ;;
  esac
}

render_header() {
  local template="$1" path_str="$2" idx="$3" total="$4"
  local out="$template"
  out=${out//\{path\}/$path_str}
  out=${out//\{index\}/$idx}
  out=${out//\{total\}/$total}
  out=${out//\{label\}/$HEADER_LABEL}
  printf '%s\n' "$out"
}

ends_with_newline() {
  local f="$1"
  if [[ ! -s "$f" ]]; then return 0; fi
  local last
  last=$(tail -c 1 "$f" 2>/dev/null || printf '')
  [[ "$last" == $'\n' ]]
}

__tree_build_from_paths() {
  local call_root="$1"
  shift
  local -a paths=("$@")
  local -a rels=()
  local p
  for p in "${paths[@]}"; do
    rels+=("$(relpath "$(abspath "$p")" "$call_root")")
  done

  python3 - "${rels[@]}" <<'PY'
import sys
paths = sys.argv[1:]
tree: dict[str, dict] = {}
for path in paths:
    node = tree
    for part in path.split('/'):
        node = node.setdefault(part, {})
def dump(node: dict[str, dict], prefix: str = "") -> None:
    items = sorted(node.items())
    for i, (name, child) in enumerate(items):
        connector = "└──" if i == len(items) - 1 else "├──"
        print(f"{prefix}{connector} {name}")
        if child:
            ext = "    " if i == len(items) - 1 else "│   "
            dump(child, prefix + ext)
print(".")
dump(tree)
PY
}

usage() {
  cat <<'USAGE'
Usage:
  pack_kits_into_crate.sh   --kit tools/warehouse/yard/kits/<name>.txt \
                      --output tools/warehouse/yard/crates/<name>.txt
  [--base-dir DIR] [--path-style auto|abs|rel]
  [--header-template "..."] [--no-unique] [--sort]
  [--fail-missing] [--fail-empty]
  [--tree] [--no-tree] [--tree-output FILE] [--tree-root PATH]
  [--max-lines-per-output N] [--header-label "KIT MEMBER"]

Conventions:
  Kits:   tools/warehouse/yard/kits/
  Crates: tools/warehouse/yard/crates/

Notes:
  - Globs expand relative to --base-dir if provided, otherwise to the kit file's directory.
  - Path style "rel" is relative to --base-dir (if set) else current directory.
  - Tokens for --header-template: {path} {index} {total} {label}
  - Default label: KIT MEMBER
  - Use --max-lines-per-output 0 to disable chunking

  --kit <file>      Path to the kit (.txt)
USAGE
}

# ----------------------------- arg parsing -------------------------------------

if [[ $# -eq 0 ]]; then usage; exit 2; fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --kit)            KIT_PATH="$2"; shift 2 ;;
    --output)         OUTPUT_PATH="$2"; shift 2 ;;
    --base-dir)       BASE_DIR="$2"; shift 2 ;;
    --path-style)     PATH_STYLE="$2"; shift 2 ;;
    --header-template) HEADER_TEMPLATE="$2"; shift 2 ;;
    --header-label)    HEADER_LABEL="$2"; shift 2 ;;
    --no-unique)      UNIQUE=0; shift ;;
    --sort)           DO_SORT=1; shift ;;
    --fail-missing)   FAIL_MISSING=1; shift ;;
    --fail-empty)     FAIL_EMPTY=1; shift ;;
    --tree)           TREE=1; TREE_DISABLE=0; shift ;;
    --no-tree)        TREE_DISABLE=1; shift ;;
    --tree-output)    TREE_OUTPUT="$2"; shift 2 ;;
    --tree-root)      TREE_ROOT="$2"; shift 2 ;;
    --max-lines-per-output)
      [[ "$2" =~ ^[0-9]+$ ]] && MAX_LINES_PER_OUTPUT="$2" || MAX_LINES_PER_OUTPUT=3000
      shift 2 ;;
    -h|--help)        usage; exit 0 ;;
    *)
      err "Unknown argument: $1"; usage; exit 2 ;;
  esac
  done

if [[ -z "$KIT_PATH" || -z "$OUTPUT_PATH" ]]; then
  err "Error: --kit and --output are required."; usage; exit 2
fi

# Default BASE_DIR: prefer Git root, else repo root relative to this script
if [[ -z "$BASE_DIR" ]]; then
  if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
    BASE_DIR=$(git rev-parse --show-toplevel)
  else
    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    BASE_DIR=$(abspath "$script_dir/../..") || BASE_DIR="$PWD"
  fi
else
  BASE_DIR=$(abspath "$BASE_DIR") || BASE_DIR="$PWD"
fi

KIT_PATH=$(abspath "$KIT_PATH") || true
mkdir -p "$(dirname "$OUTPUT_PATH")"
OUTPUT_PATH=$(abspath "$OUTPUT_PATH") || true

# Derive base/ext for rotating outputs
OUTPUT_BASE="$OUTPUT_PATH"
OUTPUT_EXT=""
if [[ "$OUTPUT_PATH" == *.* ]]; then
  OUTPUT_BASE="${OUTPUT_PATH%.*}"
  OUTPUT_EXT=".${OUTPUT_PATH##*.}"
fi

open_new_output() {
  CUR_OUT="${OUTPUT_BASE}.part${PART_INDEX}${OUTPUT_EXT}"
  mkdir -p "$(dirname "$CUR_OUT")"
  printf '# __CRATE_PATH_PLACEHOLDER__\n\n' > "$CUR_OUT"
  CUR_LINES=2   # 2 lines written (placeholder + blank)
  # track created outputs (avoid accidental dups)
  if [[ ${#OUTPUTS[@]} -eq 0 || "${OUTPUTS[-1]}" != "$CUR_OUT" ]]; then
    OUTPUTS+=("$CUR_OUT")
  fi
}

rotate_output_if_needed() {
  # Caller decides when to rotate based on CUR_LINES + pending lines.
  ((PART_INDEX+=1))
  open_new_output
}

count_lines_of_file() {
  # Fast, whitespace-trimmed numeric output
  wc -l < "$1" | tr -d '[:space:]'
}

shopt -s nullglob dotglob globstar

# ----------------------------- collect files -----------------------------------

declare -a RAW_ITEMS=()
declare -a FILES=()

if [[ ! -f "$KIT_PATH" ]]; then
  err "Error: kit file not found: $KIT_PATH"; exit 2
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  line=$(trim "$line")
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^# ]] && continue
  # Strip inline trailing comments and trim again
  if [[ "$line" == *"#"* ]]; then
    line="${line%%#*}"
    line=$(trim "$line")
    [[ -z "$line" ]] && continue
  fi
  RAW_ITEMS+=("$line")
done < "$KIT_PATH"

for item in "${RAW_ITEMS[@]}"; do
  # Defensive: skip if empty after previous processing
  [[ -z "$item" ]] && continue
  if [[ "$item" == /* ]]; then
    pattern="$item"
  else
    pattern="$BASE_DIR/$item"
  fi

  if is_glob "$item"; then
    mapfile -t matches < <(compgen -G "$pattern" || true)
    if [[ ${#matches[@]} -gt 0 ]]; then
      for m in "${matches[@]}"; do
        if [[ -f "$m" ]]; then
          FILES+=("$(abspath "$m")")
        elif [[ -d "$m" ]]; then
          err "Warning: directory matched (skipped): $m"
          [[ $FAIL_MISSING -eq 1 ]] && { err "Failing due to --fail-missing."; exit 3; }
        fi
      done
    else
      err "Warning: no matches for glob: $item"
      [[ $FAIL_MISSING -eq 1 ]] && { err "Failing due to --fail-missing."; exit 3; }
    fi
  else
    abs=$(abspath "$pattern" 2>/dev/null || printf '%s' "$pattern")
    if [[ -f "$abs" ]]; then
      [[ -n "$abs" ]] && FILES+=("$abs")
    elif [[ -d "$abs" ]]; then
      err "Warning: directory listed (skipped): $abs"
      [[ $FAIL_MISSING -eq 1 ]] && { err "Failing on directory."; exit 3; }
    else
      err "Warning: missing file: $abs"
      if [[ $FAIL_MISSING -eq 1 ]]; then
        err "Failing due to --fail-missing."
        exit 3
      fi
    fi
  fi
done

if [[ $UNIQUE -eq 1 ]]; then
  declare -A SEEN=()
  declare -a DEDUP=()
  for p in "${FILES[@]}"; do
    if [[ -z "${SEEN[$p]:-}" ]]; then
      SEEN["$p"]=1
      DEDUP+=("$p")
    fi
  done
  FILES=("${DEDUP[@]}")
fi

if [[ $DO_SORT -eq 1 ]]; then
  LC_ALL=C mapfile -t FILES < <(printf '%s\n' "${FILES[@]}" | sort)
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  if [[ $FAIL_EMPTY -eq 1 ]]; then
    err "No files matched; failing due to --fail-empty."
    exit 4
  fi
  err "No files matched; writing empty crate: $OUTPUT_PATH"
  : > "$OUTPUT_PATH"
  exit 0
fi

# ------------------------------- write output ----------------------------------

outdir=$(dirname "$OUTPUT_PATH")
mkdir -p "$outdir"

if (( TREE == 1 && TREE_DISABLE == 0 )); then
  if [[ -n "$TREE_ROOT" ]]; then
    call_root=$(abspath "$TREE_ROOT") || call_root="$PWD"
  elif command -v git >/dev/null 2>&1 \
       && git rev-parse --show-toplevel >/dev/null 2>&1; then
    call_root=$(git rev-parse --show-toplevel)
  else
    call_root="$PWD"
  fi

  tree_text=$(__tree_build_from_paths "$call_root" "${FILES[@]}")
  err ""
  err "Kit tree (rooted at: $call_root)"
  err "$tree_text"
  # Open first output and write tree preface only once.
  open_new_output
  {
    printf 'Kit tree (rooted at: %s)\n' "$call_root"
    printf '%s\n\n' "$tree_text"
  } >> "$CUR_OUT"
  # Update CUR_LINES to account for lines written by the preface.
  # Count lines in the just-written block (avoid subshell complexity).
  CUR_LINES="$(wc -l < "$CUR_OUT" | tr -d '[:space:]')"
  if [[ -n "$TREE_OUTPUT" ]]; then
    mkdir -p "$(dirname "$TREE_OUTPUT")"
    {
      printf 'Kit tree (rooted at: %s)\n' "$call_root"
      printf '%s\n' "$tree_text"
    } > "$TREE_OUTPUT"
    err "Wrote tree -> $TREE_OUTPUT"
  fi
else
  open_new_output
fi

idx=0
total=${#FILES[@]}
for f in "${FILES[@]}"; do
  ((idx+=1))
  rel_base="$PWD"
  [[ -n "$BASE_DIR" ]] && rel_base="$BASE_DIR"

  path_str=$(print_path_for_header "$f" "$rel_base" "$PATH_STYLE")
  header=$(render_header "$HEADER_TEMPLATE" "$path_str" "$idx" "$total")

  # Lines that will be added: 1 for header + file content lines
  file_lines=$(ends_with_newline "$f" || true; count_lines_of_file "$f")
  header_lines=1
  pending=$(( header_lines + file_lines ))

  # If the file as a whole exceeds the per-output limit by itself, we
  # split it across outputs. Otherwise, rotate only between files.
  if (( MAX_LINES_PER_OUTPUT > 0 && file_lines > MAX_LINES_PER_OUTPUT )); then
    # Ensure header fits; rotate if necessary
    if (( CUR_LINES + header_lines > MAX_LINES_PER_OUTPUT )); then
      rotate_output_if_needed
    fi
    printf '%s\n' "$header" >> "$CUR_OUT"
    (( CUR_LINES += header_lines ))

    # Chunk the file into slices that fit the remaining space,
    # then into full MAX_LINES_PER_OUTPUT slices as needed.
    # We read with awk to avoid loading the whole file in memory.
    awk -v max="$MAX_LINES_PER_OUTPUT" -v cur="$CUR_LINES" '
      BEGIN { line=0; }
      {
        print;
        line++;
        cur++;
        if (cur >= max) {
          print "__CRATE_ROTATE__";  # sentinel for rotation
          cur=0;
        }
      }
    ' "$f" | while IFS= read -r line || [[ -n "$line" ]]; do
      if [[ "$line" == "__CRATE_ROTATE__" ]]; then
        rotate_output_if_needed
        printf '%s\n' "${header} (continued)" >> "$CUR_OUT"
        (( CUR_LINES += 1 ))
        continue
      fi
      printf '%s\n' "$line" >> "$CUR_OUT"
      (( CUR_LINES += 1 ))
    done
    # Ensure single trailing newline per original file contract already handled.
    continue
  fi

  # Regular case: do not split files; rotate if it will overflow
  if (( MAX_LINES_PER_OUTPUT > 0 && CUR_LINES + pending > MAX_LINES_PER_OUTPUT )); then
    rotate_output_if_needed
  fi

  printf '%s\n' "$header" >> "$CUR_OUT"
  (( CUR_LINES += header_lines ))

  if [[ ! -r "$f" ]]; then
    err "Warning: unreadable file: $f"
    if [[ $FAIL_MISSING -eq 1 ]]; then
      err "Failing due to --fail-missing."
      exit 3
    fi
    continue
  fi

  cat "$f" >> "$CUR_OUT"

  if ! ends_with_newline "$f"; then
    printf '\n' >> "$CUR_OUT"
  fi
  # Update current line count after writing file content
  CUR_LINES=$(( CUR_LINES + file_lines ))
done

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")

if (( ${#OUTPUTS[@]} > 1 )); then
  dest_dir="$OUTPUT_BASE"
  mkdir -p "$dest_dir"
  new_outputs=()
  for p in "${OUTPUTS[@]}"; do
    base="$(basename "$p")"
    mv "$p" "$dest_dir/$base"
    new_outputs+=("$dest_dir/$base")
  done
  OUTPUTS=("${new_outputs[@]}")
  err "Packed $total file(s) into ${#OUTPUTS[@]} outputs (≤$MAX_LINES_PER_OUTPUT lines each):"
  for p in "${OUTPUTS[@]}"; do
    err " - $p"
  done
else
  # Only one part: rename .part1 back to the requested --output path.
  if [[ "${OUTPUTS[0]}" != "$OUTPUT_PATH" ]]; then
    mv "${OUTPUTS[0]}" "$OUTPUT_PATH"
    OUTPUTS=("$OUTPUT_PATH")
  fi
  err "Packed $total file(s) -> ${OUTPUTS[0]}"
fi

for p in "${OUTPUTS[@]}"; do
  rel="$(relpath "$(abspath "$p")" "$repo_root")"
  sed -i "1s|.*|# $rel|" "$p"
done

exit 0
