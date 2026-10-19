# Tasks — SPEC-012: Adapter Teams Embedded e mensageria E2E

**State**: NOT_STARTED. Roteiro inicial a revisar por `/speckit-tasks` na execução.

## Phase 1 — Specify / Plan / Analyze
- [ ] T001 Conferir Constituição, baseline 006C, dependências e registrar SHA da branch.
- [ ] T002 Refinar escopo, cenários de aceite, contratos, modelos de autorização e ameaças.
- [ ] T003 `/speckit-clarify` para ambiguidades materiais; `/speckit-plan` para arquitetura detalhada.
- [ ] T004 `/speckit-analyze` para consistência FR ↔ SC ↔ testes ↔ rollback; obter design review.

## Phase 2 — Independent vertical slices
- [ ] T005 E.1 Contrato canonical inbound/outbound e fake adapter testado; escrever testes e evidência sintética antes de concluir.
- [ ] T006 E.2 Adapter Tornado/Teams Embedded e feature flag de canário; escrever testes e evidência sintética antes de concluir.
- [ ] T007 E.3 Retry/ACK/DLQ, falhas E2E e rollback auditado; escrever testes e evidência sintética antes de concluir.

## Phase 3 — QA / Convergence
- [ ] T008 Garantir não regressão de RBAC, concorrência, isolamento histórico e N1→N2.
- [ ] T009 Executar `start.cmd --check` e QA manual aplicável; registrar resultados reais e SHA no PR.
- [ ] T010 `/speckit-converge`, rollback documentado, aprovação de aceitação do incremento; sem merge automático.

**Tracking rule:** só marcar [x] se existir evidência; estado NOT_STARTED / IN_PROGRESS / BLOCKED / REVIEW / ACCEPTED é diferente de PROD_READY.
