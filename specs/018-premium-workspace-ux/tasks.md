# Tasks — SPEC-018: Design system premium, acessibilidade e experiência operacional

**State**: NOT_STARTED. Roteiro inicial a revisar por `/speckit-tasks` na execução.

## Phase 1 — Specify / Plan / Analyze
- [ ] T001 Conferir Constituição, baseline 006C, dependências e registrar SHA da branch.
- [ ] T002 Refinar escopo, cenários de aceite, contratos, modelos de autorização e ameaças.
- [ ] T003 `/speckit-clarify` para ambiguidades materiais; `/speckit-plan` para arquitetura detalhada.
- [ ] T004 `/speckit-analyze` para consistência FR ↔ SC ↔ testes ↔ rollback; obter design review.

## Phase 2 — Independent vertical slices
- [ ] T005 U.1 Inventariar gaps e aprovar tokens do design system; escrever testes e evidência sintética antes de concluir.
- [ ] T006 U.2 Componentes e UX de Operador/Supervisão sem regressão; escrever testes e evidência sintética antes de concluir.
- [ ] T007 U.3 Portais novos, a11y, responsividade e gates visuais; escrever testes e evidência sintética antes de concluir.

## Phase 3 — QA / Convergence
- [ ] T008 Garantir não regressão de RBAC, concorrência, isolamento histórico e N1→N2.
- [ ] T009 Executar `start.cmd --check` e QA manual aplicável; registrar resultados reais e SHA no PR.
- [ ] T010 `/speckit-converge`, rollback documentado, aprovação de aceitação do incremento; sem merge automático.

**Tracking rule:** só marcar [x] se existir evidência; estado NOT_STARTED / IN_PROGRESS / BLOCKED / REVIEW / ACCEPTED é diferente de PROD_READY.
