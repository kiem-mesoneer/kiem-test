# Internal Socialization — arc42 Workshop & Blueprint Walkthroughs

> Deliverable for DS-442. Not a Confluence-published convention page (no `status` frontmatter /
> not registered in `confluence.yaml`) — this is the internal rollout plan + materials index for
> the workshop series, kept in-repo so it stays versioned alongside the content it walks through.

## Format

Rather than one big-bang session at the very end (a schedule risk when all six RAs land close
together), socialization runs as **one 60-minute session per artifact**, scheduled as soon as that
artifact is finalized:

- 20 min walkthrough by the artifact's author/SA
- 30 min Q&A
- 10 min feedback form (kept open for 1 week after the session)

Every session is recorded and the recording + feedback summary is linked from that artifact's own
Confluence page, so someone who joins the walkthrough late still gets the context.

## Session plan

| # | Session | Depends on | Owner |
|---|---|---|---|
| 1 | arc42/C4 template + adoption guide | DS-274, DS-275 | SA who piloted the adoption guide |
| 2 | ADR process & governance (template, lifecycle, escalation) | DS-271, DS-272 | SA group |
| 3 | RA walkthrough: Event-driven / message-based | DS-276 | RA author |
| 4 | RA walkthrough: Standard stack (Angular + Spring Boot + Postgres) | DS-432 | RA author |
| 5 | RA walkthrough: Multi-tenant data isolation | DS-277 | RA author |
| 6 | RA walkthrough: Frontend SPA with BFF | DS-433 | RA author |
| 7 | RA walkthrough: Serverless workloads | DS-434 | RA author |
| 8 | RA walkthrough: Workflow automation | DS-435 | RA author |
| 9 | Quality metrics catalogue + how to self-report | DS-436/437/438 | SA group |

## Feedback capture template

```markdown
## Session: <name>  |  Date: <date>  |  Attendees: <count>

**What was unclear?**
-

**What would you change about the RA/process before adopting it in your project?**
-

**Follow-up ADR or support request needed?**
- [ ] Yes — filed as: <link>
- [ ] No
```

## Outcome tracking

- Feedback that changes a convention doc is folded directly into that doc (per the repo's "rewrite,
  do not append" convention) — not left in a separate changelog.
- Feedback that surfaces a genuinely new decision is filed as an [Architecture Support
  Request](../architecture-support/support-request-process.md), which may produce a new ADR.
- Session recordings and feedback-form links are added to each artifact's Confluence page after
  its session, not tracked in this file (this file is the plan, not the live log).
