# Implementation Plan: Premium UX Across Handoff Hub

**Branch**: `feat/spec018-ux-premium-batch-20261022` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-premium-system-ux/spec.md`

## Summary

Improve the complete current frontend through one integrated, role-safe UX batch: clear protected-data/error states, accessible navigation and controls, safer confirmations, consistent Portuguese status language, semantic tables, contrast/focus coverage, and complete desktop/zoom/mobile validation. Keep this frontend-only; preserve backend RBAC, operator identity, route/shell boundaries, CAS/single-flight behavior, synthetic lab markings, and the no-real-Teams-delivery disclosure.

The design uses the current React/TypeScript/Vite application and design tokens, adds no runtime dependency, and builds on existing Node architecture contracts plus the full local launcher gate. Browser verification must use a disposable synthetic TEMP lab.

## Technical Context

**Language/Version**: TypeScript and React 19 in the frontend; Python/FastAPI runtime is unchanged.

**Primary Dependencies**: Existing React Router, Lucide icons, Vite, CSS design foundations, and Node built-in test runner. No new dependency.

**Storage**: No product data or schema change. Browser validation uses disposable synthetic SQLite lab data only.

**Testing**: Focused `node --test` architecture/foundation contracts; `.\start.cmd --check` for Pytest, Ruff, frontend architecture tests, TypeScript, and Vite; integrated-browser checks in `start.cmd --lab` with a TEMP lab.

**Target Platform**: Local Windows launcher and integrated Chromium-based browser; desktop, 200% zoom, and 390×844 mobile viewport.

**Project Type**: Existing React SPA with FastAPI backend and independent role-based workspace shells.

**Performance Goals**: No new network dependency or recurring poll; added status/confirmation UI must not add requests or introduce automatic retries.

**Constraints**: Frontend-only; backend authorization remains authoritative; no change to roles/routes, authentication semantics, database, schema, migrations, original POC DB, channel adapter, or production gates. All reports and browser evidence must be synthetic and sanitized.

**Scale/Scope**: Every current user-facing route: login/space selection, Operator, Supervision overview/conversations/queues/team, Administration, verified history, and Laboratory. Validate the available roles without granting any new access.

## Constitution Check

| Gate | Result | Evidence / constraint |
|---|---|---|
| Identity and backend authorization | PASS | No role, grant, token, or endpoint change; UI only explains backend results. |
| Operator identity and role boundaries | PASS | No identity simulation, cross-operator response, supervisor/admin takeover, or auditor write action. |
| Durable state and mutation safety | PASS | No persistence/schema work; preserve CAS and single-flight; no automatic retry after uncertain mutation. |
| Credentials and synthetic data | PASS | Use disposable TEMP lab only; never read or publish developer credentials, hashes, tokens, or original DB data. |
| Separate workspaces and keyboard reachability | PASS | Preserve current route/shell boundaries; essential actions remain keyboard reachable at viewport and zoom targets. |
| Local verification / no hosted CI | PASS | Use project launcher and local browser; do not add GitHub Actions. |
| POC/channel truthfulness | PASS | Keep simulated message and Teams-not-installed disclosures explicit. |

No constitution deviations are proposed.

## Design Decisions

1. **Incremental use of the current design system.** Keep `styles.css` followed by `design-system/foundations.css`; add semantic tokens and narrowly scoped rules without replacing the workspace shells or changing established scrolling contracts.
2. **Small shared presentation helpers.** Centralize Portuguese labels for queue/session/presence states and safe user-facing errors; leave wire values and backend contracts unchanged.
3. **Fail closed on authorization denial.** For 401/403/404, clear protected content and relevant selections. For transient failures, explicitly identify stale/unavailable data and block actions that depend on unconfirmed state.
4. **Intentional operational mutations.** Use a shared native confirmation dialog for supervisor membership/presence/capacity changes and admin lifecycle actions; cancellation performs no mutation, focus returns to the trigger, and success/error/conflict feedback is announced. Preserve one request per confirmation.
5. **Accessible table and compact-navigation semantics.** Use native table header/row associations for team data and accessible names for icon-only navigation; narrow layouts retain row labels and internal scrolling as needed.
6. **Evidence-first certification.** Add regression contracts for security-sensitive UI behavior and inspect the actual rendered application in the integrated browser at all requested roles, routes, zoom levels, and mobile viewport. Do not claim untested coverage.

## Project Structure

### Documentation (this feature)

```text
specs/019-premium-system-ux/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-behavior.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
web/
├── src/
│   ├── App.tsx
│   ├── OperatorDesk.tsx
│   ├── styles.css
│   ├── design-system/
│   │   ├── ConfirmDialog.tsx
│   │   ├── foundations.css
│   │   └── presentation.ts
│   └── workspaces/
│       ├── AdminLanding.tsx
│       ├── AdminPeople.tsx
│       ├── SupervisorConversations.tsx
│       ├── SupervisorOverview.tsx
│       ├── SupervisorQueues.tsx
│       ├── SupervisorTeam.tsx
│       └── WorkspaceHome.tsx
└── scripts/
    ├── foundations.test.mjs
    └── workspaces.test.mjs
```

**Structure Decision**: Extend existing frontend components and shared design-system utilities. Keep route coordination in `App.tsx` and workspace behavior in its existing component modules.

## Complexity Tracking

No constitution violations or new architectural layer are introduced.

## Rollback

Revert only the UX feature branch changes. No database or backend rollback is required. If content remains after a denial, a mutation is duplicated, a role gains a route, or an essential control is clipped, block release and revert/fix the affected frontend behavior before rerunning the local gate and browser checks.
