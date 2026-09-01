---
status: active
---

# Reference Architecture: Workflow Automation (BPMN)

> **Last updated**: 2026-09-01
> **Status**: Active

## Why

Several mesoneer projects need long-running, human-in-the-loop processes — approvals, onboarding,
case handling — where the control flow itself is a business artifact that changes independently of
the code around it. Modeling that flow as BPMN makes it visible to business stakeholders and
diffable in Git, but only if teams draw a hard line between what belongs in the process diagram and
what belongs in application code, and pick one engine deliberately instead of re-litigating the
choice per project. Without that discipline, BPMN processes turn into either an unreadable diagram
that reimplements business logic in script tasks, or an unversioned side-channel of rules that
nobody can code-review. This RA fixes the engine choice, the process/code boundary, the deployment
topology, and the versioning discipline so every workflow-automation project starts from the same
defaults.

## Rules

### Engine selection: Flowable is the default; Camunda 7 / CIB seven are exceptions, not alternatives

- **Default to Flowable** for any new workflow-automation project. It is Apache 2.0 licensed, ships
  a first-class `flowable-spring-boot-starter` for embedded deployment, and is the engine mesoneer
  engineers already have production experience with — there is no "it depends" decision to make
  for a greenfield service.
- **Use CIB seven** only when a project already has significant investment in Camunda 7 process
  models, Camunda Modeler tooling, or team BPMN/DMN authoring skills built on the Camunda 7 API —
  and needs continued patch support now that Camunda 7 itself is past its vendor-supported
  lifecycle. CIB seven is an API-compatible fork, so this is a runtime swap, not a re-model.
- **Do not start new projects on Camunda 7** directly — it has no path forward without CIB seven's
  continued support, and Camunda 8 (Zeebe) is a different runtime architecture, not a drop-in
  successor, and is out of scope for this RA.
- **Camunda 8 / Zeebe** is deliberately excluded from this decision: if a project's real requirement
  is horizontally-scaled, cloud-native orchestration at the throughput Zeebe targets, that is a
  distinct architecture decision requiring its own RA and ADR — do not back into it by picking
  "Camunda" off this list.

**Do this:**
```text
New claims-approval service, no prior workflow-engine investment
  -> Flowable, embedded via flowable-spring-boot-starter

Existing service already running Camunda 7 process models authored by the business team,
Camunda 7 community support has ended
  -> Migrate the runtime dependency to CIB seven, keep the BPMN/DMN files unchanged
```

**Not this:**
```text
"Let's use Camunda 7 because the BA team knows the Modeler" for a brand-new service with no
existing Camunda 7 investment, ignoring that Camunda 7 has no supported forward path on its own
```

### Process model boundaries: BPMN owns flow and human interaction, Java owns decision logic

- BPMN describes **who does what, in what order, and where a human is involved** — start/end
  events, gateways, human task nodes, call activities. It does not contain business rule logic.
- Logic that needs to be unit-tested and code-reviewed the same way the rest of the service is —
  thresholds, scoring, eligibility checks — lives in a Spring Boot service task backed by an
  injectable `JavaDelegate`/service class, not inline in a script task and not as a DMN table
  maintained through the engine's own web console. A DMN table edited live in a running engine's
  admin UI is not versioned, not reviewed, and not covered by the service's test suite — it fails
  the same bar every other change to business logic has to clear.
- If a decision genuinely is a business-owned tabular rule set, express it as a `.dmn` file
  committed to the same repo as the process, reviewed in the same PR, and deployed by the same CI
  pipeline as the BPMN file — never edited directly against the running engine.

