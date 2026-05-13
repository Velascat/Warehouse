#!/usr/bin/env python3
# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.

"""Provision a Kit (file list) for Packing.

Run from the target repo root.  Outputs go under `.warehouse/yard/kits/`.

Modes:
- dir        → select by git/EXT/INCLUDE/EXCLUDE
- analysis   → static entrypoint analysis

Examples:
  # dir-filter (current default)
  python /path/to/Warehouse/provision/provision_kit_from_draft.py \
    --mode dir \
    --out .warehouse/yard/kits/app.txt \
    --git --ext py,md,sh \
    --exclude **/__pycache__/**,**/*.pyc,

  # static analysis (requires --entry)
  python /path/to/Warehouse/provision/provision_kit_from_draft.py \
    --mode analysis \
    --entry src/entrypoints/main_long_form_video.py \
    --out .warehouse/yard/kits/app_graph.txt,
"""

import argparse
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    try:
        import subprocess

        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            timeout=10,
        ).strip()
        return Path(root)
    except Exception:
        return Path(__file__).resolve().parents[3]


def _write_kit(
    out_path: Path,
    paths: list[str],
) -> None:
    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with out_path.open("w", encoding="utf-8") as f:
        f.write(
            "# kit (generated) — edit freely; comments ok\n",
        )
        for p in paths:
            f.write(f"{p}\n")

    print(f"[kit] wrote {out_path}")


ALWAYS_KEEP_BASENAMES = {".gitkeep", ".gitignore"}


