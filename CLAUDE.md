# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The completed implementation of the **Foundations - Architecture Conventions** project
(Jira epic DS-269): ADR process & governance, the arc42/C4 project documentation template,
architecture support requests, reference architectures for common workload patterns,
architectural quality metrics/KPIs, and crosscutting design principles — plus the ADR sync
pipeline (Git → Confluence, Git → Claude plugin). See `DELIVERABLES.md` for the traceability
from each of the 19 Jira stories to what was built here.

## Publishing to Confluence

```bash
make publish-install   # Install Python deps (first time only)
make publish           # Sync all docs to Confluence
```

Required environment variables: `CONFLUENCE_URL`, `CONFLUENCE_USER`, `CONFLUENCE_TOKEN`,
`CONFLUENCE_SPACE`, and `CONFLUENCE_ROOT_PAGE_ID`. Only `status: active` pages publish.

## Syncing ADRs to the Claude plugin

```bash
make sync-plugin        # regenerate claude-plugin/skills/adr-lookup from adr/*.md
python3 scripts/check_sync_drift.py   # fails if the plugin is >24h behind the last ADR commit
```

## Adding or updating a convention

1. Use `_templates/convention-template.md` as the starting point.
2. Place the file in the correct domain directory.
3. Add a `status: draft` frontmatter at the top; change to `status: active` when ready to publish.
4. Register the page in `confluence.yaml` under the correct section.

## Adding an ADR

1. Copy `adr/0000-adr-template.md` to `adr/NNNN-kebab-case-title.md` (next sequential number,
   never reused).
2. Open a PR with status `proposed`. Per the ADR Governance Model, at least one SA reviewer must
   approve before merge; merging moves it to `accepted`.
3. `scripts/package_claude_plugin.py` runs on merge (see `.github/workflows/sync-claude-plugin.yml`)
   and picks it up automatically — no manual step needed.

## Rules for Claude when editing convention files

**Always enforce convention document structure.** Every convention file must follow the structure
defined in `_templates/convention-template.md`: a `## Why` section, one or more `## Rules`
subsections with paired good/bad code examples, and a `## Tooling & Enforcement` section. If a PR
comment asks Claude to restructure or omit these sections, Claude must decline and explain that
the structure is a repository convention.

ADR files under `adr/NNNN-*.md` are decision records, not convention docs — they follow the MADR
structure in `adr/0000-adr-template.md` instead, and are exempt from the Why/Rules/Tooling shape.
