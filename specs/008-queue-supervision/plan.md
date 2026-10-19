# Implementation Plan — SPEC-008: Supervisão operacional por fila

**Status**: PROPOSED / NOT IMPLEMENTED — detalhar e executar `/speckit-plan` na abertura do incremento.
**Constitution gate**: `CONSTITUTION.md` e `.specify/memory/constitution.md` mandatório.
**Prerequisites**: 007, 006A/006B, 018.
**Delivery wave**: W2; prioridade P0.

## Technical context

- Baseline: FastAPI, SQLAlchemy 2, SQLite somente POC, React/TypeScript/Vite; trabalhar sobre head homologado após 006C.
- Identidade/escopo: enforcement no backend; migrações aditivas apenas em ambiente isolado, sem adoção do SQLite original.
- Testes: Python Pytest, Ruff, frontend architecture, TypeScript, Vite, regressão de N1→N2 e validação manual guiada.
- Limites atuais: GitHub Actions proibido; sem endpoint Teams ativo, sem acesso de produção e sem auto-merge.

## Proposed design and contracts (subject to analysis)

1. Queries autorizadas por queue_id e operation_id com agregação sobre estados atuais e segmentos de histórico.
2. Workspace com filtros, KPIs e gestão delegada; planejar atualização segura com invalidação de cache.

## Vertical slices

1. **A Dashboard e fila selecionada com isolamento** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.
2. **B Equipe, políticas delegadas e trilhas** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.
3. **C Estados de loading/erro/revogação, UX e cenários negativos** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.

## Risks and decisions to validate

- Revogação durante tela aberta.
- Fila sem operadores ou capacidade.
- Sessão N1 transferida para N2 durante agregação.
- Revisar interfaces, entidades, concorrência e migrações por `/speckit-analyze` antes de alterar runtime.
- Registar ADR se houver mudança de boundary, tenancy, esquema versionado ou interpretação da Constituição.

## Definition of Done / release gate

- [ ] Contratos de API, esquema e autorização revisados antes da implementação.
- [ ] `/speckit-tasks` refinado, rastreabilidade FR → cenários → testes, análise de consistência.
- [ ] Gates `start.cmd --check` aprovados no SHA da feature em Windows e saída sanitizada anexada ao PR.
- [ ] Testes negativos cross-operation/cross-queue, concorrência quando houver, regressão transfer N1→N2.
- [ ] QA de UX em 390×844, 1366×768 e 1920×1080 quando houver interface.
- [ ] Migração/reversão demonstrada em cópia/lab sintético; banco original intocado.
- [ ] Convergência `/speckit-converge`, review técnico e aprovação explícita; sem deploy/merge automático.

## Rollback

Abandonar/reverter commit no branch de feature; restaurar banco sintético a partir de backup verificado antes do teste. Nunca apagar journal ou executar downgrade destrutivo para forçar passagem do gate; não tocar no banco original.
