# Implementation Plan — SPEC-006C: Baseline verificável e promoção controlada da POC

**Status**: PROPOSED / NOT IMPLEMENTED — detalhar e executar `/speckit-plan` na abertura do incremento.
**Constitution gate**: `CONSTITUTION.md` e `.specify/memory/constitution.md` mandatório.
**Prerequisites**: PR #28 Draft, banco TEMP 006b4, Constituição v1.1.
**Delivery wave**: W0; prioridade P0.

## Technical context

- Baseline: FastAPI, SQLAlchemy 2, SQLite somente POC, React/TypeScript/Vite; trabalhar sobre head homologado após 006C.
- Identidade/escopo: enforcement no backend; migrações aditivas apenas em ambiente isolado, sem adoção do SQLite original.
- Testes: Python Pytest, Ruff, frontend architecture, TypeScript, Vite, regressão de N1→N2 e validação manual guiada.
- Limites atuais: GitHub Actions proibido; sem endpoint Teams ativo, sem acesso de produção e sem auto-merge.

## Proposed design and contracts (subject to analysis)

1. Usar apenas scripts/qa existentes e relatórios sanitizados; complementar com checklist de revisão manual por SHA.
2. Preservar PR #28 como Draft até decisão explícita; qualquer mudança de runtime exige branch de correção independente.

## Vertical slices

1. **C.1 Inventariar commits, diffs, dependências, PRs paralelos e atualizar a matriz de evidências** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.
2. **C.2 Homologar UX-02, UX-05 e UX-08 com navegador de viewport comprovado** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.
3. **C.3 Revalidar gates no SHA final, conferir concorrência e segurança, obter decisão formal de promoção** — entregar API/modelo + autorização + testes + UX/documentação pertinente; abrir PR pequeno.

## Risks and decisions to validate

- Mudança do head durante homologação invalida evidências afetadas.
- Browser sem viewport comprovável não satisfaz UX-08.
- Banco de homologação fora de TEMP interrompe imediatamente a execução.
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
