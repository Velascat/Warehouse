#!/usr/bin/env python3
# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
# /tools/warehouse/provision/analyzers/dependency_closure/cli.py
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import Options, build_paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--entry", required=True)
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
    ap.add_argument("--max-depth", type=int, default=0)
    args = ap.parse_args()
    paths = build_paths(
        Path(args.root),
        Path(args.entry),
        Options(
            import_scope=args.import_scope,
            star_policy=args.star_policy,
            max_depth=args.max_depth,
        ),
    )
    print(json.dumps({"entry": args.entry, "paths": paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
