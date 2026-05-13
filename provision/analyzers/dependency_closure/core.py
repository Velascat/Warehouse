# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
# /tools/warehouse/provision/analyzers/dependency_closure/core.py
"""Dependency graph traversal for warehouse provisioning."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Options:
    import_scope: str = "used"  # "used" | "all" |
    # "entry-all"
    star_policy: str = "warn"  # "include" | "warn" | "skip"
    max_depth: int = 0  # 0 = unlimited


# ---------- path resolution ----------
def resolve_module_to_file(
    root: Path,
    module: str,
) -> Path | None:
    parts = module.split(".")
    for base in (root / "src", root):
        mod_py = base.joinpath(*parts).with_suffix(".py")
        pkg_init = base.joinpath(*parts, "__init__.py")
        for cand in (mod_py, pkg_init):
            if cand.exists() and cand.is_file():
                return cand
    return None


def pkg_name_for_file(
    root: Path,
    py_path: Path,
) -> str | None:
    for base in (root / "src", root):
        try:
            rel = py_path.resolve().relative_to(base.resolve())
        except Exception:
            continue
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].removesuffix(".py")
        if parts:
            return ".".join(parts)
    return None


# ---------- AST helpers ----------
def iter_imports(
    py_path: Path,
) -> Iterable[tuple[str, str | None, int, str | None, str | None],]:
    """Yields tuples:
    (kind, base, level, tail, asname)
    kind: "import" or "from"
    - import x as y           -> ("import","x",0,None,"y")
    - from a.b import c as d  -> ("from","a.b",0,"c","d")
    - from . import e         -> ("from",None,1,"e",None).
    """
    try:
        tree = ast.parse(
            py_path.read_text(encoding="utf-8"),
            filename=str(py_path),
        )
    except Exception:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield (
                    "import",
                    alias.name,
                    0,
                    None,
                    alias.asname,
                )
        elif isinstance(node, ast.ImportFrom):
            base, level = node.module, node.level or 0
            if node.names:
                for alias in node.names:
                    tail = alias.name if alias else None
                    yield (
                        "from",
                        base,
                        level,
                        tail,
                        alias.asname if alias else None,
                    )
            else:
                yield ("from", base, level, None, None)


def resolve_relative(
    module_base: str | None,
    level: int,
    tail: str | None,
) -> str | None:
    if level == 0:
        return tail
    if not module_base:
        return None
    parts = module_base.split(".")
    depth = max(0, len(parts) - level)
    prefix = parts[:depth]
    if tail:
        prefix += tail.split(".")
    return ".".join(prefix) if prefix else None


# ---------- “used” name tracking ----------
class UsedNameScanner(ast.NodeVisitor):
    def __init__(self):
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name):
        self.names.add(node.id)

    def visit_Attribute(self, node: ast.Attribute):
        # record base (e.g., `np` in `np.array`)
        cur = node
        while isinstance(cur, ast.Attribute):
            cur = cur.value
        if isinstance(cur, ast.Name):
            self.names.add(cur.id)
        self.generic_visit(node)


def imported_aliases(root: Path, py_path: Path) -> dict[str, str]:
    """Map 'binding name in this module' -> 'module that provides it'.
    Provider module names are normalized to absolute modules.
    - import numpy as np               => {'np': 'numpy'}
    - import package.sub as sub        => {'sub': 'package.sub'}
    - from a.b import c as d           => {'d':'a.b'}
    - from a.b import c                => {'c':'a.b'}
    - from a.b import *                => {'*':'a.b'} (star).
    """
    out: dict[str, str] = {}
    try:
        tree = ast.parse(
            py_path.read_text(encoding="utf-8"),
            filename=str(py_path),
        )
    except Exception:
        return out

    cur_mod = pkg_name_for_file(root, py_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bind = alias.asname or alias.name.split(".")[-1]
                out[bind] = alias.name
        elif isinstance(node, ast.ImportFrom):
            base_abs = resolve_relative(cur_mod, node.level or 0, node.module) or ""
            for alias in node.names or []:
                if alias.name == "*":
                    out["*"] = base_abs
                else:
                    bind = alias.asname or alias.name
                    out[bind] = base_abs
    return out


def used_provider_modules(
    py_path: Path,
    star_policy: str,
    root: Path,
) -> set[str]:
    """Return set of provider modules whose imported bindings are actually referenced."""
    binds = imported_aliases(root, py_path)
    try:
        tree = ast.parse(
            py_path.read_text(encoding="utf-8"),
            filename=str(py_path),
        )
    except Exception:
        return set()

    scanner = UsedNameScanner()
    scanner.visit(tree)

    used_mods: set[str] = set()
    for name in scanner.names:
        if name in binds:
            mod = binds[name]
            if mod:
                used_mods.add(mod)
    # star-import handling
    if "*" in binds:
        if star_policy == "include":
            if binds["*"]:
                used_mods.add(binds["*"])
        elif star_policy == "warn":
            # emit a human-friendly warning (non-fatal)
            print(
                "[dep-closure] warning: star import in "
                f"{py_path} from '{binds['*']}' "
                "ignored (STAR_IMPORT_POLICY=warn)",
            )
    return used_mods


# ---------- crawl ----------
def crawl(
    root: Path,
    entry: Path,
    opt: Options,
) -> list[Path]:
    root, entry = root.resolve(), entry.resolve()
    seen: set[Path] = set()
    stack: list[tuple[Path, int]] = [(entry, 0)]
    while stack:
        cur, depth = stack.pop()
        if cur in seen or not cur.exists() or not cur.is_file():
            continue
        seen.add(cur)

        cur_mod = pkg_name_for_file(root, cur)
        # decide which imports from this file are considered "active"
        imports: list[
            tuple[
                str,
                str | None,
                int,
                str | None,
                str | None,
            ],
        ] = list(iter_imports(cur))
        allowed_bases: set[str] | None = None

        # Decide which imports to follow from *this file* based on scope + depth.
        # - "all": allow all imports everywhere (allowed_bases=None -> no filtering)
        # - "used": only follow provider modules whose bindings are referenced in this file
        # - "entry-all":   entry (depth==0) -> all; deeper (depth>0) -> used
        if opt.import_scope == "used":
            allowed_bases = set(
                used_provider_modules(cur, opt.star_policy, root),
            )
        elif opt.import_scope == "entry-all":
            if depth == 0:
                allowed_bases = None
            else:
                allowed_bases = set(
                    used_provider_modules(
                        cur,
                        opt.star_policy,
                        root,
                    ),
                )
        else:
            allowed_bases = None

        for kind, base, level, _tail, _asname in imports:
            if kind == "import" and base:
                target_module = base
                if allowed_bases is not None and target_module not in allowed_bases:
                    continue
                tgt = resolve_module_to_file(root, target_module)
                if tgt and tgt not in seen and (opt.max_depth == 0 or depth + 1 <= opt.max_depth):
                    stack.append((tgt, depth + 1))
            elif kind == "from":
                abs_base = resolve_relative(cur_mod, level, base)
                # tail names are bindings; for scope=used we only care that the base module is used
                target_module = abs_base
                if target_module:
                    if allowed_bases is not None and target_module not in allowed_bases:
                        continue
                    tgt = resolve_module_to_file(root, target_module)
                    if tgt and tgt not in seen and (opt.max_depth == 0 or depth + 1 <= opt.max_depth):
                        stack.append((tgt, depth + 1))

    # Return only files within root
    return sorted(
        (p for p in seen if str(p).startswith(str(root))),
        key=lambda p: p.as_posix(),
    )


def build_paths(
    root: Path,
    entry: Path,
    opt: Options,
) -> list[str]:
    files = crawl(root, entry, opt)
    root_res = root.resolve()

    def _rel(p: Path) -> str:
        return str(p.resolve().relative_to(root_res))

    out = {_rel(entry)}
    out.update(_rel(p) for p in files if p != entry)
    return sorted(out)
