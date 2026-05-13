# Changelog

All notable changes to Warehouse are documented here.

## [Unreleased]

### Fixed
- Add `timeout=` to `subprocess.check_output` calls in `provision_kit_from_draft.py` and `dir_filter.py` (C11).
- Add `ensure_ascii=False` to `json.dumps` in `parse_draft_yaml.py` and `dependency_closure/cli.py` (C41).
- Fix module-level import ordering in `dependency_closure/core.py` (RUFF E402).
- Add `tests/conftest.py` with venv guard (S4).