def _apply_overrides_and_sentinels(
    paths: list[str],
    *,
    repo_root: Path,
    force_include_csv: str | None,
    force_exclude_csv: str | None,
    keep_sentinels: str = "none",
) -> list[str]:
    """Mode-agnostic post-filter that enforces precedence:
    1) optional sentinel basenames
    2) force_exclude
    3) force_include
    (regular include/exclude already applied upstream).
    """

    def to_list(csv: str | None) -> list[str]:
        if not csv:
            return []
        return [s.strip() for s in csv.split(",") if s.strip()]

    def rel(p: str) -> str:
        return str(Path(p).resolve().relative_to(repo_root))

    as_set: set[str] = set(paths)

    # 1) optional sentinels
    if keep_sentinels in {
        "warehouse",
        "segmentation_audit",
        "kibana",
        "all",
    }:
        for base in ALWAYS_KEEP_BASENAMES:
            if keep_sentinels == "warehouse":
                patts = [
                    ".warehouse/yard/**/{base}",
                    ".warehouse/entry/{base}",
                    ".warehouse/draft/{base}",
                ]
            elif keep_sentinels == "segmentation_audit":
                patts = ["tools/audit/report/segmentation/{base}"]
            elif keep_sentinels == "kibana":
                patts = ["docker/kibana/generated/{base}"]
            elif keep_sentinels == "all":
                patts = ["**/{base}"]
            else:
                patts = []
            for patt in patts:
                for p in repo_root.glob(patt.format(base=base)):
                    if p.is_file():
                        as_set.add(rel(str(p)))

    fi = to_list(force_include_csv)
    fe = to_list(force_exclude_csv)

    # 2) force_exclude (remove matches)
    if fe:
        to_remove: set[str] = set()
        for pat in fe:
            for p in repo_root.glob(pat):
                if p.is_file():
                    rp = rel(str(p))
                    if rp in as_set:
                        to_remove.add(rp)
        as_set.difference_update(to_remove)

    # 3) force_include (add matches)
    if fi:
        for pat in fi:
            for p in repo_root.glob(pat):
                if p.is_file():
                    as_set.add(rel(str(p)))

    return sorted(as_set)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Generate a Kit (file list) for Packing using either dir-filter "
            "or static-analysis strategy."
        ),
    )
    ap.add_argument(
        "--mode",
        choices=("dir", "analysis"),
        default="dir",
        help=("Strategy: 'dir' (filters) or 'analysis' " "(static entrypoint)."),
    )
    ap.add_argument(
        "--out",
        required=True,
        help=("Output kit path (e.g., .warehouse/yard/kits/<name>.txt)."),
    )
    ap.add_argument(
        "--git",
        action="store_true",
        help="Include git tracked.",
    )
    ap.add_argument(
        "--untracked",
        action="store_true",
        help="Include git untracked.",
    )
    ap.add_argument(
        "--ext",
        help="Extensions CSV: py,md,sh",
    )
    ap.add_argument(
        "--include",
        help="Include globs CSV.",
    )
    ap.add_argument(
        "--exclude",
        help="Exclude globs CSV.",
    )
    ap.add_argument(
        "--keep-hidden",
        action="store_true",
        help="Keep dotfiles in dir walk",
    )
    ap.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symlinks in dir walk",
    )
    ap.add_argument(
        "--combine",
        default="union",
        choices=("union", "intersect", "graph", "dir"),
    )
    ap.add_argument(
        "--import-scope",
        default="used",
        choices=("used", "all", "entry-all"),
    )
    ap.add_argument(
        "--star-policy",
        default="warn",
        choices=("include", "warn", "skip"),
    )
    ap.add_argument(
        "--max-depth",
        type=int,
        default=0,
    )
    ap.add_argument(
        "--force-include",
        help="CSV of globs to force-include (analysis mode)",
        default=None,
    )
    ap.add_argument(
        "--force-exclude",
        help="CSV of globs to force-exclude (analysis mode)",
        default=None,
    )
    ap.add_argument(
        "--keep-sentinels",
        choices=(
            "none",
            "warehouse",
            "segmentation_audit",
            "kibana",
            "all",
        ),
        default="none",
        help=(
            "Sentinel mode: "
            "none (default), "
            "warehouse (yard + provision entry/draft), "
            "segmentation_audit (report), "
            "kibana (docker templates), "
            "all (any .gitignore sentinel found)"
        ),
    )
    ap.add_argument(
        "--plan",
        action="store_true",
        help="Print a short summary of selection (counts per source + combine).",
    )
    ap.add_argument(
        "--entry",
        help=("Entrypoint .py " "(required if --mode analysis)."),
    )
    ap.add_argument(
        "--entry-file",
        help=(
            "Repo-relative source file for shim. "
            "If provided or CLASS/METHOD given, "
            "a shim is generated and used as --entry."
        ),
    )
    ap.add_argument(
        "--class",
        dest="cls",
        help=("Optional class name for shim " "(e.g. ScriptWritingStage)"),
    )
    ap.add_argument(
        "--method",
        help="Optional method name for shim (e.g. run)",
    )
    ap.add_argument(
        "--kit-name",
        help="Kit name (used to name the shim)",
        default="kit",
    )
    args = ap.parse_args()

    repo_root = _repo_root()
    os.chdir(repo_root)

    if args.mode == "dir":
        from generators.dir_filter import (
            build_file_list as dir_build,
        )

        paths = dir_build(
            repo_root=repo_root,
            use_git_tracked=args.git,
            include_untracked=args.untracked,
            extensions_csv=args.ext,
            include_globs_csv=args.include,
            exclude_globs_csv=args.exclude,
            keep_hidden=args.keep_hidden,
            follow_symlinks=args.follow_symlinks,
        )
    else:
        # If no --entry but given --entry-file
        # (or CLASS/METHOD), synthesize a shim and use that.
        entry_path = args.entry
        if not entry_path and (args.entry_file or args.cls or args.method):
            # lazy import: generate shim
            from entry_shim import make_shim

            repo_root = _repo_root()
            kit_name = args.kit_name or "kit"
            out = make_shim(
                repo_root=repo_root,
                kit_name=kit_name,
                entry_file=args.entry_file or (args.entry or ""),
                cls=args.cls,
                method=args.method,
                out_dir=repo_root / ".warehouse/entry",
            )
            entry_path = str(out.relative_to(repo_root))

        if not entry_path:
            print(
                "[err] analysis mode needs --entry "
                "(or --entry-file/--class/--method "
                "to synthesize one)",
                file=sys.stderr,
            )
            return 2

        from generators.dependency_strategy import (
            build_file_list as dep_build,
        )

        paths = dep_build(
            repo_root=repo_root,
            entry_path=Path(entry_path),
            import_scope=args.import_scope,
            star_policy=args.star_policy,
            max_depth=args.max_depth,
            use_git_tracked=args.git,
            include_untracked=args.untracked,
            extensions_csv=args.ext,
            include_globs_csv=args.include,
            exclude_globs_csv=args.exclude,
            combine=args.combine,
        )
        if args.plan:
            # For plan, recompute individual sets to show counts (cheap enough).
            from analyzers.dependency_closure.core import (
                Options,
                build_paths,
            )
            from generators.dependency_strategy import (
                _rel_list,
            )
            from generators.dir_filter import (
                build_file_list as dir_list,
            )

            g_list = build_paths(
                repo_root,
                Path(entry_path),
                Options(
                    import_scope=args.import_scope,
                    star_policy=args.star_policy,
                    max_depth=args.max_depth,
                ),
            )
            d_list = dir_list(
                repo_root=repo_root,
                use_git_tracked=args.git,
                include_untracked=args.untracked,
                extensions_csv=args.ext,
                include_globs_csv=args.include,
                exclude_globs_csv=args.exclude,
            )
            g = set(_rel_list(g_list, repo_root))
            d = set(_rel_list(d_list, repo_root))
            u = g | d
            i = g & d
            print(
                f"[plan] combine={args.combine} "
                f"import_scope={args.import_scope} "
                f"star_policy={args.star_policy} "
                f"max_depth={args.max_depth}",
                file=sys.stderr,
            )
            print(
                f"[plan] graph={len(g)} dir={len(d)} union={len(u)} intersect={len(i)}",
                file=sys.stderr,
            )
    # Enforce sentinels + force_* for BOTH modes (single code path)
    paths = _apply_overrides_and_sentinels(
        paths,
        repo_root=repo_root,
        force_include_csv=args.force_include,
        force_exclude_csv=args.force_exclude,
        keep_sentinels=args.keep_sentinels,
    )

    _write_kit(Path(args.out), paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
