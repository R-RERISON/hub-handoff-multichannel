# Roadmap com custo mínimo e testes locais

## POC-002 / Primeira entrega
SQLite + SQLAlchemy, FastAPI, distribuição manual e atômica, sessões, operadores, mensagens, outbox pendente, React/TypeScript cockpit e testes locais. Não usa GitHub Actions; nenhum serviço externo.

## POC-003 / Evolução imediata
Extrair repositories/services da API única; Alembic para migrações; campos de política de fila, habilidades, SLA, cobertura de turnos; idempotência e validação de ownership completas; documentação de erros; testes adicionais de conflitos, retries e cross-operation.

## POC-004 / Operação humana completa
Área operador autenticado, aceite e recusa, reserva OFFERED, interrupção, transferência, histórico de operador, anexos, alertas e status. WebSocket/SSE, autenticação e autorização por papel.

## POC-005 / Teams Embedded
Criar adapter do bot original, com feature flag e homologação isolada. Protocolo REST/webhook versionado, inbox/outbox workers e ACK. Manter a conversa no bot original. Falhas e rollback testados.

## POC-006 / Expansão
Multioperação, segunda integração, Teams App Native, Cisco Finesse opcional, SLA/CSAT e observabilidade.

## Gate para SQL Server
Concluir avaliação do modelo de entidades, constraints e tipos; migrar via Alembic; implementar mecanismo apropriado de locking/transação no SQL Server; validar conciliação e concorrência no banco-alvo. Sem migração automática do banco atual legado.

## Custos
Sem pipelines GitHub Actions. Executar testes, lint e builds na máquina local; avaliação posterior de servidor/infraestrutura própria.
