# Research — Premium UX Across Handoff Hub

## Decision 1: Keep the improvement frontend-only

- **Decision**: Use the current route shells, React components, CSS foundations, and local browser validation. Do not change backend endpoints, role grants, database state, migrations, or channel integrations.
- **Rationale**: The audit findings concern presentation, interaction feedback, accessibility semantics, stale client state, and truthful copy. Existing backend responses already provide the authorization and version results the UI needs to interpret.
- **Alternatives considered**: Adding new backend UX endpoints or replacing the app shell. Rejected because neither is required to address the findings and both broaden security and regression scope.

## Decision 2: Preserve U1 foundations and add semantic presentation helpers

- **Decision**: Extend `web/src/design-system/foundations.css` and add one small shared TypeScript presentation module for Portuguese labels and safe error messages.
- **Rationale**: `main.tsx` already loads the foundations after `styles.css`; U1 established semantic colors, spacing, focus, and reduced-motion behavior. A single label/error mapping prevents status drift without changing API wire values.
- **Alternatives considered**: Replacing all CSS or duplicating status strings in every workspace. Rejected due to regression risk and inconsistent behavior.

## Decision 3: Treat authorization loss differently from transient failure

- **Decision**: A 401/403/404 for protected content clears it and blocks dependent actions. A transport/5xx failure may retain previously authorized data only if it is visibly marked stale and mutations are disabled until reconciliation.
- **Rationale**: This satisfies fail-closed authorization while preserving operational context during a temporary network outage. Requests from a prior route, selection, or queue are discarded.
- **Alternatives considered**: Clear all content on every network error, or retain all content for every error. The former loses useful context unnecessarily; the latter risks exposing stale data after revocation.

## Decision 4: Confirm changes before sending supervisor/admin mutations

- **Decision**: Use a shared native modal confirmation with the target and impact, explicit Cancel/Confirm actions, managed focus, and one-request safeguards.
- **Rationale**: Queue membership, presence, capacity, and lifecycle affect routing. Existing code already uses explicit lifecycle confirmation and API CAS; the same interaction contract should cover supervisor mutations.
- **Alternatives considered**: Immediate mutations on select/click; inline confirmation groups; generic browser `confirm()`. Rejected because inline contexts can be overlooked, immediate mutations hide impact, and native modal confirmations provide consistent focus trapping and return behavior without new dependencies.

## Decision 5: Keep native semantic tables and accessible compact navigation

- **Decision**: Use native table semantics for team data and keep names available for icon-only navigation when labels are visually compacted.
- **Rationale**: The existing admin inventory already uses `caption`, `scope="col"`, and `scope="row"`; extending the same pattern supports screen-reader row/column relationships.
- **Alternatives considered**: ARIA grid roles on the existing div layout. Rejected because there is no need for spreadsheet-style keyboard interaction.

## Decision 6: Validate all existing routes in a synthetic environment

- **Decision**: Use a fresh TEMP lab and integrated Chromium browser for role-based journeys, desktop 1366×768 and 1920×1080, 100%/200% zoom, and 390×844 viewport. Record only sanitized outcomes.
- **Rationale**: Source contracts cannot prove actual focus order, clipping, overflow, responsive behavior, or role-restricted navigation. The existing launcher supports disposable labs without touching the original DB.
- **Alternatives considered**: Static source checks only or normal POC startup. Rejected because the user explicitly requested browser validation and the normal startup uses the original POC database.

## Decision 7: Keep local validation and no new browser/test dependencies

- **Decision**: Extend the existing Node architecture contracts and run `.\start.cmd --check`; use the integrated browser for runtime checks.
- **Rationale**: The repository already has local coverage for workspaces, route contracts, focus, contrast tokens, and no-retry behavior. The integrated browser is available and avoids introducing Playwright packages or CI.
- **Alternatives considered**: Add a new browser automation dependency or GitHub workflow. Rejected by simplicity and project governance.
