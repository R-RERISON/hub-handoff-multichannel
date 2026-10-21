# SPEC-018 U1 — Foundations visuais (implementação isolada)

**Branch:** feat/spec018-u1-light-foundations-20261021
**Base SHA:** `c4bbf981f0d049951d0b04fb5a78d421ceb42808`, PR #59 Draft (liveness, Issue #58).
**Fonte de escopo:** PR #60 (Q1/Q2 aprovadas em 21/10/2026).
**Status:** CODED / STATIC_CHECK_REQUIRED / WINDOWS_BUILD_QA_REQUIRED / VISUAL_QA_REQUIRED / DRAFT / NO_MERGE

## Escopo entregue no U1

- `web/src/design-system/foundations.css`: tokens semânticos, cor, espaçamento, borda, foco e superficies claras com baixa sombra. Carregamento **após** `styles.css`, sem alterar as regras G07.
- `web/src/design-system/EmptyState.tsx`: componente reutilizável somente informativo, `role=status`. Aplicado a filas e contas vazias e a resultados vazios da supervisão.
- `web/scripts/foundations.test.mjs`: testes estáticos de carregamento, contraste do conjunto de cores, teclado, reduced-motion, compatibilidade com G07 e ausência de retry mutante. `test:architecture` passa a executar **também** esses testes, sem substituir a suíte existente.
- Sem edição em `poc_api.py`, autenticação, RBAC, schemas, migrations, grants, rotas ou mutações. Nenhum MONITOR, nenhum acesso externo.

## Visual UX proposto

Superfície branca em canvas cinza-azulado leve, bordas sutis, elevação mínima, navegação azul-ardósia, componentes sem excesso de badges. Aumenta clareza de foco sem reflow de containers críticos. Prefere movimento reduzido. Cores textuais primárias e muted / primária sobre branco devem atender >=4.5:1 (testado matematicamente pelo novo Node test), sem afirmar conformidade WCAG da aplicação inteira.

## Critérios de aprovação (pendentes)

1. `npm run test:architecture` e `npm run build`; `start.cmd --check` integrado com Python/Ruff e TS/Vite no Windows, em worktree TEMP nova do **SHA exato** e DB sintético.
2. Review visual real, 1366×768/1920×1080, zoom 100%/200% na Mesa, Admin e Supervisão, mouse/Tab/Enter; verificar modal e botões, tabelas focáveis, nota de transferência, diálogos e estado vazio.
3. Não regredir SPEC-006C UX-08 mobile 390×844, **que continua bloqueante para release** mesmo se U1 desktop passar. Nenhuma funcionalidade mobile foi implementada nesta mudança.
4. Validar que o PR #59 liveness e a Issue #58 têm revisão independente; este PR herda código ainda Draft, mas **não herda aprovação G09/G10**.
5. Reconciliar SPEC local da worktree `spec/018-premium-workspace-ux` antes de aplicar mudanças naquele checkout. Não sobrescrevê-lo.

## Rollback

Reverter este commit no branch U1, nunca fazer reset ou merge automático em #59/#57/#51; nenhum rollback de schema necessário. Nenhum dado real, tokens ou segredos de laboratório devem ser copiados para evidência.
