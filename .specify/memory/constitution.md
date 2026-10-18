# Handoff Hub Constitution

This SDD constitution applies the project-wide rules in [`CONSTITUTION.md`](../../CONSTITUTION.md) to Spec Kit artifacts. The root constitution remains authoritative; keep both documents aligned when engineering policy changes.

**Version**: 1.0.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18

## Core Principles

### I. Preserve domain and channel boundaries

The Hub owns sessions, queues, routing, messages, authorization, and audit. Channel adapters transport messages but do not own Hub business rules or identities. Do not describe Teams or another external channel as integrated until an adapter and end-to-end test exist. Keep simulated messages clearly identified as simulations.

### II. Enforce identity and authorization in the backend

Authorization must be checked by the backend, not inferred from hidden navigation. Operators act only as the authenticated operator; do not simulate operational identities or act across operators. Supervisors and administrators do not answer or take over operator conversations. Auditors are read-only.

### III. Persist state and make mutations safe

Use the repository's SQLAlchemy and persistence patterns. Do not move durable routing, capacity, queue membership, dispatch turns, or audit state into process memory. SQLite POC mutations must preserve transactional and concurrency guarantees. Alembic changes are explicit and tested on disposable authorized labs; never implicitly migrate, seed, or test against the original POC database.

### IV. Protect credentials and user data

Do not commit passwords, hashes, tokens, real conversation content, or sensitive identifiers. Developer demo credentials belong only in the ignored local data file; synthetic lab credentials belong in the temporary lab directory. Do not expose the local POC as a production service or weaken authorization to simplify tests.

### V. Verify behavior with repository gates

Add or update focused tests for changed behavior, including authorization-negative and concurrency cases where relevant. Run `.\start.cmd --check` for project validation; it covers Pytest, Ruff, frontend architecture tests, TypeScript, and Vite. Report actual results and remaining manual gates; do not claim unexecuted checks passed.

### VI. Keep workspaces and user flows distinct

Operator, supervision, administration, and lab workspaces keep independent routes and shells. `web/src/App.tsx` coordinates routing and snapshots; workspace behavior belongs in the existing workspace/component boundaries. Essential commands remain reachable by keyboard and within supported viewports.

## Specification and Implementation Constraints

- Every feature specification states its goal, scope, model, contract, security, acceptance tests, limits, and rollback.
- Treat legacy scripts and existing behavior as requirements evidence only; do not copy legacy implementation or migrate its data.
- Reuse the current FastAPI, SQLAlchemy, SQLite POC, React, TypeScript, and Vite architecture unless an approved specification explicitly changes it.
- Keep production gates explicit: Entra ID/OIDC, versioned production migrations, multi-operation isolation, an external worker, and a real channel adapter remain unfinished.
- Do not add GitHub Actions. Execute tests, lint, and builds locally and record evidence in the relevant delivery documentation and PR.
- New Spec Kit feature artifacts use the generated `specs/` workflow. Existing historical and architecture specifications under `docs/specs/` remain in place; do not retroactively recreate the whole system as Spec Kit features.

## SDD Workflow

For each bounded new change, use the Copilot Spec Kit skills in order: `/speckit-specify`, `/speckit-clarify` when material ambiguity remains, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`, and `/speckit-converge`. Review generated artifacts before implementation, run the repository gates, and repeat implementation/convergence if tasks remain. Do not create a feature specification merely to document the entire existing application.

## Governance

The root [`CONSTITUTION.md`](../../CONSTITUTION.md) is the project-wide source of truth. This document operationalizes it for Spec Kit and must not weaken its requirements. Proposed policy changes require explicit agreement and synchronized updates to both constitutions. Feature-level specifications may add constraints but cannot override either constitution or backend authorization.
