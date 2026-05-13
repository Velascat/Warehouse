# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
from __future__ import annotations

"""Tests for resolving relative imports in used-scope analysis."""

from pathlib import Path

from provision.analyzers.dependency_closure.core import (
    Options,
    build_paths,
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_used_scope_resolves_relative_from(
    tmp_path: Path,
) -> None:
    root = tmp_path
    pkg = root / "src" / "pkg"
    entry = pkg / "a.py"
    target = pkg / "sub" / "mod.py"

    _write(target, "VALUE = 1\n")
    _write(pkg / "sub" / "__init__.py", "")
    _write(pkg / "__init__.py", "")
    _write(
        entry, "from .sub.mod import VALUE as V\nused = V\n"
    )

    files = build_paths(
        root=root,
        entry=entry,
        opt=Options(
            import_scope="used",
            star_policy="warn",
            max_depth=0,
        ),
    )

    assert "src/pkg/a.py" in files
    assert "src/pkg/sub/mod.py" in files
