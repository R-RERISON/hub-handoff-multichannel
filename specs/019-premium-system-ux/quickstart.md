# Quickstart — Premium UX Across Handoff Hub

## Prerequisites

- Windows checkout on `feat/spec018-ux-premium-batch-20261022`.
- Baseline: published U2 evidence commit `641ea2fc3c77c7f365f36f8af939f7e404a44c84`.
- Python and Node dependencies prepared by the repository launcher.
- Integrated browser available in VS Code.
- Do not use `data/handoff-poc.db`, `data/demo-credentials.txt`, or the normal POC startup for synthetic role verification.

## Automated validation

From the repository root:

```powershell
Remove-Item Env:HANDOFF_DB_URL -ErrorAction SilentlyContinue
.\start.cmd --check
```

Expected: Pytest, Ruff, frontend architecture contracts, TypeScript, and Vite build all exit successfully.

## Synthetic browser validation

1. Create and start a fresh disposable lab in TEMP. The launcher creates a unique `handoff-qa-006b4-*` directory and prints its path; do not pass `--lab-dir` when creating a new lab:

   ```powershell
   .\start.cmd --lab --no-browser
   ```

2. Save the exact generated directory path from the launcher as `$lab`. Use `.\start.cmd --lab --lab-dir $lab --no-browser` only to resume that existing lab.
3. If lifecycle UI is needed, stop the services and explicitly upgrade only that synthetic lab with a verified backup:

   ```powershell
   .\.venv\Scripts\python.exe -m handoff_hub.schema_admin --database (Join-Path $lab "synthetic.db") --backup-dir (Join-Path $lab "schema-backups") upgrade-lifecycle --confirm-offline
   .\.venv\Scripts\python.exe -m handoff_hub.schema_admin --database (Join-Path $lab "synthetic.db") inspect
   .\start.cmd --lab --lab-dir $lab --no-browser
   ```

4. Use only the synthetic identities and data created in that TEMP lab. Never paste credentials into chat, screenshots, committed files, or logs.
5. In the integrated browser, validate login and role-appropriate navigation; do not assume hidden navigation is authorization.
6. Exercise operator offer guidance, conversation selection/tabs, authorization denial, uncertain message outcomes, and no-retry behavior.
7. Exercise queue loading/empty/error/403/stale cases; membership, presence, and capacity confirmation; admin lifecycle confirmation and conflict handling.
8. Inspect every route at 1366×768 and 1920×1080 at 100% and 200% zoom, then 390×844. Verify keyboard focus, visible labels, table relationships, color contrast, and no clipped essential actions or unintended horizontal document scrolling.
9. Record sanitized results by code SHA, role, route, state, viewport, zoom, input method, and browser. Do not mark the separate SPEC-006C UX-08, G09, or G10 gates accepted by implication.
10. Stop the local launcher after validation. Remove only the named TEMP lab if cleanup is authorized; never point the launcher at the original POC database.

## Route and role inventory

| Route / mode | Operator | Supervisor | Admin | Auditor | Primary task |
|---|---:|---:|---:|---:|---|
| `/` login | Yes | Yes | Yes | Yes | Authenticate using the local synthetic identity. |
| `/inicio` space selection | No | No | Yes | No | Select one of the administrator's available workspaces. |
| `/operador` | Yes | No | No | No | Accept offers and handle the authenticated operator's conversations. |
| `/supervisao` | No | Yes | Yes | Yes | Review operation overview and local POC capabilities. |
| `/supervisao/conversas` | No | Yes | Yes | Yes | Read current conversations; Supervisor/Auditor also have the scoped verified-history mode. |
| `/supervisao/filas` | No | Yes | Yes | No | Review queue rotation and manage queue memberships. |
| `/supervisao/equipe` | No | Yes | Yes | No | Review and update team presence/capacity. |
| `/administracao` | No | No | Yes | No | Inspect the admin inventory and perform the supported queue lifecycle. |
| `/laboratorio` | No | Yes | Yes | No | Create synthetic requests for local validation. |

This is a frontend navigation inventory, not an authorization grant. The API remains the authorization authority; direct navigation is validated separately for each synthetic role.

## Evidence expected

- Exact tested code SHA and exit status of `start.cmd --check`.
- Browser matrix with route/persona/state/viewport/zoom/input and observed result.
- Sanitized screenshots only where they contain no credentials, tokens, personal content, or sensitive IDs.
- Any unverified scenario listed as pending, not as PASS.
