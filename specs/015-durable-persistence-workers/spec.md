# Feature Specification — SPEC-015: Persistência SQL Server e workers resilientes

**Feature Branch**: `spec/015-durable-persistence-workers` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W1–W3 / P0
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 006C, 006B Alembic opt-in; 014 para acessos corporativos antes de produção

## User Scenarios & Testing

### User Story 1 — Despachar sob concorrência multi-instância (Priority: P1)

Como **operador e supervisor**, quero ter distribuição consistente mesmo com dois workers.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dadas ofertas concorrentes à mesma capacidade, quando dois processos competem, então não há dupla reserva.
2. Dada falha de worker após persistência, quando o segundo assume, então não cria oferta duplicada.

### User Story 2 — Restaurar dados e mensagens (Priority: P2)

Como **responsável SRE**, quero reconstruir estado consistente a partir de backup verificado.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado banco de teste restaurado, quando executar recuperação, então sessões, outbox e journal permanecem consistentes.
2. Dada migration interrompida, quando tentar iniciar, então o sistema impede escrita com schema incompatível.

### Edge Cases

- Deadlock, lock timeout e worker crash em commit.
- Mismatch de versões da API e do esquema.
- Failover e replay de mensagem depois de ACK externo.

## Requirements

### Functional Requirements

- **FR-001**: Modelar SQL Server com constraints, índice, níveis de isolamento e locking nativos equivalentes aos invariantes SQLite, sem transpor BEGIN IMMEDIATE..
- **FR-002**: Manter migrations versionadas com pré-check, backup verificável, rollback não destrutivo e proibição de alteração automática de bases existentes..
- **FR-003**: Implementar workers externos com lease/claim concorrente, idempotência, retry/backoff, outbox e DLQ transacionais..
- **FR-004**: Comprovar reconciliação, failover, backup/restore, observabilidade, índices e desempenho sob volume-alvo medido..
- **FR-005**: Evitar transações distribuídas implícitas, perda silenciosa de evento e uso de memória como fonte de verdade..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- MigrationState, BackupManifest, DataIntegrityCheckpoint.
- WorkerLease, OutboxDelivery, DispatchConcurrencyLock.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 reservas duplicadas em ensaio multi-worker concorrente.
- **SC-002**: 0 mensagens perdidas no ensaio de crash/recovery.
- **SC-003**: 100% dos restores críticos com checksums e integridade verificados.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- Migrar o arquivo original data/handoff-poc.db.
- Múltiplos serviços prematuros fora dos boundaries aprovados.

## Assumptions

- Personas: engenharia backend, DBA, operação SRE.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
