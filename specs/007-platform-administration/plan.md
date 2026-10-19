# Implementation Plan — SPEC-007: Administração de operações, filas, pessoas e permissões

**Status**: IN_PROGRESS / SPEC-007-A0 iniciado — inventário read-only antes das mutações do ciclo de vida; testes locais ainda pendentes.
**Constitution gate**: `CONSTITUTION.md` e `.specify/memory/constitution.md` mandatório.
**Prerequisites**: 006C para desenvolvimento integrado; SPEC-006A/006B para grants e esquema; SPEC-018 para UX.
**Delivery wave**: W1; prioridade P0.

## Technical context

- Baseline: FastAPI, SQLAlchemy 2, SQLite somente POC, React/TypeScript/Vite; trabalhar sobre head homologado após 006C.
- Identidade/escopo: enforcement no backend; migrações aditivas apenas em ambiente isolado, sem adoção do SQLite original.
- Testes: Python Pytest, Ruff, frontend architecture, TypeScript, Vite, regressão de N1→N2 e validação manual guiada.
- Limites atuais: GitHub Actions proibido; sem endpoint Teams ativo, sem acesso de produção e sem auto-merge.

## Proposed design and contracts (subject to analysis)

1. API administrativa versionada; validação transacional e revisão de autorização por operação/fila/ação.
2. Formulários React segregados por rotas administrativas e sem comandos operacionais de operador.

## Vertical slices

1. **A Cadastro de operações/filas, estados e políticas mínimas** — A0 inventário read-only, A1.1 criação auditada via journal 006b4 sem migração, A1.2 lifecycle opt-in 007a2 com CAS, audit trail e proteção de intake/despacho/transferência (PRs pequenos e gates por SHA).
2. **B Pessoas, perfis, memberships e grants separados** — B0 reforça RBAC e tenancy de rotas de membership/capacidade/presença antes da UI, com testes negativos. B1 inventário e gestão de pessoas/membership; B2 grants/auditoria/revogação. Entregas em PRs pequenos.
3. **C Revisão de alterações, auditoria, UX, rollback e documentação** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.

## Risks and decisions to validate

- Fila pausada enquanto há ofertas já emitidas.
- Desativação de operador com conversa ativa.
- Dois administradores alteram capacidade simultaneamente.
- Revisar interfaces, entidades, concorrência e migrações por `/speckit-analyze` antes de alterar runtime.
- Registar ADR se houver mudança de boundary, tenancy, esquema versionado ou interpretação da Constituição.

## Definition of Done / release gate

- [ ] Contratos de API, esquema e autorização revisados antes da implementação.
- [ ] `/speckit-tasks` refinado, rastreabilidade FR → cenários → testes, análise de consistência.
- [ ] Gates `start.cmd --check` aprovados no SHA da feature em Windows e saída sanitizada anexada ao PR.
- [ ] Testes negativos cross-operation/cross-queue, concorrência quando houver, regressão transfer N1→N2.
- [ ] QA de UX em desktop 1366×768 e 1920×1080, mais navegação por teclado e zoom 200% quando houver interface.
- [ ] Migração/reversão demonstrada em cópia/lab sintético; banco original intocado.
- [ ] Convergência `/speckit-converge`, review técnico e aprovação explícita; sem deploy/merge automático.

## Rollback

Abandonar/reverter commit no branch de feature; restaurar banco sintético a partir de backup verificado antes do teste. Nunca apagar journal ou executar downgrade destrutivo para forçar passagem do gate; não tocar no banco original.
