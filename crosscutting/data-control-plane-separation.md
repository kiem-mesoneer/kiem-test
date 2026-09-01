---
status: active
---

# Data-Plane / Control-Plane Separation

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

mesoneer has regulated tenants (e.g. Swiss Olympic) whose data must be pinned to a Swiss region,
while management tooling (CI/CD orchestration, Terraform state, monitoring configuration) has no
such constraint and benefits from running wherever it's cheapest/simplest to operate. Without an
explicit split, teams default to keeping everything — data and management — in the same region
"to be safe," which is both more expensive and harder to reason about than actually separating
the two concerns. This principle applies across all Tier-1 Reference Architectures so the split is
consistent rather than reinvented per project.

## Rules

### Definition: what belongs in each plane

- **Data plane**: anything holding or transporting customer/tenant data at rest or in transit —
  databases, event stores, object storage, message broker payloads. This must be pinned to the
  tenant's required region.
- **Control plane**: anything that configures, deploys, or observes the system without touching
  tenant data payloads directly — CI/CD pipelines, Terraform/IaC state, monitoring/alerting
  config, feature-flag services. This can run from a non-Swiss region.

**Do this:**
```text
Terraform state bucket: West Europe (Azure)         ← control plane
Postgres instance holding athlete records: Switzerland North  ← data plane
```

**Not this:**
```text
Everything — including CI/CD state and monitoring dashboards — hosted in Switzerland North
"to keep it simple", at 2-3x the cost with no compliance benefit
```

### The split is enforced at the infrastructure-module boundary, not left to documentation

- Region pinning is a parameter on the Terraform module that provisions the data-plane resource
  (database, event hub namespace, storage account) — not a note in a wiki page that someone has
  to remember to follow.

**Do this:**
```hcl
module "tenant_database" {
  source = "../modules/postgres"
  region = "switzerlandnorth"   # hardcoded for data-plane resources, not a variable
}

module "cicd_state_backend" {
  source = "../modules/storage-account"
  region = var.control_plane_region   # free to be westeurope, cheapest available
}
```

**Not this:**
```hcl
module "tenant_database" {
  source = "../modules/postgres"
  region = var.default_region   # same variable used everywhere — one config change
                                  # away from accidentally moving tenant data
}
```

### Applicability per Tier-1 Reference Architecture

- **Event-driven** ([RA](../reference-architectures/event-driven.md)): the broker's data-plane
  endpoint (message payloads) is regionally pinned; the RA's deployment/CI config is not.
- **Multi-tenant data isolation** ([RA](../reference-architectures/multi-tenant-data-isolation.md)):
  the per-tenant database/schema is the data plane; the provisioning automation that creates it is
  control plane and can run centrally regardless of tenant region.
- **Standard stack, Frontend SPA+BFF, Serverless, Workflow automation**: same split applies to
  each RA's persistent store and broker; see each RA's own Deployment View for the concrete
  region assignment.

**Do this:**
```text
Multi-tenant RA: "provisioning-service" (control plane, West Europe) creates a new
per-tenant Postgres schema (data plane, region taken from the tenant's residency requirement).
```

**Not this:**
```text
A single "region" setting on the whole tenant-onboarding pipeline, applied uniformly to both
the provisioning automation and the resulting tenant database
```

### Anti-patterns to avoid

- **Don't** put tenant data in control-plane telemetry — e.g. logging a full order payload to a
  centrally-hosted log aggregator defeats the residency guarantee even if the database itself is
  correctly pinned.
- **Don't** treat "control plane can run anywhere" as license to skip access controls — control
  plane access (e.g. Terraform apply credentials) can still indirectly affect data-plane resources
  and must be scoped accordingly.

## Tooling & Enforcement

- Region parameters on the shared Terraform modules (`modules/postgres`, `modules/eventhub`,
  `modules/storage-account`) — data-plane modules take a hardcoded/required region, control-plane
  modules take a free-choice variable.
- Referenced from §8 (Crosscutting Concepts) of every Tier-1 Reference Architecture's arc42 doc.
- No automated policy check yet (e.g. an Azure Policy / OPA rule blocking a data-plane resource
  from a non-approved region) — tracked as a follow-up, not solved by this document alone.
