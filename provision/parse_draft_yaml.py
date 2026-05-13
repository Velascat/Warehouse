#!/usr/bin/env python3
# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
# /tools/warehouse/provision/parse_draft_yaml.py

"""Parse YAML drafts and emit CLI flags or JSON."""

import argparse
import json
from pathlib import Path

import yaml


def to_cli(cfg: dict) -> list[str]:
    kit = cfg.get("kit") or {}
    sel = cfg.get("selection") or {}
    ana = cfg.get("analysis") or {}
    combine = cfg.get("combine", "union")
    beh = cfg.get("behavior") or {}

    args: list[str] = []

    mode = ana.get("mode") or "dir"
    args += ["--mode", mode]

    kit_name = kit.get("name")
    if kit_name:
        args += ["--kit-name", kit_name]

    if sel.get("git", False):
        args += ["--git"]
    if sel.get("untracked", False):
        args += ["--untracked"]
    ext = sel.get("ext")
    if ext:
        joined = ",".join(ext) if isinstance(ext, list) else str(ext)
        args += ["--ext", joined]
    inc = sel.get("include")
    if inc:
        joined = ",".join(inc) if isinstance(inc, list) else str(inc)
        args += ["--include", joined]
    exc = sel.get("exclude")
    if exc:
        joined = ",".join(exc) if isinstance(exc, list) else str(exc)
        args += ["--exclude", joined]
    if sel.get("hidden", False):
        args += ["--keep-hidden"]
    if sel.get("follow_symlinks", False):
        args += ["--follow-symlinks"]

    if mode == "analysis":
        ef = ana.get("entry_file")
        if ef:
            args += ["--entry-file", ef]
        cls = ana.get("class")
        if cls:
            args += ["--class", cls]
        mth = ana.get("method")
        if mth:
            args += ["--method", mth]
        sc = ana.get("import_scope")
        if sc:
            args += ["--import-scope", sc]
        sp = ana.get("star_import_policy")
        if sp:
            args += ["--star-policy", sp]
        md = ana.get("max_graph_depth")
        if md is not None:
            args += ["--max-depth", str(md)]

    # Force overrides now live under selection; keep analysis.* as fallback.
    sel_fi = sel.get("force_include") or []
    ana_fi = ana.get("force_include") or []
    sel_fe = sel.get("force_exclude") or []
    ana_fe = ana.get("force_exclude") or []

    def _join_list(v):
        if not v:
            return None
        return ",".join(v) if isinstance(v, list) else str(v)

    fi_joined = _join_list(sel_fi or ana_fi)
    fe_joined = _join_list(sel_fe or ana_fe)
    if fi_joined:
        args += ["--force-include", fi_joined]
    if fe_joined:
        args += ["--force-exclude", fe_joined]

    ks = sel.get("keep_sentinels")
    if ks:
        args += ["--keep-sentinels", str(ks)]

    args += ["--combine", combine]

    if beh.get("plan", False):
        args += ["--plan"]

    return args


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--emit", choices=("cli", "json"), default="cli")
    parsed = ap.parse_args()

    path = Path(parsed.file)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    if parsed.emit == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        cli = to_cli(data)

        def q(s: str) -> str:
            if all(c not in s for c in " \t'\""):
                return s
            inner = s.replace("'", "'\"'\"'")
            return "'" + inner + "'"

        print(" ".join(q(s) for s in cli))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
