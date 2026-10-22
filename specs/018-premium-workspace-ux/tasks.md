# Tasks — SPEC-018: Plano aprovado nas decisões Q1/Q2

**Status:** U2_FUNCTIONAL_QA_PASS_WORKTREE / Q1_Q2_APPROVED / T004_T005_PENDING / NOT_ACCEPTED
**Branch:** feat/spec018-u2-operational-journeys-20261022 (base U1 `4ad1ffed1e5202698009777135f5bd55d224a32b`)
**Método:** três blocos U1/U2/U3 (não 23 PRs). IDs mantidos para rastreabilidade.

## Governança e pré-requisitos
- [x] T001 — diff da worktree Windows local conferido e preservado; decisões Q1/Q2 reconciliadas sem sobrescrever aquela worktree.
- [x] T002 / PO — desktop 1366×768 / 1920×1080 @100/200% bloqueantes SPEC-018; mobile 390×844 exploratório nesta feature, mas bloqueante na SPEC-006C UX-08.
- [x] T003 / PO — Monitoria, role MONITOR e grants na SPEC-010, não nesta feature.
- [ ] T004 / BLOCK — revisão formal de Segurança/Arquitetura da preservação RBAC, stale responses, autenticação, estados e rolagem.
- [ ] T005 / BLOCK — congelar SHA de implementação funcional (avaliar PR #59 e incidente #58), mantendo sua branch independente do planejamento e da RC.

## U1 — Foundations, componentes e baseline (um PR)
- [ ] T006 — inventariar App, Mesa, Supervisão, Admin, Auditor, DemoLab, CSS e estados; classificar impacto e prioridade.
- [x] T007 — tokens leves implementados e cobertos pelos contratos U1.
- [x] T008 — controles, foco, estados compartilhados e estilos U1 implementados sem mudar rotas/roles.
- [ ] T009 — testes estáticos frontend/semântica + captura visual de baseline e regressão 1366/1920 @100/200%.
- [ ] T010 / GATE-U1 — revisão UX, A11y e Segurança + gates locais por SHA + decisão de continuar.

## U2 — Jornadas críticas (um PR)
- [x] T011 — foco confinado no modal de oferta, retorno de foco e nota interna segregada; execução visual 200% fica no gate T015/T016.
- [x] T012 — composer e mutações single-flight, sem retry de POST, estado de reconciliação explícito e limpeza do detalhe anterior durante troca/falha de conversa.
- [x] T013 — estados de carregamento/erro/vazio/revogação e descarte de respostas/dados protegidos obsoletos.
- [x] T014 — confirmação lifecycle CAS com single-flight e mensagem segura para resultado não confirmado.
- [x] T015 — QA sintético N1→N2, grants/revoke/restore, 401/403/404/409/timeout e mouse/teclado executados; o 409 e timeouts de UI foram fault-injected, e os 404/auditoria foram verificados pelo cenário sintético.
- [x] T016 / GATE-U2 — regressão funcional e visual desktop passou nesta worktree; sem ampliação RBAC ou alteração schema. Repetir no SHA U2 imutável após commit.

## U3 — Certificação e aceite (um PR/evidência)
- [ ] T017 — UX18-01..08 nos quatro pares desktop/zoom real, rastreio por SHA/persona/browser.
- [ ] T018 — exploração 390×844 da SPEC-018: formulário Admin empilhado/visível após ajuste U2; completar matriz mobile e UX-08 da SPEC-006C em trilha de release separada.
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

**Estado atual:** T015/T016 passaram na worktree local após QA automatizado e browser em TEMP; T004/T005, T009/T010, T017–T023 e UX-08 mobile da SPEC-006C continuam pendentes. Não existe SHA de commit U2 para fixar esta evidência.
