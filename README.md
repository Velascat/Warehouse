# Warehouse

The **warehouse** is a context packaging utility for preparing code context
for LLMs and debugging workflows.

## What Warehouse Is

- a context provisioning and packaging tool
- a kit-based file selection and bundling system
- a staging ground for LLM-ready context crates
- a utility for preparing code subsets for assistant workflows

## What Warehouse Is Not

- part of the platform spine
- an owner of topology truth
- an orchestration or governance layer
- a scheduling or execution system

## Getting Started

```bash
# Provision a kit from a draft YAML spec
python -m provision.provision_kit_from_draft --draft yard/drafts/my_draft.yaml

# Pack a kit into a crate
scripts/pack_kits_into_crate.sh \
  --kit yard/kits/my_kit.txt \
  --output yard/crates/my_crate.txt
```

## Architecture Overview

```
provision/      # drafts → kits (plans, file lists)
yard/           # active warehouse floor
  kits/         # file lists (curated subsets of code/docs)
  crates/       # bundled outputs (LLM-ready context files)
  pallets/      # symlink workspaces (materialized kits for editing)
```

The flow: **draft YAML → provision → kit → pack → crate → LLM**.

- **Provision**: turn draft specs into kit file lists.
- **Kits**: curated lists of files scoped to a purpose.
- **Crates**: sealed bundles built from kits, shipped to LLMs.
- **Pallets**: temporary workspaces materialized from kits for editing.
- **Yard**: the floor space where all active materials are staged.

## Crate Building

Use `scripts/pack_kits_into_crate.sh` to turn a kit list into one or more crate files.
Flags:

- `--max-lines-per-output N` – split outputs when exceeding `N` lines (default 3000)
- `--header-label "KIT MEMBER"` – customize the header label

Each emitted crate file begins with a `#` comment noting its repo-relative path.
When splitting occurs, outputs are placed in a subdirectory named after the
requested crate; single-part crates remain at the specified output path without
any `.part1` suffix.

Example:

```bash
tools/warehouse/scripts/pack_kits_into_crate.sh \
  --kit tools/warehouse/yard/kits/script_writing.txt \
  --output tools/warehouse/yard/crates/script_writing.txt \
  --max-lines-per-output 2000 \
  --header-label "KIT MEMBER"
```

Output:

```
Packed 5 file(s) into 2 outputs (≤2000 lines each):
 - tools/warehouse/yard/crates/script_writing/script_writing.part1.txt
 - tools/warehouse/yard/crates/script_writing/script_writing.part2.txt
```