**Do this:**
```xml
<!-- approval-process.bpmn: flow and human task nodes only -->
<bpmn:userTask id="managerApproval" name="Manager Approval" flowable:assignee="${approverId}"/>
<bpmn:serviceTask id="checkAutoApproval" name="Check Auto-Approval Threshold"
                  flowable:delegateExpression="${autoApprovalDelegate}"/>
<bpmn:exclusiveGateway id="autoApprovedGateway"/>
```
```java
// AutoApprovalDelegate.java — versioned, reviewed, unit-tested like any other Java class
@Component("autoApprovalDelegate")
public class AutoApprovalDelegate implements JavaDelegate {

    private static final BigDecimal AUTO_APPROVAL_THRESHOLD = new BigDecimal("5000.00");

    @Override
    public void execute(DelegateExecution execution) {
        BigDecimal amount = (BigDecimal) execution.getVariable("requestAmount");
        execution.setVariable("autoApproved", amount.compareTo(AUTO_APPROVAL_THRESHOLD) < 0);
    }
}

@ExtendWith(MockitoExtension.class)
class AutoApprovalDelegateTest {
    @Test
    void approvesAmountsBelowThreshold() {
        // ordinary unit test — no engine required to verify the business rule
    }
}
```

**Not this:**
```text
A DMN decision table for the auto-approval threshold, maintained by editing it directly in the
Flowable admin console — no PR, no diff, no unit test, and no record of who changed the threshold
or when.
```

### Deployment topology: embedded engine by default, standalone only for shared/cross-team orchestration

- **Default: embedded engine.** Run Flowable inside the same Spring Boot process that owns the
  business logic, sharing that service's Postgres instance (a dedicated `ACT_*` schema, migrated
  independently of the application's Flyway migrations). This matches the Standard Stack's default
  of one deployable per bounded context and avoids operating a second runtime.
- **Standalone engine only when** the process genuinely spans multiple services owned by different
  teams and needs one shared orchestrator (e.g. a cross-team fulfillment process calling out to
  several bounded contexts as external task workers), or when the workflow engine's scaling and
  failure domain must be independent from the business logic that triggers it. Standing up a
  standalone engine is an explicit decision documented in the project's ADR — it is not the
  default you reach for because "it might need to scale later."

**Do this:**
```text
Single-team approval service, all human tasks and service tasks belong to that service
  -> embedded Flowable inside the Spring Boot app, ACT_* tables in that service's Postgres instance
```

**Not this:**
```text
Standing up a separate standalone Flowable REST service for a process used by exactly one
Spring Boot application, adding a second deployable, a second on-call surface, and a network hop
for every task completion with no corresponding cross-team requirement
```

### Human task UI patterns: a dedicated task-inbox screen, never the engine's own admin console

- Business users interact with human tasks through a purpose-built task-inbox screen in the
  Angular frontend, backed by a thin REST layer the owning service exposes over the engine's
  `TaskService` — never by giving business users direct access to Flowable's/Camunda's own
  cockpit/admin UI, which is an operator tool, not a business-user tool, and exposes engine
  internals the UI shouldn't have to explain.
- Task assignment should push a notification (e.g. email or Teams message via the existing
  notification integration) rather than relying on users to poll the inbox; the inbox itself
  remains the source of truth for "what do I need to act on right now."

**Do this:**
```java
@RestController
@RequestMapping("/api/tasks")
class TaskInboxController {

    private final TaskService taskService;

    @GetMapping("/my-tasks")
    ResponseEntity<List<TaskDto>> myTasks(@AuthenticationPrincipal UserPrincipal user) {
        List<Task> tasks = taskService.createTaskQuery()
            .taskAssignee(user.getId())
            .active()
            .list();
        return ResponseEntity.ok(tasks.stream().map(TaskDto::from).toList());
    }

    @PostMapping("/{taskId}/complete")
    ResponseEntity<Void> complete(@PathVariable String taskId, @RequestBody ApprovalDecision body) {
        taskService.complete(taskId, Map.of("approved", body.approved()));
        return ResponseEntity.noContent().build();
    }
}
```

