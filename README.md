# Warehouse

The **warehouse** is a context packaging utility for preparing code context
for LLMs and debugging workflows.

It is not part of the platform spine. It does not own topology truth,
orchestration, governance, or scheduling.

## Structure

```

tools/warehouse/
provision/      # drafts → kits (plans, file lists)
yard/           # active warehouse floor
kits/         # file lists (curated subsets of code/docs)
crates/       # bundled outputs (LLM-ready context files)
pallets/      # symlink workspaces (materialized kits for editing)

```

## Metaphor

- **Provision**: draw up the plans (turn drafts into kits).  
- **Kits**: organized lists of files.  
- **Crates**: sealed bundles built from kits, shipped to LLMs.  
- **Pallets**: temporary workspaces made from kits, ready to load into an editor.  
- **Yard**: the floor space where all active materials are staged.

The warehouse is where we **provision, assemble, and stage** everything before it’s handed off.


## Crate building

Use `scripts/pack_kits_into_crate.sh` to turn a kit list into one or more crate files.
Flags:

- `--max-lines-per-output N` – split outputs when exceeding `N` lines (default 3000)
- `--header-label "KIT MEMBER"` – customize the header label

Each emitted crate file begins with a `#` comment noting its repo-relative path.
When splitting occurs, outputs are placed in a subdirectory named after the
requested crate; single-part crates remain at the specified output path without
any `.part1` suffix.

Example with rotation and explicit part list:

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
