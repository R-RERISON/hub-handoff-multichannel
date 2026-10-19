# Tasks — SPEC-007: Administração de operações, filas, pessoas e permissões

**State**: IN_PROGRESS / B0.1 Windows QA PASS; B0.1 diff review sem findings; B1 e integração pendentes. IDs T001–T010.
**Dependencies**: 006C para desenvolvimento integrado; SPEC-006A/006B para grants e esquema; SPEC-018 para UX

## Phase 1 — Design and verification

- [ ] T001 Confirmar baseline do PR #28, Constituição e dependências anteriores; registrar SHA.
- [ ] T002 Executar `/speckit-clarify` quando houver ambiguidade material e validar FR/SC com o stakeholder.
- [ ] T003 Revisar contrato de dados, endpoints, riscos e ameaças; adicionar ADR, se necessário.
- [ ] T004 Executar `/speckit-analyze` para cobertura FR/SC, autorização, concorrência, rollback.

## Phase 2 — Incremental delivery

- [ ] T005 A Cadastro de operações/filas, estados e políticas mínimas; usar dados sintéticos, verificar autorização e revisar testes.
  - [x] T005-A0 API GET administrativa somente leitura e painel de inventário (código versionado; sem claim de teste executado).
  - [x] T005-A0-QA Executar testes de escopo/RBAC e `start.cmd --check` no SHA A0 (evidência da rodada registrada).
  - [x] T005-A1.1 Criar fila ADMIN-only vinculada à operação, com journal transacional e formulário desktop (código/testes versionados, não homologados).
  - [x] T005-A1.1-QA Executar testes Windows e revisar segurança/UX no SHA 8fd9294.
  - [x] T005-A1.2 Código de estados, migration opt-in 007a2, guardas e UI desktop versionados.
  - [x] T005-A1.2-QA Rodar start.cmd --check em Windows, migration TEMP, RBAC/CAS/dispatcher/transfer, visual desktop (código 6503d30; evidência em setup-one-command.md).
  - [ ] T005-A1.2-SEC Revisar SQLite concurrency, journal, rollback e autorização.
- [ ] T006 B Pessoas, perfis, memberships e grants separados; usar dados sintéticos, verificar autorização e revisar testes.
  - [x] T006-B0 Código de revalidação de role/operation em transação para membership, capacidade e presença; testes negativos sintéticos escritos.
  - [x] T006-B0-QA Executar start.cmd --check, testes cross-operation/legítimos e revisão independente do diff no Windows (código 49a28ad; 170 passed, 1 skipped; 8 testes B0.1; sem findings no escopo revisado).
  - [ ] T006-B1 Inventário de pessoas/operadores e memberships por fila, API/UI administrativa separada dos grants.
  - [ ] T006-B2 Fluxo auditado de concessão/revogação de grants com controle de versão e revogação comprovada.
- [ ] T007 C Revisão de alterações, auditoria, UX, rollback e documentação; usar dados sintéticos, verificar autorização e revisar testes.

## Phase 3 — Gates and closure

- [ ] T008 Executar testes negativos e de concorrência (se aplicável) e provar invariantes do banco original.
- [ ] T009 Executar `start.cmd --check` no Windows, documentar QA visual aplicável, artefatos, problemas e SHA.
- [ ] T010 Executar `/speckit-converge`, revisar rollback e colher decisão formal no PR pequeno antes de integrar.

## Progress convention

Marcar caixa **somente após evidência objetiva** (link do commit, teste, captura sintética, PR). Manter `NOT_STARTED → IN_PROGRESS → BLOCKED / IN_REVIEW → ACCEPTED` no registro de programa. `ACCEPTED` não significa `PRODUCTION_READY`.
