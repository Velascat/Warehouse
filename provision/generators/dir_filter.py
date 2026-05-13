# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
# /tools/warehouse/provision/generators/dir_filter.py

"""Dir-Filter strategy for kit generation.

Selects files by:
- git tracked / untracked
- extensions
- include/exclude globs
- fallback walk if git unavailable
"""

from __future__ import annotations

import fnmatch
import os
import subprocess
from pathlib import Path


def _git_ls(
    tracked: bool,
) -> list[str]:
    try:
        args = (
            ["git", "ls-files"]
            if tracked
            else [
                "git",
                "ls-files",
                "--others",
                "--exclude-standard",
            ]
        )
        out = subprocess.check_output(
            args,
            text=True,
            timeout=30,
        )
        return [p for p in out.splitlines() if p]
    except Exception:
        return []


def build_file_list(
    repo_root: Path,
    use_git_tracked: bool,
    include_untracked: bool,
    extensions_csv: str | None,
    include_globs_csv: str | None,
    exclude_globs_csv: str | None,
    *,
    keep_hidden: bool = False,
    follow_symlinks: bool = False,
) -> list[str]:
    """Return sorted, de-duplicated relative file paths."""
    os.chdir(repo_root)
    files: list[str] = []

    if use_git_tracked:
        files += _git_ls(tracked=True)

    if include_untracked:
        files += _git_ls(tracked=False)

    if not files:
        for root, dirs, fns in os.walk(
            ".",
            topdown=True,
            followlinks=follow_symlinks,
        ):
            if root.startswith("./.git"):
                continue
            if not keep_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                fns = [f for f in fns if not f.startswith(".")]
            for f in fns:
                files.append(
                    str(Path(root) / f).lstrip("./"),
                )

    if extensions_csv:
        wanted = {
            e.strip().lstrip(".").lower() for e in extensions_csv.split(",") if e.strip()
        }
        files = [p for p in files if Path(p).suffix.lower().lstrip(".") in wanted]

    if include_globs_csv:
        pats = [s.strip() for s in include_globs_csv.split(",") if s.strip()]
        inc: list[str] = []
        for pat in pats:
            inc += [p for p in files if fnmatch.fnmatch(p, pat)]
        files = sorted(set(inc))

    if exclude_globs_csv:
        pats = [s.strip() for s in exclude_globs_csv.split(",") if s.strip()]
        keep: list[str] = []
        for p in files:
            if any(fnmatch.fnmatch(p, pat) for pat in pats):
                continue

            keep.append(p)
        files = keep

    return sorted(set(files))
