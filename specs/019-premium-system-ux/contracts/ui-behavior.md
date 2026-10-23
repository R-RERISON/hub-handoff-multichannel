# UI Behavior Contract — Premium UX Across Handoff Hub

## Authorization and data freshness

- The backend remains the permission authority. Navigation, labels, tabs, or disabled controls do not grant access.
- A 401 returns the user to the login flow and removes the prior authenticated snapshot.
- A 403/404 for protected data removes the affected selection, transcript, internal notes, timeline, membership, or detail before showing the denied state.
- A transient transport/server failure may retain previously authorized data only when clearly marked stale; actions depending on it remain disabled until a successful refresh.
- Responses for a prior workspace, queue, session, or selection are ignored.

## Mutation behavior

- Risky operational actions show the target and consequence before confirmation.
- Canceling a confirmation sends no mutation.
- One explicit confirmation results in at most one API mutation; no retry occurs automatically after timeout, conflict, or uncertain response.
- Confirmed results, rejected results, and uncertain results use distinct accessible feedback. An uncertain result is never presented as confirmed success.
- Existing CAS, role checks, audit behavior, and authenticated operator identity are preserved.

## Accessibility and content

- Every interactive element and icon-only navigation link has an accessible name; state is programmatically conveyed and focus is visible.
- Dialog/panel focus is placed in the new context and restored to the initiating control when it closes.
- Team and administration tables use meaningful captions, column headers, and row headers; narrow layouts retain the relationship between each value and its label.
- Color is not the only carrier of status. Text contrast and relevant non-text indicators meet applicable WCAG 2.2 AA thresholds.
- Status and common error labels are in Portuguese and user-actionable. Technical payloads do not replace the primary error message.
- Simulated messages and local-only operations are never described as real Teams delivery or corporate identity.

## Layout

- Required viewports include 1366×768 and 1920×1080 at 100% and 200% browser zoom, plus 390×844.
- Essential actions remain reachable; content may use clearly labeled, keyboard-focusable internal scrolling when a table or transcript cannot fit.
- No unintended document-level horizontal overflow is introduced.

## Route inventory

The implementation inventory covers login/space selection, `/operador`, `/supervisao`, `/supervisao/conversas`, `/supervisao/filas`, `/supervisao/equipe`, `/administracao`, verified-history mode, and `/laboratorio`. Access continues to follow the existing role matrix; no route or role is added.
