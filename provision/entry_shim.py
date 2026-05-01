#!/usr/bin/env python3
# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
"""Generate analysis shims for code analyzer entrypoints.

Resolve module paths from the repo root. Keep the leading
package segment (for example, `src.` or `tools.`) so imports
like `tools.audit.run_segmentation_audit` work for nested
entries.
"""

import argparse
import os
from pathlib import Path

TEMPLATE = """\
# Auto-generated analysis entrypoint for kit: {kit_name}
# Source: {entry_file}{extra_hdr}

import sys
from pathlib import Path

# Put repo root and src on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

{imports}

def main():
{body}

if __name__ == "__main__":
    main()
"""


def guess_module(
    repo_root: Path,
    entry_file: Path,
) -> str:
    """Return a dotted module path relative to repo root.

    Examples:
      tools/audit/run_segmentation_audit.py
        -> tools.audit.run_segmentation_audit
      src/foo/bar.py
        -> src.foo.bar
      other/top_level.py
        -> other.top_level
      lone_script.py
        -> lone_script
    """
    rel = entry_file.relative_to(repo_root)
    parts = rel.as_posix().split("/")
    # Keep leading packages (src/ or tools/)
    # since in-tree imports are often qualified
    # that way for static analyzers.

    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    return ".".join(p.replace(".py", "") for p in parts).rstrip(".")


def make_shim(
    repo_root: Path,
    kit_name: str,
    entry_file: str,
    cls: str | None,
    method: str | None,
    out_dir: Path,
) -> Path:
    src = (repo_root / entry_file).resolve()
    if not src.exists():
        raise FileNotFoundError(f"entry file not found: {src}")
    module_path = guess_module(
        repo_root,
        src,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{kit_name}_entry.py"

    imports = [
        f"import {module_path}  # ensure importable",
    ]
    extra_hdr = []
    body = []

    if cls:
        imports.append(f"from {module_path} import {cls}")
        extra_hdr.append(f"# Class: {cls}")
    if method:
        call = f"{cls}().{method}()" if cls else f"{module_path}.{method}()"
        body.append(
            "    # Nudge analyzer to follow call graph",
        )
        body.append(f"    {call}")
    else:
        body.append(f"    _ = {module_path}  # touch module")

    content = TEMPLATE.format(
        kit_name=kit_name,
        entry_file=entry_file,
        extra_hdr=("\n" + "\n".join(extra_hdr)) if extra_hdr else "",
        imports="\n".join(imports),
        body="\n".join(body),
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description=("Generate analysis shim for entry file"),
    )
    ap.add_argument("--kit-name", required=True)
    ap.add_argument("--entry-file", required=True)
    ap.add_argument("--class", dest="cls")
    ap.add_argument("--method")
    ap.add_argument(
        "--out-dir",
        default=".warehouse/entry",
    )
    args = ap.parse_args()

    repo_root = Path(
        os.popen("git rev-parse --show-toplevel 2>/dev/null").read().strip() or "."
    ).resolve()
    out = make_shim(
        repo_root=repo_root,
        kit_name=args.kit_name,
        entry_file=args.entry_file,
        cls=args.cls,
        method=args.method,
        out_dir=repo_root / args.out_dir,
    )
    print(str(out.relative_to(repo_root)))


if __name__ == "__main__":
    main()
