# Tasks — SPEC-009: Portal de auditoria e evidências por segmento

**State**: PLANNED; nenhuma tarefa abaixo foi executada nesta entrega. IDs locais T001–T010.
**Dependencies**: 006B-4.x/5.x, 007, 008 para controles de fila

## Phase 1 — Design and verification

- [ ] T001 Confirmar baseline do PR #28, Constituição e dependências anteriores; registrar SHA.
- [ ] T002 Executar `/speckit-clarify` quando houver ambiguidade material e validar FR/SC com o stakeholder.
- [ ] T003 Revisar contrato de dados, endpoints, riscos e ameaças; adicionar ADR, se necessário.
- [ ] T004 Executar `/speckit-analyze` para cobertura FR/SC, autorização, concorrência, rollback.

## Phase 2 — Incremental delivery

- [ ] T005 A Busca e experiência de auditor sob grants; usar dados sintéticos, verificar autorização e revisar testes.
- [ ] T006 B Evidências e exportação rastreável; usar dados sintéticos, verificar autorização e revisar testes.
- [ ] T007 C Casos cross-queue, retenção, segurança e testes de revalidação; usar dados sintéticos, verificar autorização e revisar testes.

## Phase 3 — Gates and closure

- [ ] T008 Executar testes negativos e de concorrência (se aplicável) e provar invariantes do banco original.
- [ ] T009 Executar `start.cmd --check` no Windows, documentar QA visual aplicável, artefatos, problemas e SHA.
- [ ] T010 Executar `/speckit-converge`, revisar rollback e colher decisão formal no PR pequeno antes de integrar.

## Progress convention

Marcar caixa **somente após evidência objetiva** (link do commit, teste, captura sintética, PR). Manter `NOT_STARTED → IN_PROGRESS → BLOCKED / IN_REVIEW → ACCEPTED` no registro de programa. `ACCEPTED` não significa `PRODUCTION_READY`.
