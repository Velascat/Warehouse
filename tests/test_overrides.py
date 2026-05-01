# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
test_overrides.py

"""Tests for sentinel and force override behavior."""

from pathlib import Path

from provision.provision_kit_from_draft import (
    _apply_overrides_and_sentinels,
)


def test_sentinels_gitignore(tmp_path: Path):
    root = tmp_path
    a = root / ".warehouse/yard/kits/.gitignore"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text("*\n!.gitignore\n")
    out = _apply_overrides_and_sentinels(
        paths=[],
        repo_root=root,
        force_include_csv=None,
        force_exclude_csv=None,
        keep_sentinels="warehouse",
    )
    assert ".warehouse/yard/kits/.gitignore" in out


def test_force_exclude_wins(tmp_path: Path):
    root = tmp_path
    f = root / "src/experimental/x.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x=1")
    out = _apply_overrides_and_sentinels(
        paths=["src/experimental/x.py"],
        repo_root=root,
        force_include_csv=None,
        force_exclude_csv="src/experimental/**",
    )
    assert "src/experimental/x.py" not in out


def test_force_include_adds(tmp_path: Path):
    root = tmp_path
    f = root / "docs/keep.me"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("ok")
    out = _apply_overrides_and_sentinels(
        paths=[],
        repo_root=root,
        force_include_csv="docs/keep.me",
        force_exclude_csv=None,
    )
    assert "docs/keep.me" in out
