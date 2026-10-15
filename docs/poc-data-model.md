# Modelo de dados — POC SQLite / SPEC-002-P1

## Referências funcionais

Os scripts legados fornecidos descrevem fila por setor, status/operador, associação de conversas, envio Teams, anexos, ociosidade, transferência, Finesse e pesquisa de satisfação. São requisitos funcionais de referência **e não uma fonte de migração ou código para copiar**. O novo Hub cria tabelas, dados e regras próprias.

## Esquema implementado

| Tabela | Responsabilidade | Integridade |
|---|---|---|
| operations | Unidade lógica de atendimento | PK id |
| integrations | Bot/adapter de origem | FK operation_id |
| queues | Fila por operação | FK operation_id |
| operators | Pessoas/capacidade/presença | CHECK capacity >= 1 |
| queue_memberships | Operador autorizado em fila | PK composta |
| handoff_sessions | Sessão, operação, fila, conversa, operador | UNIQUE(integration_id, idempotency_key); índices |
| session_events | Registro de transições | FK session_id; índice |
| messages | Usuário e operador | UNIQUE(session_id,external_message_id); índice |
| outbox_events | Mensagem operador pendente de adapter | UNIQUE(message_id), FKs |

## Invariantes da POC

- SQLite local em um host com PRAGMA foreign_keys=ON, journal_mode=WAL, busy_timeout.
- Mutação de fila/despacho utiliza BEGIN IMMEDIATE: transação de escritor exclusivo em SQLite.
- Limite de capacidade confirmado durante a transação, sem reserva apenas em memória.
- Request duplicado com mesma integração e Idempotency-Key retorna o mesmo atendimento; conflito de payload retorna 409.
- Mensagens são deduplicadas por id externo na sessão.
- Resposta do operador **não é publicada no Teams**: registra evento PENDING_ADAPTER.
- Estados funcionais de POC: QUEUED -> ACTIVE -> CLOSED. Demais estados planejados não expostos nesta etapa.
- Operadores, usuários e integrações do seed são artificiais.

## Migração futura SQL Server

SQLAlchemy torna o modelo mais portável, mas não substitui revisão de isolamento, transações/locking, índices, restrições, parâmetros de conexão, timezone, JSON, performance e migrações versionadas. BEGIN IMMEDIATE não é portátil e será substituído por estratégia SQL Server. Alembic deverá ser introduzido antes de qualquer operação não descartável. Nunca migrar dados da operação legada para o Hub automaticamente.

## Fases de enriquecimento

Policies, skills, turnos, calendário, feriados, SLAs, transfers, ownership history, attachments/media, delivery_attempts, webhook_subscriptions, external_message_mapping, CSAT, operator_presence_events, tenant security, retention policies e relatórios gerenciais.
