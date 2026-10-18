# Implementation Plan — SPEC-017: Teams Native e expansão multicanal/multibot

**State:** proposed architecture only / no feature implementation in this commit.
**Constitution:** `CONSTITUTION.md` is normative; `.specify/memory/constitution.md` complements it.
**Dependencies:** 012 Embedded comprovado, 014, 015, 016; capability matrix de 011. **Wave:** W4.

## Technical context

Backend FastAPI/SQLAlchemy 2, SQLite sintético da POC, SPA React/TS/Vite. SQL Server, Teams, Entra ID e workers externos exigem homologação própria (não presumir que já funcionam). Sem GitHub Actions; gates locais e evidências por SHA.

## Architectural approach to validate

1. Reutilizar contrato canônico do Embedded; adapters distintos sem lógica de negócio replicada.
2. Registrar capabilities/versionamento por integration_id; controlar rollout e health por canal.

## Vertical slices

1. **N.1 Teams App Native e identidade independente** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
2. **N.2 Segundo adapter e capabilities/health** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
3. **N.3 Testes E2E multitenant/canal, canário e rollback** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.

## Contracts and risks

- Definir interface versionada, estado persistente, ownership, idempotência e observabilidade antes de escrever código.
- Manter compatibilidade e falhar fechado quando schema, grant ou adapter estiver ausente.
- Teams tenant sem permissão de instalação.
- Canal sem suporte a conteúdo rico.
- Mensagem duplicada por dois adapters distintos.
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
