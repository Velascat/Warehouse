# Log

_Chronological continuity log. Decisions, stop points, what changed and why._
_Not a task tracker — that's backlog.md. Keep entries concise and dated._

- 2026-05-12 — RepoGraph boundary artifact wiring tightened to file-only: the
  custodian audit path now materializes `REPOGRAPH_BOUNDARY_ARTIFACT_FILE` from a
  source locator before invoking Custodian, and the remaining deployment-facing
  templates were aligned to `PlatformDeployment` naming.

## Recent Decisions

_Log significant choices here so they survive context resets._

| Decision | Rationale | Date |
|----------|-----------|------|
| [what was decided] | [why] | [date] |

## Stop Points

_Where did you leave off? What should be verified next session?_

- [what to pick up next]

## Notes

_Free-form scratch. Clear periodically — old entries can be deleted once no longer relevant._

---

## 2026-05-10 — GitHub username migration

- Updated repo-owned references from the previous GitHub username to `ProtocolWarden` after the account rename.
- Scope: license headers, GitHub URLs, workflow install commands, manifests, dependency URLs, examples, and local owner defaults where present.

## 2026-05-13 — Custodian audit cleanup (phase 1)

- C11: added timeout=10 to subprocess.check_output in provision_kit_from_draft.py; timeout=30 in dir_filter.py.
- C41: added ensure_ascii=False to json.dumps in parse_draft_yaml.py and dependency_closure/cli.py.
- RUFF: fixed E402 in dependency_closure/core.py (moved docstring before __future__ import).
- S4: added tests/conftest.py with venv guard.

## 2026-05-13 — Fix test collection errors and Python 3.12 glob regression

- Removed accidental bare filename statements on line 3 of test_overrides.py, test_parse_draft_yaml.py, and test_relative_imports.py that caused NameError/SyntaxError at pytest collection time.
- Fixed `_apply_overrides_and_sentinels` glob patterns: in Python 3.12, `Path.glob("a/**")` only matches directories. Added `_glob_files` helper that also tries `pat + "/*"` when pattern ends with `/**`, restoring Python 3.11 semantics for force_exclude and force_include. Fixed test: test_force_exclude_wins.
- All 7 tests pass.
