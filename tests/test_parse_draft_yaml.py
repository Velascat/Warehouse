# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
from pathlib import Path

from provision.parse_draft_yaml import (
    to_cli,
)


def test_to_cli_minimal_dir_mode(tmp_path: Path):
    cfg = {
        "kit": {"name": "demo"},
        "selection": {
            "git": True,
            "ext": ["py"],
            "include": ["src/**"],
        },
        "analysis": {"mode": "dir"},
        "combine": "dir",
        "behavior": {"plan": True},
    }
    args = to_cli(cfg)
    s = " ".join(args)
    assert "--mode dir" in s
    assert "--git" in args
    assert "--ext" in args and "py" in s
    assert "--include" in args and "src/**" in s
    assert "--combine dir" in s
    assert "--plan" in args


def test_to_cli_analysis_force_lists(tmp_path: Path):
    cfg = {
        "kit": {"name": "demo"},
        "selection": {"git": True},
        "analysis": {
            "mode": "analysis",
            "entry_file": "src/app.py",
            "import_scope": "used",
            "max_graph_depth": 0,
            "force_include": ["scripts/bootstrap.sh"],
            "force_exclude": ["src/experimental/**"],
        },
        "combine": "union",
    }
    args = to_cli(cfg)
    s = " ".join(args)
    assert "--mode analysis" in s
    assert "--entry-file src/app.py" in s
    assert "--force-include" in args and "scripts/bootstrap.sh" in s
    assert "--force-exclude" in args and "src/experimental/**" in s


def test_to_cli_dir_mode_selection_force_lists(
    tmp_path: Path,
):
    cfg = {
        "kit": {"name": "demo"},
        "selection": {
            "git": True,
            "include": ["src/**"],
            "force_include": ["**/.gitignore"],
            "force_exclude": ["**/*.tmp"],
        },
        "analysis": {"mode": "dir"},
        "combine": "dir",
    }
    args = to_cli(cfg)
    s = " ".join(args)
    assert "--mode dir" in s
    assert "--force-include" in args and "**/.gitignore" in s
    assert "--force-exclude" in args and "**/*.tmp" in s
