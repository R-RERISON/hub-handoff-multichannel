# Implementation Plan — SPEC-013: SLA, relatórios, qualidade e observabilidade

**State:** proposed architecture only / no feature implementation in this commit.
**Constitution:** `CONSTITUTION.md` is normative; `.specify/memory/constitution.md` complements it.
**Dependencies:** 008 supervisão; 009 evidência; 010 monitoria para métricas de auxílio; 012 canal para métricas E2E. **Wave:** W3–W4.

## Technical context

Backend FastAPI/SQLAlchemy 2, SQLite sintético da POC, SPA React/TS/Vite. SQL Server, Teams, Entra ID e workers externos exigem homologação própria (não presumir que já funcionam). Sem GitHub Actions; gates locais e evidências por SHA.

## Architectural approach to validate

1. Telemetria OpenTelemetry e métricas agregadas a partir de event log com validação de cardinalidade.
2. Definir SLO por processo; dashboards autorizados; testes de falha e capacidade isolados.

## Vertical slices

1. **O.1 Dicionário de métricas e KPIs por fila** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
2. **O.2 Telemetria/alertas e indicadores de qualidade** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
3. **O.3 Carga, continuidade, DR e evidências de readiness** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.

## Contracts and risks

- Definir interface versionada, estado persistente, ownership, idempotência e observabilidade antes de escrever código.
- Manter compatibilidade e falhar fechado quando schema, grant ou adapter estiver ausente.
- Eventos fora de ordem e fuso horário diferente.
- Baixo volume de eventos distorce médias.
- SLO degradado mas provedor externo indisponível.
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
