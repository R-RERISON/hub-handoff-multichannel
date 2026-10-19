# Tasks — SPEC-007: Administração de operações, filas, pessoas e permissões

**State**: IN_PROGRESS / A0 CODED — gates locais e aceite ainda pendentes. IDs T001–T010 e subfatia A0.
**Dependencies**: 006C para desenvolvimento integrado; SPEC-006A/006B para grants e esquema; SPEC-018 para UX

## Phase 1 — Design and verification

- [ ] T001 Confirmar baseline do PR #28, Constituição e dependências anteriores; registrar SHA.
- [ ] T002 Executar `/speckit-clarify` quando houver ambiguidade material e validar FR/SC com o stakeholder.
- [ ] T003 Revisar contrato de dados, endpoints, riscos e ameaças; adicionar ADR, se necessário.
- [ ] T004 Executar `/speckit-analyze` para cobertura FR/SC, autorização, concorrência, rollback.

## Phase 2 — Incremental delivery

- [ ] T005 A Cadastro de operações/filas, estados e políticas mínimas; usar dados sintéticos, verificar autorização e revisar testes.
  - [x] T005-A0 API GET administrativa somente leitura e painel de inventário (código versionado; sem claim de teste executado).
  - [ ] T005-A0-QA Executar testes de escopo/RBAC e `start.cmd --check` no SHA final Windows.
  - [x] T005-A1.1 Criar fila ADMIN-only vinculada à operação, com journal transacional e formulário desktop (código/testes versionados, não homologados).
  - [ ] T005-A1.1-QA Executar testes Windows e revisar segurança/UX no SHA da fatia.
  - [ ] T005-A1.2 Ativar/pausar/arquivar fila com schema versionado aditivo, proteção de intake/dispatcher e rollback.
- [ ] T006 B Pessoas, perfis, memberships e grants separados; usar dados sintéticos, verificar autorização e revisar testes.
- [ ] T007 C Revisão de alterações, auditoria, UX, rollback e documentação; usar dados sintéticos, verificar autorização e revisar testes.

## Phase 3 — Gates and closure

- [ ] T008 Executar testes negativos e de concorrência (se aplicável) e provar invariantes do banco original.
- [ ] T009 Executar `start.cmd --check` no Windows, documentar QA visual aplicável, artefatos, problemas e SHA.
- [ ] T010 Executar `/speckit-converge`, revisar rollback e colher decisão formal no PR pequeno antes de integrar.

## Progress convention

Marcar caixa **somente após evidência objetiva** (link do commit, teste, captura sintética, PR). Manter `NOT_STARTED → IN_PROGRESS → BLOCKED / IN_REVIEW → ACCEPTED` no registro de programa. `ACCEPTED` não significa `PRODUCTION_READY`.
