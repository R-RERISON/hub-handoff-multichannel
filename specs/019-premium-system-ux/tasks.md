# Tasks: Premium UX Across Handoff Hub

**Input**: Design documents from `specs/019-premium-system-ux/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/ui-behavior.md`, `quickstart.md`

**Tests**: Requested by the user. Add regression contracts before implementation and confirm behavior in the integrated browser.

## Format

Every task uses `- [x] Tnnn [P?] [USn?] Description with exact repository paths`.

## Phase 1: Setup

**Purpose**: Prepare a traceable, role-safe UX validation baseline.

- [x] T001 Capture the U2 parent SHA, all current frontend routes, and role access matrix in `specs/019-premium-system-ux/quickstart.md` without reading local credentials or POC data.
- [x] T002 Define the baseline route/state/viewport evidence table in `docs/qa/SPEC-019-PREMIUM-SYSTEM-UX.md` with all current screens and no assumed PASS results.

## Phase 2: Foundational

**Purpose**: Establish shared presentation vocabulary and accessible semantic tokens before workspace-specific changes.

- [x] T003 [P] Add tests for shared Portuguese status/error labels, WCAG contrast pairs, and visible focus tokens in `web/scripts/foundations.test.mjs`.
- [x] T004 Create shared `queueStateLabel`, `presenceLabel`, `roleLabel`, `eventLabel`, safe user-facing error mapping, and accessible `ConfirmDialog` in `web/src/design-system/presentation.ts` and `web/src/design-system/ConfirmDialog.tsx`, preserving API status codes as non-user-facing data.
- [x] T005 Extend semantic text, status, focus, border, and control tokens in `web/src/design-system/foundations.css`; ensure text and state colors meet the specified contrast thresholds.

## Phase 3: User Story 1 - Safe, accessible workspace navigation (Priority: P1)

**Goal**: Make login, route navigation, and authorization changes understandable and accessible without changing role permissions.

**Independent Test**: Sign in as each synthetic role; verify route and accessible navigation names at compact width; trigger session expiry/denial while protected data is present and confirm it is cleared.

### Tests for User Story 1

- [x] T006 [P] [US1] Add architecture contracts for semantic login submission, main landmarks, accessible compact navigation labels, conditional navigation groups, and unchanged route-role boundaries in `web/scripts/workspaces.test.mjs`.

### Implementation for User Story 1

- [x] T007 [US1] Convert login to a semantic form with one submit path, accessible loading/error feedback, and main landmarks in `web/src/App.tsx`.
- [x] T008 [US1] Add persistent accessible names and destinations to compact navigation links and render group headings only when the role has a link in `web/src/App.tsx` and `web/src/styles.css`.
- [x] T009 [US1] Apply the main landmark and consistent page focus behavior to role-appropriate space selection and access-denied screens in `web/src/workspaces/WorkspaceHome.tsx` and `web/src/App.tsx`.

## Phase 4: User Story 2 - Truthful operator conversation states (Priority: P1)

**Goal**: Prevent protected or stale conversation content from remaining available after access loss and make transfer guidance and panel selection explicit.

**Independent Test**: In a synthetic lab, open a conversation, inject a 403/404 and a transient failure into the next poll, load transfer guidance slowly/fail it, and use the mobile panel controls by keyboard.

### Tests for User Story 2

- [x] T010 [P] [US2] Add regression contracts for denied versus transient operator polling, protected-data cleanup, transfer-guidance loading/error/empty states, selected-panel semantics, and safe no-retry behavior in `web/scripts/workspaces.test.mjs`.

### Implementation for User Story 2

- [x] T011 [US2] Distinguish 401/403/404 from transient message-poll failures; clear protected conversation content and actions on denial and mark transiently retained data stale with dependent mutations disabled in `web/src/OperatorDesk.tsx`.
- [x] T012 [US2] Represent transfer-note lookup as loading, available, unavailable, or empty and announce it before an offer decision without inserting it into the user transcript in `web/src/OperatorDesk.tsx`.
- [x] T013 [US2] Expose mobile work/conversation tab selection, selected session, and operator presence labels programmatically and in Portuguese in `web/src/OperatorDesk.tsx`.

## Phase 5: User Story 3 - Safe supervision and queue/team controls (Priority: P1)

**Goal**: Distinguish queue/team loading, empty, denied, error, and stale states; make routing mutations deliberate and team data understandable as a table.

**Independent Test**: Delay and deny rotation data, change scope during pending requests, cancel and confirm membership/presence/capacity changes, and verify announcements and final state.

### Tests for User Story 3

