# Arquitetura atual — POC SQLite

## Contexto
Usuário simulado -> API FastAPI -> SQLite -> Workspace React.
Primeiro canal real futuro: Teams via bot original -> adapter Embedded -> Hub -> workspace operador -> outbox -> adapter do bot original.

## Limites do produto
- Hub é proprietário da sessão, fila, operador, mensagens e auditoria.
- Bot de origem é proprietário apenas do transporte de conversa no Teams e mantém sua identidade.
- Nunca reutilizar credentials/conversationId entre bots.
- Scripts Tornado existentes servem como **referência funcional** para requisitos; não são código de migração.

## Stack
- FastAPI, SQLAlchemy 2 e SQLite WAL para laboratório em máquina única.
- React, TypeScript e Vite para interface independente.
- Idempotency-Key, tabela messages, session_events e outbox.
- Testes locais, sem pipelines GitHub Actions.
- Futura avaliação SQL Server + Alembic; não implementados ainda.

## Implementação presente
- Operation / Integration / Queue / Operator / QueueMembership.
- HandoffSession / SessionEvent / Message / OutboxEvent.
- Distribuição manual com BEGIN IMMEDIATE, sem sobrealocação em concorrência de SQLite.
- Estados QUEUED -> ACTIVE -> CLOSED.
- Workspace e cockpit simulados, sem conexão Teams e sem identidade corporativa.

## Evoluções
1. Services e repositories isolados; Entra ID/OAuth/RBAC; multioperação.
2. Alembic e regras completas de transferência, abandono, horários, SLA.
3. Worker outbox e protocolo seguro de confirmação de entrega.
4. Adapter Teams Embedded com bot original e feature flag.
5. Bot Native Teams, outros canais, Finesse e relatórios.

## Fontes
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/lang_transaction.html
- https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages
