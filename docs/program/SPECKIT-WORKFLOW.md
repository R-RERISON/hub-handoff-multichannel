# Operação SPECKIT — do discovery à aceitação

## Como iniciar uma nova feature

1. Verificar [MASTER-TRACKER](./MASTER-TRACKER.md), issue correspondente e dependências. Trabalhar sobre baseline de código homologada; **não** construir runtime novo sobre o PR Draft #28 apenas por conveniência.
2. Ler `CONSTITUTION.md`, `AGENTS.md`, `docs/architecture/overview.md`, `docs/poc-data-model.md`, `docs/roadmap.md` e `.specify/memory/constitution.md`.
3. Usar `/speckit-specify` **uma feature por vez**, preferindo atualizar a SPEC planejada em `specs/<id>-<slug>/spec.md`, com caminho explícito `SPECIFY_FEATURE_DIRECTORY` para preservar numeração. O planning branch já prepara os drafts.
4. Rodar `/speckit-clarify` somente para ambiguidade material, depois `/speckit-plan`, `/speckit-tasks` e `/speckit-analyze`; registrar ADR para alteração de invariantes.
5. Abrir branch/PR de **fatia vertical pequena**, com issue ligada, API/DB/UX/testes negativos. Não implementar 007–018 como uma única mudança.
6. Executar `/speckit-implement` e `/speckit-converge`. Guardar SHA, Windows local `start.cmd --check`, evidence checklist, resultados de RBAC/concorrência e rollback em banco sintético. Sem GitHub Actions.
7. Revisão humana e QA bloqueadores; atualizar `tasks.md`, issue, MASTER-TRACKER e PR. Só depois decidir merge, separado do aceite de produção.

## Modelo de atualização de status (comentário no issue)

```text
SPEC: 0xx | Fatia: X.Y | Data UTC: YYYY-MM-DD
Status: NOT_STARTED / IN_PROGRESS / BLOCKED / IN_REVIEW / QA_PENDING / ACCEPTED
Branch / PR / Commit SHA:
Requisitos FR cobertos:
Testes executados (comando, ambiente, resumo, exit):
Gates manuais / visual / RBAC / concorrência:
Migrações e proteção do banco original:
Riscos / blockers / dependências:
Rollback testado:
Próximo passo / decisão necessária:
```

## Causas de bloqueio automático de aceitação

Falha de isolamento N1/N2, autorização somente frontend, transação não confiável, journal fail-closed omitido, segredo/PII real no Git, mudança do SQLite original, ausência de teste em SHA afetado, viewport incompleto e integração Teams simulada apresentada como real.

**Regra de frescor**: medir novamente HEAD, compare, testes e screenshots antes de cada release; snapshots estáticos não são evidência de estado atual.