- [x] T014 [P] [US3] Add regression contracts for queue load/deny/stale states, membership confirmation and cancellation, native team table semantics, and presence/capacity confirmation in `web/scripts/workspaces.test.mjs`.

### Implementation for User Story 3

- [x] T015 [US3] Add request-generation guards and distinct loading/ready/empty/stale/error/denied states to queue rotation; clear protected rotation on denial and block changes until revalidated in `web/src/workspaces/SupervisorQueues.tsx`.
- [x] T016 [US3] Require an accessible target-specific confirmation for queue membership changes and announce success, rejection, and uncertain results in `web/src/workspaces/SupervisorQueues.tsx`.
- [x] T017 [US3] Replace the div-based team grid with a semantic table and row-preserving responsive labels in `web/src/workspaces/SupervisorTeam.tsx` and `web/src/styles.css`.
- [x] T018 [US3] Stage presence/capacity selections locally and apply them only after explicit confirmation; provide cancel, focus placement, and accessible outcomes in `web/src/workspaces/SupervisorTeam.tsx` and `web/src/App.tsx`.

## Phase 6: User Story 4 - Understandable administration and lifecycle confirmation (Priority: P2)

**Goal**: Make lifecycle confirmation focusable and clear, and make queue/person table status values understandable.

**Independent Test**: In the synthetic lab, confirm and cancel lifecycle changes by keyboard, inject a version conflict, and inspect administration tables at 200% and 390×844.

### Tests for User Story 4

- [x] T019 [P] [US4] Add regression contracts for lifecycle confirmation focus/target announcement, no mutation on cancel, translated lifecycle/presence/role labels, and one-request CAS behavior in `web/scripts/workspaces.test.mjs`.

### Implementation for User Story 4

- [x] T020 [US4] Move focus into lifecycle confirmation, announce the queue and consequence, preserve cancel/confirm single-flight behavior, use localized state labels, and refresh the supervisor snapshot after a confirmed change in `web/src/workspaces/AdminLanding.tsx` and `web/src/App.tsx`.
- [x] T021 [US4] Localize presence, role, and account-state values in operator and administration people tables in `web/src/workspaces/AdminPeople.tsx` and `web/src/design-system/presentation.ts`.

## Phase 7: User Story 5 - Coherent premium UX across all workspaces (Priority: P2)

**Goal**: Apply consistent Portuguese status/error language, truthful operational health, focus/contrast, and responsive visual hierarchy to all routes.

**Independent Test**: Inspect every route in the role matrix at desktop, zoomed, and mobile viewports; verify common statuses, focus, table relationships, empty/error feedback, and no unsupported integration claims.

### Tests for User Story 5

- [x] T022 [P] [US5] Add contracts for localized statuses and errors, truthful POC health wording, shared visual-state tokens, and contrast calculations across all semantic states in `web/scripts/foundations.test.mjs` and `web/scripts/workspaces.test.mjs`.

### Implementation for User Story 5

- [x] T023 [US5] Use common Portuguese session/queue/presence labels in conversations, overview, operator, queues, team, and verified-history screens in `web/src/workspaces/SupervisorConversations.tsx`, `web/src/workspaces/SupervisorOverview.tsx`, `web/src/workspaces/ScopedVerifiedHistory.tsx`, `web/src/workspaces/SupervisorQueues.tsx`, `web/src/workspaces/SupervisorTeam.tsx`, and `web/src/OperatorDesk.tsx`.
- [x] T024 [US5] Replace static service-health claims and inaccurate bot-integration copy with explicit local-POC and unmonitored-state wording in `web/src/workspaces/SupervisorOverview.tsx` and `web/src/workspaces/WorkspaceHome.tsx`.
- [x] T025 [US5] Apply consistent text, status, focus, selected, disabled, form, table, and confirmation styles without changing existing workspace shells or scroll contracts in `web/src/styles.css` and `web/src/design-system/foundations.css`.

## Phase 8: Polish & Cross-Cutting Validation

**Purpose**: Close documentation, automated tests, browser evidence, and exact-SHA reporting.

