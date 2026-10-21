# Tasks — SPEC-018: Plano aprovado nas decisões Q1/Q2

**Status:** PLANNING_READY / Q1_Q2_APPROVED / IMPLEMENTATION_BLOCKED_ON_SECURITY_BASELINE
**Branch:** spec/018-approved-plan-20261021
**Método:** três blocos U1/U2/U3 (não 23 PRs). IDs mantidos para rastreabilidade.

## Governança e pré-requisitos
- [ ] T001 / BLOCK — reconciliar git diff da worktree Windows local spec/018-premium-workspace-ux; jamais sobrescrever arquivos não commitados.
- [x] T002 / PO — desktop 1366×768 / 1920×1080 @100/200% bloqueantes SPEC-018; mobile 390×844 exploratório nesta feature, mas bloqueante na SPEC-006C UX-08.
- [x] T003 / PO — Monitoria, role MONITOR e grants na SPEC-010, não nesta feature.
- [ ] T004 / BLOCK — revisão formal de Segurança/Arquitetura da preservação RBAC, stale responses, autenticação, estados e rolagem.
- [ ] T005 / BLOCK — congelar SHA de implementação funcional (avaliar PR #59 e incidente #58), mantendo sua branch independente do planejamento e da RC.

## U1 — Foundations, componentes e baseline (um PR)
- [ ] T006 — inventariar App, Mesa, Supervisão, Admin, Auditor, DemoLab, CSS e estados; classificar impacto e prioridade.
- [ ] T007 — definir tokens leves (superfície, texto, borda, foco, espaçamento, radius, cores de estado), fallback e contraste.
- [ ] T008 — padronizar controles, regiões/tabelas focáveis, alertas, diálogos e estados sem alterar rotas/roles.
- [ ] T009 — testes estáticos frontend/semântica + captura visual de baseline e regressão 1366/1920 @100/200%.
- [ ] T010 / GATE-U1 — revisão UX, A11y e Segurança + gates locais por SHA + decisão de continuar.

## U2 — Jornadas críticas (um PR)
- [ ] T011 — oferta/modal/scroll/foco em 200% para mouse, Tab, Enter; nota interna separada.
- [ ] T012 — composer, feedback e transferência N1→N2 sem sobreposição/retry de mutação.
- [ ] T013 — supervisão/auditoria: loading/error/empty/revoked e invalidação de fetch stale.
- [ ] T014 — Admin: tabelas e confirmação lifecycle CAS acessíveis e revalidadas.
- [ ] T015 — regressão QA N1→N2, permissions/grants, 401/403/404/409, timeout e mouse/teclado.
- [ ] T016 / GATE-U2 — regressão completa funcional e visual, nenhuma ampliação RBAC ou alteração schema.

## U3 — Certificação e aceite (um PR/evidência)
- [ ] T017 — UX18-01..08 nos quatro pares desktop/zoom real, rastreio por SHA/persona/browser.
- [ ] T018 — 390×844 exploratório SPEC-018 e UX-08 obrigatório release SPEC-006C em trilha separada.
- [ ] T019 — WCAG 2.2 AA aplicável (foco, teclado, nome, contraste, redução de movimento, click).
- [ ] T020 — start.cmd --check local: Pytest/Ruff/frontend architecture/TypeScript/Vite e revisão de segredos.
- [ ] T021 — Spec Kit local /speckit-analyze e matriz cobertura FR↔UX↔test por SHA.
- [ ] T022 / BLOCK — G09 independente, cobertura do PR #59 liveness e riscos residuais.
- [ ] T023 / BLOCK — G10 aceite formal por SHA e decisão de merge separada de produção.

## Matriz de rastreabilidade

| FR | Tarefas | Cenários |
|---|---|---|
| FR-001 | T006–T010 | UX18-01,06,08 |
| FR-002 | T002–T005, T009, T013 | UX18-04,05,08 |
| FR-003 | T009, T011, T014, T017–T019 | UX18-01,02,06,08 e SPEC-006C UX-08 à parte |
| FR-004 | T013, T015, T020 | UX18-04,05,08 |
| FR-005 | T006, T009, T017–T022 | UX18-01..08 |
| FR-006 | T012, T014–T016, T020 | UX18-03,07 |
| FR-007 | T011–T020 | UX18-01..08 |

**Estados:** somente T002/T003 completos como decisões de produto; planejamento versionado e inventário estático não contam como implementação entregue. Nenhum teste Windows ou validação mobile foi executado por esta branch.
