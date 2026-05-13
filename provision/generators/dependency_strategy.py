# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
# /tools/warehouse/provision/generators/dependency_strategy.py
from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import Path

from analyzers.dependency_closure.core import (
    Options,
    build_paths,
)

from .dir_filter import build_file_list as dir_list


def _rel_list(paths: Iterable[str], repo_root: Path) -> list[str]:
    root = repo_root.resolve()
    out: list[str] = []
    for p in paths:
        pp = Path(p)
        if not pp.is_absolute():
            out.append(str(pp))
            continue
        try:
            out.append(str(pp.resolve().relative_to(root)))
        except Exception:
            continue
    return out


def build_file_list(
    repo_root: Path,
    entry_path: Path,
    import_scope: str = "used",
    star_policy: str = "warn",
    max_depth: int = 0,
    # dir-filter knobs
    use_git_tracked: bool = True,
    include_untracked: bool = False,
    extensions_csv: str | None = None,
    include_globs_csv: str | None = None,
    exclude_globs_csv: str | None = None,
    # combine
    combine: str = "union",  # "union" | "intersect" | "graph" | "dir"
) -> list[str]:
    graph_paths = build_paths(
        repo_root,
        entry_path,
        Options(
            import_scope=import_scope,
            star_policy=star_policy,
            max_depth=max_depth,
        ),
    )
    dir_paths = dir_list(
        repo_root=repo_root,
        use_git_tracked=use_git_tracked,
        include_untracked=include_untracked,
        extensions_csv=extensions_csv,
        include_globs_csv=include_globs_csv,
        exclude_globs_csv=exclude_globs_csv,
    )
    graph_paths = set(_rel_list(graph_paths, repo_root))
    dir_paths = set(_rel_list(dir_paths, repo_root))

    if combine == "graph":
        paths = graph_paths
    elif combine == "dir":
        paths = dir_paths
    elif combine == "intersect":
        paths = graph_paths & dir_paths
    else:  # union
        paths = graph_paths | dir_paths

    if exclude_globs_csv:
        pats = [s.strip() for s in exclude_globs_csv.split(",") if s.strip()]
        filtered: list[str] = []
        for p in paths:
            if any(fnmatch.fnmatch(p, pat) for pat in pats):
                continue
            filtered.append(p)
        paths = set(filtered)

    return sorted(paths)