- [x] T026 [P] Update `docs/setup-one-command.md` with the new branch, synthetic-lab-only browser workflow, local commands, and explicit pending release gates.
- [x] T027 Run targeted frontend architecture/foundation tests and verify regression assertions fail before implementation and pass after it in `web/scripts/workspaces.test.mjs` and `web/scripts/foundations.test.mjs`.
- [x] T028 Run `.\start.cmd --check` with `HANDOFF_DB_URL` removed and record actual test/build results in `docs/qa/SPEC-019-PREMIUM-SYSTEM-UX.md`.
- [x] T029 Validate login and every role-authorized route in the integrated browser using a disposable TEMP lab; cover delayed, empty, error, denied, stale, confirmation, and no-retry states without capturing credentials.
- [x] T030 Validate 1366×768 and 1920×1080 at 100% and 200%, plus 390×844, for all routes; verify keyboard focus, accessible names, table headers, contrast, essential actions, and document overflow in the integrated browser.
- [x] T031 Record only verified SHA/persona/route/state/viewport/zoom/input/browser evidence and unresolved items in `docs/qa/SPEC-019-PREMIUM-SYSTEM-UX.md` and `docs/setup-one-command.md`; keep UX-08, G09, and G10 gates distinct.
- [x] T032 Run `git diff --check`, review only the changed UX/spec paths, and preserve the unrelated untracked `.github/agents/premium-ux-reviewer.agent.md` without staging or modifying it.

## Dependencies & Execution Order

### Phase Dependencies

- Setup Phase 1 precedes shared foundations.
- Foundational Phase 2 precedes all user stories because all use shared labels, errors, tokens, and focus states.
- User Stories 1-3 are priority P1 and depend only on Phase 2; they share helpers but touch distinct primary workspace modules.
- User Story 4 depends on the shared presentation helpers and can follow the P1 journeys.
- User Story 5 follows route-level changes so cross-workspace contracts cover the final states.
- Polish/validation depends on all implementation stories.

### User Story Dependencies

- **US1 (P1)**: Depends on the foundational presentation/error helpers; no dependency on other stories.
- **US2 (P1)**: Depends on shared errors/labels and denial semantics; no dependency on US1 screen implementation.
- **US3 (P1)**: Depends on shared errors/labels and focus tokens; no dependency on US2.
- **US4 (P2)**: Depends on shared labels and focus tokens; no dependency on US3.
- **US5 (P2)**: Integrates common labels and styles after US1-US4 but remains independently verifiable across all screens.

### Parallel Opportunities

- T003 and the setup evidence inventory T002 can be prepared independently.
- In each user story, the contract-test task can be written before its component changes.
- After T004/T005, US1, US2, US3, and US4 touch mostly separate files and can be developed independently, but integrate only after checking overlapping `App.tsx`, `presentation.ts`, and CSS edits.
- T026 documentation can proceed alongside code validation once the branch and test commands are fixed.

### Parallel Execution Examples

```text
Task: T006 [US1] navigation/login regression contract
Task: T010 [US2] operator stale/offer state contract
Task: T014 [US3] queue/team mutation contract
```

These tests may be drafted in parallel, but their implementation phases must use shared helpers from Phase 2.

## Implementation Strategy

### MVP First

Complete Phase 1 and Phase 2, then US1 (safe, accessible route and authorization feedback). Validate it in the browser before proceeding.

### Incremental Delivery

1. Finish shared semantic labels, errors, tokens, and tests.
2. Deliver and validate the P1 navigation, operator, and supervision journeys.
3. Deliver P2 administration confirmations and common system-wide status/health language.
4. Finish the full matrix, local launcher gate, and integrated-browser evidence.

### Release Boundaries

This branch and local POC evidence do not constitute production readiness, G09 independent review, G10 human acceptance, or approval of the separate SPEC-006C UX-08 release gate.

## Notes

- Every task is checkbox-formatted, sequentially identified, story-tagged in story phases, and includes exact repository paths.
- Tests and browser validation are explicitly requested; their tasks are therefore required.
- No task may touch `data/handoff-poc.db`, `data/demo-credentials.txt`, production secrets, or real user content.

## Phase 9: Convergence

- [x] T033 [US4] Preserve a meaningful keyboard focus target after lifecycle conflict or timeout reconciliation; add a regression contract in `web/scripts/workspaces.test.mjs` and browser evidence in `docs/qa/SPEC-019-PREMIUM-SYSTEM-UX.md` per SC-004 and US4/AC2 (partial).
- [x] T034 Complete keyboard-only primary-task validation for every in-scope role and route; record verified input methods, defects, and remaining gaps in `docs/qa/SPEC-019-PREMIUM-SYSTEM-UX.md` and `docs/setup-one-command.md` per SC-004, SC-013, and T030 (partial).
- [x] T035 [US5] Extend contrast contracts and browser verification to all applicable text and non-text indicators in normal, focused, selected, disabled, hover, and error states; document coverage and exclusions in `web/scripts/foundations.test.mjs` and `docs/qa/SPEC-019-PREMIUM-SYSTEM-UX.md` per FR-011, SC-003, and T030 (partial).
