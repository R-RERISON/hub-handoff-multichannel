# Implementation Plan — SPEC-015: Persistência SQL Server e workers resilientes

**State:** proposed architecture only / no feature implementation in this commit.
**Constitution:** `CONSTITUTION.md` is normative; `.specify/memory/constitution.md` complements it.
**Dependencies:** 006C, 006B Alembic opt-in; 014 para acessos corporativos antes de produção. **Wave:** W1–W3.

## Technical context

Backend FastAPI/SQLAlchemy 2, SQLite sintético da POC, SPA React/TS/Vite. SQL Server, Teams, Entra ID e workers externos exigem homologação própria (não presumir que já funcionam). Sem GitHub Actions; gates locais e evidências por SHA.

## Architectural approach to validate

1. Design de transações específicas para SQL Server; migração controlada após contrato de esquema e concorrência revisados.
2. Worker com lease no banco, retries idempotentes, métricas de backlog e failover reproduzível.

## Vertical slices

1. **D.1 Esquema SQL Server e migrations em laboratório novo** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
2. **D.2 Despacho/worker multi-instância, concurrency gate** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
3. **D.3 Recovery/backup, outbox/DLQ, performance e DR** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.

## Contracts and risks

- Definir interface versionada, estado persistente, ownership, idempotência e observabilidade antes de escrever código.
- Manter compatibilidade e falhar fechado quando schema, grant ou adapter estiver ausente.
- Deadlock, lock timeout e worker crash em commit.
- Mismatch de versões da API e do esquema.
- Failover e replay de mensagem depois de ACK externo.
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
