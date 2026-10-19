# RC-001 — Baseline consolidada do Handoff Hub

**Data:** 2026-10-19  
**Estado:** CODE_FROZEN_FOR_QA / NOT_TESTED / NOT_ACCEPTED / DRAFT  
**Escopo:** POC local sintética, NÃO produção.

## Identidade e procedência
- Origem integral da árvore de código: `feat/007b1-people-inventory-desktop`, PR #50, commit `ee0a834a283b4ce60e129185961ef4d1cf8072da`.
- Ancestral: `main` em `7de0e16976ee856280ebb82366380580ccb956a6`.
- Candidato: `integration/rc-001-consolidated-poc-20261019`.
- Técnica: snapshot da árvore da origem, novo commit único com pai `main`, somente overlay dos arquivos de governança listados em `RC-001-MANIFEST.json`.
- A `main` não foi alterada; branches, 474 commits prévios e PRs históricos permanecem intactos. O histórico original fica rastreável nos PRs de origem.
- O snapshot NÃO foi testado no Windows e NÃO possui aceite humano. Gates antigos por SHA não são transferidos.

## Escopo funcional versionado
- POC FastAPI/SQLAlchemy/SQLite e React/TypeScript/Vite: Mesa do Operador, Supervisão, Administração e Laboratório.
- Login local com papéis, grants de fila, despacho automático e fluxo N1→N2.
- Histórico segmentado VERIFIED, journaling de leituras/decisões e migrações Alembic opt-in 006b1–006b4.
- SPEC-006C: evidências sintéticas, UX desktop-first e ferramentas de QA.
- SPEC-007/A: gestão de filas, criação auditada, lifecycle com migração 007a2 opt-in.
- SPEC-007/B0.1: validação de escopo e papel transacional.
- SPEC-007/B1.0: diretório de pessoas, contas e memberships exclusivamente read-only; homologação ainda não executada.
- SPEC-007/B1.1, B2, C e demais features do portfólio continuam pendentes.

## Não incorporar automaticamente branches divergentes
Comparações GitHub indicaram divergência em `spec/006-enterprise-operating-model` (PR #14),
`feat/006-queue-scoped-auth-foundation` (PR #15) e
`feat/006b-migrations-queue-segments` (PR #17).
São frentes históricas/alternativas, não foram mescladas ou copiadas.
O conteúdo específico de cada uma exige triagem antes de eventual aproveitamento.

## Política de trabalho a partir da RC-001
1. Uma única árvore e SHA candidata para homologação integrada, não vários testes avulsos usados como aceite.
2. Nenhum novo desenvolvimento funcional sobre a RC enquanto os gates estão abertos. Defeitos de QA precisam de correção rastreável, novo SHA e reexecução.
3. Uma linha ativa de desenvolvimento e uma de estabilização, com PRs pequenos somente depois de fixar uma baseline aprovada.
4. Nunca usar `start.cmd` sem `--lab` para testes da candidata. Nunca alterar `data/handoff-poc.db` ou credenciais reais.
5. Resultados: CODED != AUTOMATED_PASS != FUNCTIONAL_PASS != HUMAN_ACCEPTED != PRODUCTION_READY.
6. PRs/branches antigos serão classificados e arquivados SOMENTE após aceite e aprovação explícita. Não apagar automaticamente.
7. Nenhum merge/deploy/Teams/Entra/SQL Server corporativo sem autorização e gates próprios.

**Próxima ação autorizada:** seguir `RC-001-QA-MATRIX.md` e registrar um único resultado por rodada integrada. 
