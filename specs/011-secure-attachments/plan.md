# Implementation Plan — SPEC-011: Anexos, imagens e prints seguros

**State:** proposed architecture only / no feature implementation in this commit.
**Constitution:** `CONSTITUTION.md` is normative; `.specify/memory/constitution.md` complements it.
**Dependencies:** 006B VERIFIED, 009 histórico e 016 regras de retenção antes de produção. **Wave:** W2.

## Technical context

Backend FastAPI/SQLAlchemy 2, SQLite sintético da POC, SPA React/TS/Vite. SQL Server, Teams, Entra ID e workers externos exigem homologação própria (não presumir que já funcionam). Sem GitHub Actions; gates locais e evidências por SHA.

## Architectural approach to validate

1. Armazenamento privado + validação server-side allowlist PNG/JPEG/WebP; quarentena e scanner com política fail-closed.
2. Separar attachment metadata da mensagem; vincular proveniência e grants a segmento e evento de acesso.

## Vertical slices

1. **M.1 Modelo, storage privado, upload e validação** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
2. **M.2 Quarentena, preview e download sob grants** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.
3. **M.3 Integração ao histórico, limpeza/retention e testes adversariais** — modelo + contratos + política de acesso + testes negativos + UX quando aplicável; PR pequeno por fatia.

## Contracts and risks

- Definir interface versionada, estado persistente, ownership, idempotência e observabilidade antes de escrever código.
- Manter compatibilidade e falhar fechado quando schema, grant ou adapter estiver ausente.
- Mime spoofing, zip bomb e arquivo descomprimido acima do limite.
- Transferência N1→N2 com visibilidade restrita.
- Falha de antivírus deixa objeto em quarentena, nunca CLEAN.
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
