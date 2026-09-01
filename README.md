# Architecture Convention — Implemented (DS-269)

This repo is the completed implementation of the **Foundations - Architecture Conventions** project
(Jira epic [DS-269](https://mesoneerag.atlassian.net/browse/DS-269)): company-wide ADR process &
governance, the arc42/C4 project documentation template, architecture support requests, reference
architectures for common workload patterns, architectural quality metrics/KPIs, and crosscutting
design principles.

See [DELIVERABLES.md](DELIVERABLES.md) for the full traceability from each of the 19 Jira stories
to what was built.

## Structure

| Directory | Confluence section | Covers |
|-----------|--------------------|--------|
| `adr/` | ADR Process & Governance | ADR template, lifecycle, governance model, and the seed ADRs from the Event-driven RA pilot |
| `documentation-template/` | Project Documentation Template (arc42/C4) | The arc42/C4 project documentation template and its adoption guide |
| `architecture-support/` | Architecture Support | Process for requesting architectural support |
| `reference-architectures/` | Reference Architectures | Tier 1 blueprints: event-driven/message-based, standard stack, multi-tenant data isolation, serverless workloads, frontend SPA with BFF, workflow automation |
| `quality-metrics/` | Architectural Quality Metrics & KPIs | The architectural quality metrics catalogue every project is expected to track |
| `crosscutting/` | Crosscutting Design Principles | Data-plane / control-plane separation, applied across the reference architectures |
| `claude-plugin/` | — | Packaged skill (`adr-lookup`) synced from `adr/` for AI-assisted architectural guidance |
| `claude-integration/` | — | Adoption review of the Claude plugin sync |
| `socialization/` | — | arc42 workshop + blueprint walkthrough materials |

Code-level conventions live in the **code-conventions** repo; infrastructure architecture decisions
live under Cloud Platform. Project-specific architecture content is owned by each project team,
using the template and process defined here.

## How to Contribute

1. Use `_templates/convention-template.md` as the starting point for new docs.
2. Place the file in the correct domain directory.
3. Register the page in `confluence.yaml`.
4. Open a PR — changes merged to `main` are auto-published to Confluence.

## Publishing to Confluence

```bash
make publish-install  # Install Python deps (first time only)
make publish          # Sync all docs to Confluence
```

Requires environment variables: `CONFLUENCE_URL`, `CONFLUENCE_USER`, `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE`, and `CONFLUENCE_ROOT_PAGE_ID`.

Only pages whose frontmatter is `status: active` are published; drafts are skipped until marked active.

## ADR → Claude plugin sync

```bash
python scripts/package_claude_plugin.py
```

Packages every ADR under `adr/*.md` (excluding the template/governance pages) into
`claude-plugin/skills/adr-lookup/`, versioned by the ADR count and a content hash. See
[claude-integration/adoption-review.md](claude-integration/adoption-review.md) for how this was
validated.

## Tooling

| Tool | Purpose |
|------|---------|
| GitHub Actions | Auto-publish on merge to `main`; sync ADRs into the Claude plugin skill |
| `make` | Orchestrate publish tasks |
