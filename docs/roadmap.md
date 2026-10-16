## POC-005 — RBAC local, filas e alertas automáticos

Branch feat/005-rbac-auto-dispatch. Backend: usuários individuais, tokens opacos, papéis e ownership; login com lockout, heartbeat e revogação; worker periódico SQLite com distribuição FIFO e rodízio por fila, ofertas persistidas, cooldown, capacidade, membros e auditoria. Frontend: login por papel, Mesa do Operador autenticada, popup e alertas opcionais, supervisão com ordem e vinculação de operadores, ajuste de capacidade.

Gates: testes locais, autorização negativa, duas identidades simultâneas, capacidade, rodízio, N1→N2, expiração, reentrada, responsividade e segurança. Sem GitHub Actions.

Próximos: Entra ID/OIDC, isolamento multioperação, Alembic, worker/outbox externo, Teams adapter, SSE/WebSockets e testes de carga. [SPEC-005](specs/POC-005-rbac-auto-dispatch.md).


## POC-004 — Portais separados e navegação por rotas

Implementação publicada na branch `feat/004-separated-workspaces`. Separação real de interfaces de Operador, Supervisão, Administração (landing planejada) e Laboratório, com React Router e componentes independentes. Mesmo FastAPI e SQLite da POC 0.3, sem alteração de esquema.

Critérios: build React/TypeScript, testes locais de contrato de rotas, renderização em múltiplas resoluções e regressão N1 → N2 → Bruno. Não usar GitHub Actions. **Próxima etapa depois da homologação**: design system/componentes compartilhados, autorização por perfis reais e experiência completa de supervisão.

Ver [UX-004](ux/UX-004-workspace-separation.md) e [ADR-0004](architecture/ADR-0004-separated-workspaces.md).


# Roadmap com custo mínimo e testes locais

## POC-002 / Primeira entrega
SQLite + SQLAlchemy, FastAPI, distribuição manual e atômica, sessões, operadores, mensagens, outbox pendente, React/TypeScript cockpit e testes locais. Não usa GitHub Actions; nenhum serviço externo.

## POC-003 — Fluxo de operação humana (implementação publicada)

Incremento em branch `feat/003-operator-workflow`: mesa de operador independente, oferta com prazo, aceite/recusa, reserva de capacidade incluindo ofertas, transferência para N2, histórico auditável e testes de concorrência. Pendente de homologação local e build React/TypeScript. Veja [POC-003](specs/POC-003-operator-workflow.md).

Este incremento **não substitui** a SPEC de adapter Teams: continua pendente e virá após estabilização do núcleo.

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
