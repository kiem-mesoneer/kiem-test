---
status: active
---

# Architectural Quality Metrics & KPIs Catalogue

> **Last updated**: 2026-09-01
> **Status**: Active (v1.0 — finalized)

## Why

Every mesoneer project picked its own quality metrics, or none at all, which made it impossible to
compare architectural health across projects or spot a systemic problem (e.g. pipeline duration
creeping up org-wide) before it became a crisis on one specific team. This catalogue defines the
minimum set every project tracks, where the data comes from, and — just as importantly — where
this project's responsibility ends: it defines *what* to measure, not a dashboard. Reporting is
assumed to land on a future Internal Developer Platform (Port or equivalent); until then, projects
report against this catalogue using their existing tooling.

## Rules

### The KPI shortlist (from stakeholder interviews)

- The longlist covered availability/SLO, DORA metrics, error-budget burn, pipeline duration,
  security-finding SLA, dependency freshness, and ADR coverage. A candidate is shortlisted only if
  at least 2 SAs flagged it as actionable (not just "nice to know") during interviews.

**Do this:**
```yaml
candidate: change_failure_rate
source: "GitHub Actions deployment events + incident labels"
flagged_by: [toai, linh]        # 2+ SAs → shortlisted
actionable: "a rising rate points directly at insufficient test coverage or a bad rollout gate"
```

**Not this:**
```yaml
candidate: lines_of_code_per_service
flagged_by: []                   # nobody could say what action follows from this number
actionable: "unclear"            # → not shortlisted
```

### Per-metric definition: formula, source, threshold, owner

Every shortlisted metric is defined the same way — a formula anyone can recompute, a concrete data
source (not "the observability stack" in the abstract), a target threshold, and one owning role.

| Metric | Formula | Data source | Target | Owner |
|---|---|---|---|---|
| Availability / SLO adherence | uptime / total time, per service SLO | Observability stack (Azure Monitor / Datadog) | ≥ service's committed SLO (e.g. 99.9%) | Service tech lead |
| Deployment frequency | deploys to prod / week | GitHub Actions / Azure DevOps deployment events | ≥ 1/week per active service | Team tech lead |
| Lead time for changes | PR-merge timestamp → prod-deploy timestamp | GitHub Actions + deployment tags | < 1 business day | Team tech lead |
| Change failure rate | failed deploys (rollback/hotfix within 24h) / total deploys | GitHub Actions deployment events + incident labels | < 15% | Team tech lead |
| Mean time to recovery (MTTR) | incident-open → incident-resolved | Incident tracker (Jira/PagerDuty) | < 4h for P1/P2 | On-call lead |
| API error-budget burn | 5xx rate vs. SLO error budget, rolling 30d | Observability stack | < 100% of budget consumed | Service tech lead |
| Build & test pipeline duration | p90 pipeline wall-clock time | GitHub Actions / Azure DevOps run history | < 15 min | Team tech lead |
| Security-finding SLA | time from finding opened → remediated, by severity | Security scanning tool (SAST/dependency scan) | Critical < 7d, High < 30d | Security champion |
| Dependency freshness | % of direct dependencies within 1 major version of latest | Dependency audit (see `dependency-upgrade-audit` tooling) | ≥ 80% | Team tech lead |
| ADR coverage | # accepted ADRs referenced from arc42 §9 / # architecturally significant decisions made | Manual review at architecture support intake | Reviewed quarterly, no hard target yet | SA group |

**Do this:**
```yaml
metric: lead_time_for_changes
formula: "deploy_timestamp - pr_merge_timestamp"
source: "github_actions.deployment_tags"
target: "< 1 business day"
owner: "team tech lead"
```

**Not this:**
```yaml
metric: lead_time_for_changes
formula: "however long it feels like it takes"
source: "ask the team"
target: "fast"
owner: "everyone"
```

### The IDP (Port) boundary — this project defines the contract, not the dashboard

- This catalogue defines each metric's **data contract**: its formula, source, collection cadence,
  and owning team. A future IDP (Port or equivalent) is responsible for *ingesting* that contract
  and *rendering* it — this project does not build, host, or maintain any dashboard.
- Until an IDP exists, projects self-report against this catalogue using whatever mechanism is
  already available (a spreadsheet, an existing Grafana/Datadog dashboard) — clearly labeled as an
  interim, pre-IDP mechanism so nobody mistakes it for the permanent reporting surface.

**Do this:**
```json
{
  "metric": "deployment_frequency",
  "shape": {"service": "string", "week": "date", "count": "integer"},
  "collection_cadence": "weekly",
  "owning_team": "string"
}
```
*(This is the handoff contract a future IDP would ingest — this project ships the contract, not the ingester.)*

**Not this:**
```text
"We'll just build a small internal dashboard for this ourselves in the meantime"
(scope creep into IDP territory that this project explicitly excludes — see Foundations
project's Out of Scope: "Reporting dashboard / Internal Developer Platform")
```

## Tooling & Enforcement

- Interim reporting: each team's existing observability dashboards + a shared spreadsheet tracking
  the 10 metrics above per project, reviewed quarterly by the SA group.
- Cross-referenced from every project's arc42 doc at §10 (Quality Requirements) and §11 (Risks &
  Technical Debt).
- No automated collection pipeline yet for metrics without an existing tool source (e.g. ADR
  coverage is manually reviewed) — tracked as a gap for the future IDP integration, not solved
  here.