**Not this:**
```text
Sending business approvers a link to the Flowable admin cockpit to complete their tasks, coupling
the UI business users see to engine upgrades and exposing process-instance internals they don't
need and shouldn't be able to touch.
```

### Versioning and long-running instance migration: never delete a process version that still has running instances

- Deploying a new BPMN version does **not** affect instances already running against an older
  version — Flowable/Camunda keep both versions deployed side by side under the same process
  definition key. That is the correct default behavior; do not "fix" it by deleting the old
  version at deploy time.
- Before removing an old process definition version, verify — programmatically, in the deploy
  pipeline or a pre-deletion check — that zero running instances reference it. If instances are
  still in flight and the new version must fully replace the old one, use the engine's explicit
  process instance migration API in a controlled, tested step; do not delete the old deployment
  out from under running instances.
- CI deploys BPMN files the same way it deploys application code: on every push that changes a
  `.bpmn`/`.dmn` file, a new version is deployed automatically; nothing is deployed by hand against
  a running engine.

**Do this:**
```java
long stillRunning = runtimeService.createProcessInstanceQuery()
    .processDefinitionId(oldDefinition.getId())
    .count();

if (stillRunning > 0) {
    throw new IllegalStateException(
        "Cannot remove process definition %s: %d instance(s) still running"
            .formatted(oldDefinition.getId(), stillRunning));
}
repositoryService.deleteDeployment(oldDefinition.getDeploymentId(), false);
```

**Not this:**
```text
repositoryService.deleteDeployment(oldDeploymentId, true); // cascade=true

Force-cascading the delete to clear out in-flight instances of the old version because the new
BPMN version "should replace it anyway" — this silently terminates whatever approvals or cases
were mid-flight.
```

### Integration with the Standard Stack

- A workflow-automation service is a Standard Stack service first: Spring Boot + Postgres, with the
  embedded engine's `ACT_*` tables living in the same Postgres instance as the service's own
  schema, in a dedicated schema namespace so the engine's own migrations never collide with the
  service's Flyway migrations.
- Process variables frequently carry tenant data (applicant details, claim amounts, case notes).
  That data is data plane per
  [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md) and
  must be pinned to the tenant's required region exactly like the rest of the Standard Stack
  Postgres instance — do not stand up a single centrally-hosted "workflow engine" shared across
  tenants with different residency requirements, since that would silently mix the tenants' data
  plane into one non-pinned store.
- The BPMN/DMN files themselves, and the CI pipeline that deploys them, are control plane and can
  be built and validated centrally regardless of tenant region — only the running engine's data
  (process instances, variables, task history) is data plane.

**Do this:**
```text
approval-service (Standard Stack: Spring Boot + Postgres, Switzerland North for a Swiss-regulated
tenant) embeds Flowable; ACT_* schema lives in the same regionally-pinned Postgres instance as the
service's own tables.
```

**Not this:**
```text
One shared standalone workflow engine, hosted centrally in West Europe, running process instances
for both a Swiss-regulated tenant and an unregulated tenant against the same Postgres instance.
```

## Tooling & Enforcement

- `flowable-spring-boot-starter` (or the CIB seven equivalent) is the only sanctioned way to embed
  the engine — no bespoke engine bootstrapping.
- BPMN/DMN files are validated and deployed by the same CI pipeline and same PR review process as
  the rest of the service's code; there is no direct-to-engine deployment path.
- A pre-undeploy check (as in the versioning rule above) runs in CI/CD before any process
  definition removal, failing the pipeline if running instances still reference it.
- Region pinning for the engine's `ACT_*` schema is enforced through the same Terraform Postgres
  module referenced in
  [Data-Plane / Control-Plane Separation](../crosscutting/data-control-plane-separation.md) — no
  separate provisioning path for workflow-engine storage.
- Engine choice (Flowable vs. CIB seven) and deployment topology (embedded vs. standalone) are
  recorded as an ADR at project start, per the company's ADR process, so the decision is traceable
  rather than implicit.
