# Implementation Plan — SPEC-012: Adapter Teams Embedded e mensageria E2E

**State:** proposed architecture only / no feature implementation in this commit.
**Constitution:** `CONSTITUTION.md` is normative; `.specify/memory/constitution.md` complements it.
**Dependencies:** 014 IAM de integrações, 015 durabilidade e trabalhadores, 016 proteção de dados; 011 opcional para fase mídia. **Wave:** W3.

## Technical context

Backend FastAPI/SQLAlchemy 2, SQLite sintético da POC, SPA React/TS/Vite. SQL Server, Teams, Entra ID e workers externos exigem homologação própria (não presumir que já funcionam). Sem GitHub Actions; gates locais e evidências por SHA.

## Architectural approach to validate

1. Ports/adapters com contrato autenticado e capability matrix; primeira vertical text-only sem presumir anexos.
2. Workers de inbox/outbox com state machine, idem key, retry/jitter, DLQ, ACK e reconciliação.

## Vertical slices

1. **E.1 Contrato canonical inbound/outbound e fake adapter testado** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
2. **E.2 Adapter Tornado/Teams Embedded e feature flag de canário** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
3. **E.3 Retry/ACK/DLQ, falhas E2E e rollback auditado** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.

## Contracts and risks

- Definir interface versionada, estado persistente, ownership, idempotência e observabilidade antes de escrever código.
- Manter compatibilidade e falhar fechado quando schema, grant ou adapter estiver ausente.
- ACK chega duplicado ou fora de ordem.
- Bot original indisponível durante resposta do humano.
- Troca de tenant, expiração de autorização e replay de webhook.
- Executar `/speckit-analyze` sobre specs, plano, tarefas e Constitution antes da implementação.

## Release and rollback gates

- [ ] Contratos de API, identidade, autorização e migrações revisados.
- [ ] `/speckit-plan` e `/speckit-tasks` refinados quando a feature abrir execução.
- [ ] Pytest, Ruff, frontend architecture, TS/Vite via `start.cmd --check` no SHA final, sem GitHub Actions.
- [ ] Testes de negação cross-queue/operation e concorrência/idempotência onde aplicáveis.
- [ ] QA de UX com teclado/viewport quando a feature afeta portais.
- [ ] Integridade/backup/rollback somente no laboratório sintético, base original intocada.
- [ ] `/speckit-converge` + revisão humana e decisão de merge separada de release corporativo.

**Rollback:** retirar alteração da branch de incremento, interromper integração opcional por flag e restaurar cópia sintética verificada, sem downgrade destrutivo de journal. Registar plano final específico antes da implementação.
