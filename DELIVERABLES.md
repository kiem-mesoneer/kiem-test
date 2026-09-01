# Deliverables Traceability — DS-269

Maps each of the 19 Jira stories under the [Foundations - Architecture Conventions
epic](https://mesoneerag.atlassian.net/browse/DS-269) to what was actually built in this repo.
Jira itself was **not** modified as part of this exercise — this file is the local record of what
"done" looks like for each story.

| # | Jira | Story | What was built | Honest caveat |
|---|---|---|---|---|
| 1 | [DS-271](https://mesoneerag.atlassian.net/browse/DS-271) | ADR template & lifecycle | [`adr/adr-template-lifecycle.md`](adr/adr-template-lifecycle.md), [`adr/0000-adr-template.md`](adr/0000-adr-template.md), dogfood ADRs [0001](adr/0001-adopt-arc42.md)/[0002](adr/0002-store-adrs-in-git.md) | — |
| 2 | [DS-272](https://mesoneerag.atlassian.net/browse/DS-272) | ADR governance model | [`adr/adr-governance-model.md`](adr/adr-governance-model.md) | Branch-protection/CODEOWNERS enforcement described but not wired to a real GitHub repo (this is a local sandbox, not pushed anywhere) |
| 3 | [DS-273](https://mesoneerag.atlassian.net/browse/DS-273) | ADR fan-out sync (Git→Confluence, Git→Claude plugin) | Path 1 (Confluence): `.github/publish.py` + `.github/workflows/publish.yml` (copied from the real pipeline). Path 2 (Claude plugin): `scripts/package_claude_plugin.py`, `scripts/check_sync_drift.py`, `.github/workflows/sync-claude-plugin.yml` — both **run successfully** against this repo's real content | Path 1 has never actually published (no `CONFLUENCE_ROOT_PAGE_ID` set, and doing so would touch the real production Confluence space, which was explicitly out of scope) |
| 4 | [DS-274](https://mesoneerag.atlassian.net/browse/DS-274) | arc42/C4 template published | [`documentation-template/arc42-c4-template.md`](documentation-template/arc42-c4-template.md) | — |
| 5 | [DS-275](https://mesoneerag.atlassian.net/browse/DS-275) | arc42 adoption guide + pilot | [`documentation-template/adoption-guide.md`](documentation-template/adoption-guide.md) | The guide is real; the "pilot on one live project" acceptance criterion is **not** satisfiable in this exercise — there is no live project to pilot it on. Treat this story as guide-complete, pilot-outstanding |
| 6 | [DS-276](https://mesoneerag.atlassian.net/browse/DS-276) | RA: Event-driven / message-based | [`reference-architectures/event-driven.md`](reference-architectures/event-driven.md) | — |
| 7 | [DS-277](https://mesoneerag.atlassian.net/browse/DS-277) | RA: Multi-tenant data isolation | [`reference-architectures/multi-tenant-data-isolation.md`](reference-architectures/multi-tenant-data-isolation.md) | — |
| 8 | [DS-278](https://mesoneerag.atlassian.net/browse/DS-278) | Claude plugin sync + adoption review | `claude-plugin/skills/{adr-lookup,arc42-template,reference-architectures}/`, [`claude-integration/adoption-review.md`](claude-integration/adoption-review.md) | "Adoption metrics reviewed" is based on artifact counts in this repo, not real usage telemetry — there are no real users of this test repo |
| 9 | [DS-432](https://mesoneerag.atlassian.net/browse/DS-432) | RA: Standard stack | [`reference-architectures/standard-stack.md`](reference-architectures/standard-stack.md) | — |
| 10 | [DS-433](https://mesoneerag.atlassian.net/browse/DS-433) | RA: Frontend SPA with BFF | [`reference-architectures/frontend-spa-bff.md`](reference-architectures/frontend-spa-bff.md) | — |
| 11 | [DS-434](https://mesoneerag.atlassian.net/browse/DS-434) | RA: Serverless workloads | [`reference-architectures/serverless-workloads.md`](reference-architectures/serverless-workloads.md) | — |
| 12 | [DS-435](https://mesoneerag.atlassian.net/browse/DS-435) | RA: Workflow automation | [`reference-architectures/workflow-automation.md`](reference-architectures/workflow-automation.md) | — |
| 13 | [DS-436](https://mesoneerag.atlassian.net/browse/DS-436) | KPI shortlist + interviews | [`quality-metrics/metrics-catalogue.md`](quality-metrics/metrics-catalogue.md) §"KPI shortlist" | Stakeholder interviews are simulated (the "flagged by 2+ SAs" rule is illustrated, not run against real interviews) |
| 14 | [DS-437](https://mesoneerag.atlassian.net/browse/DS-437) | Metrics catalogue v1 | Same file, §"Per-metric definition" table | — |
| 15 | [DS-438](https://mesoneerag.atlassian.net/browse/DS-438) | Finalize metrics + IDP boundary | Same file, §"IDP (Port) boundary" | — |
| 16 | [DS-439](https://mesoneerag.atlassian.net/browse/DS-439) | Architecture Support Request process | [`architecture-support/support-request-process.md`](architecture-support/support-request-process.md) | Jira request type / Slack channel described but not actually created anywhere |
| 17 | [DS-440](https://mesoneerag.atlassian.net/browse/DS-440) | Seed ADRs from Event-driven RA pilot | [ADR-0003](adr/0003-use-azure-event-hub-for-order-events-pilot.md), [0004](adr/0004-at-least-once-delivery-idempotent-consumers.md), [0005](adr/0005-event-schema-versioning-strategy.md) | — |
| 18 | [DS-441](https://mesoneerag.atlassian.net/browse/DS-441) | Crosscutting: data-plane/control-plane separation | [`crosscutting/data-control-plane-separation.md`](crosscutting/data-control-plane-separation.md) | — |
| 19 | [DS-442](https://mesoneerag.atlassian.net/browse/DS-442) | Internal socialization | [`socialization/arc42-workshop.md`](socialization/arc42-workshop.md) | This is the **plan and materials**, not a record of a workshop that actually happened — no real session was run |

## Known gap carried over from the real backlog

Both [DS-276](https://mesoneerag.atlassian.net/browse/DS-276) and
[DS-277](https://mesoneerag.atlassian.net/browse/DS-277) list a hard dependency on **DS-270 (SA)**
for review sign-off. DS-270 does not exist in Jira (confirmed via `searchJiraIssuesUsingJql` —
zero results). This implementation proceeded without that sign-off since the ticket doesn't exist
to block on; the real project still needs someone to either create DS-270 or drop the reference.

## What "implemented" means here, honestly

This is a from-scratch content build in a disposable local sandbox repo (`kiem-test`), done to
demonstrate what finishing all 19 Foundations stories would concretely produce. It is **not**:
- Published to the real Confluence space (publish pipeline exists and is copied verbatim from the
  real repo, but was never pointed at real credentials/root-page-id)
- Reviewed or approved by any actual SA (the governance model's PR-review flow is documented and
  would apply to a real PR, but no real reviewers exist for this sandbox)
- Piloted on a real project, or backed by real stakeholder interviews / workshop attendance

What *is* real: every file's content is complete (no placeholders), the ADR→Claude-plugin sync
pipeline actually runs and produces working output (`make sync-plugin`, `python3
scripts/check_sync_drift.py`), and every doc follows the repo's mandatory Why/Rules/Tooling &
Enforcement structure.
