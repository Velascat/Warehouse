# Copyright (C) 2024 Dave Velasco. All rights reserved.
# Proprietary and confidential. Unauthorized use prohibited.
# /tools/warehouse/provision/analyzers/dependency_closure/__init__.py
"""Dependency closure analyzer."""

from .core import Options, build_paths

__all__ = ["build_paths", "Options"]
