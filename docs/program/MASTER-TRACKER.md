> **Atualização 19/10/2026:** o tracker abaixo contém estados de planejamento
> de 18/10 e pode descrever SPEC-007 como NOT_STARTED apesar de implementações
> posteriores. O estado operacional atualizado é a [baseline RC-001](RC-001-BASELINE.md)
> e sua [matriz de QA](RC-001-QA-MATRIX.md). SPEC-007 A0/A1/B0.1/B1.0 têm
> código candidato; RC-001 e B1.0 continuam SEM TESTES E SEM ACEITE.
>
# Handoff Hub — MASTER TRACKER (Spec Kit / Project Control)

> **Fonte de verdade do plano** | Versão 0.1, 2026-10-18. Proposta no branch `spec/006c-018-program-rebaseline-20261018` / [tracking #42](https://github.com/R-RERISON/hub-handoff-multichannel/issues/42). Não modificar o registro histórico de homologação do PR #28 para parecer completo.

## 1. Baseline factual e limites

- **main**: `7de0e16976ee856280ebb82366380580ccb956a6` (somente bootstrap README; não incorporar automaticamente).
- **Branch funcional candidata**: `feat/006b5b-security-decisions-journal`, snapshot de planejamento `14e01562f05a6229f51e4fc7383d0443d11beae0`; [PR #28](https://github.com/R-RERISON/hub-handoff-multichannel/pull/28) Draft com 423 commits / 148 arquivos alterados reportados na leitura da API de 18/10. A branch funcional pode avançar; registrar SHA novamente antes de qualquer decisão.
- **Runtime**: POC local SQLite/FastAPI/React; RBAC, despacho, transferência e leitura VERIFIED versionada 006b4 no laboratório; **não** há validação de Entra/OIDC, SQL Server, Teams real, WORM ou prontidão para produção.
- **Gates reportados pelo PR**: 132 Pytest passed / 1 skipped, Ruff, 15/15 frontend, TS/Vite e probe PASS no SHA reportado; UX-08 BLOCKED; UX-02/05 NOT_RUN; revisão do diff e decisão de merge PENDING. Estes são relatos registrados no repositório, não testes executados por esta alteração documental.
- **Imutáveis**: SQLite original `data/handoff-poc.db` não recebe migration, seed ou teste mutante; sem GitHub Actions; sem auto-merge; sem dados reais/segredos.

## 2. Carteira única das SPECs

| SPEC | Domínio | Pri. | Wave | Depende de | Estado / evidência | Issue | Artefatos |
|---|---|---|---|---|---|---|---|
| 006C | Baseline release | P0 | W0 | PR #28 | **BLOCKED / manual QA** | [#29](https://github.com/R-RERISON/hub-handoff-multichannel/issues/29) | [Spec Kit](../../specs/006c-release-baseline/spec.md) |
| 007 | Administração | P0 | W1 | 006C,006A/006B,018 | **NOT_STARTED** | [#30](https://github.com/R-RERISON/hub-handoff-multichannel/issues/30) | [Spec Kit](../../specs/007-platform-administration/spec.md) |
| 008 | Supervisão | P0 | W2 | 007,006B,018 | **NOT_STARTED** | [#31](https://github.com/R-RERISON/hub-handoff-multichannel/issues/31) | [Spec Kit](../../specs/008-queue-supervision/spec.md) |
| 009 | Auditoria | P0 | W2 | 006B,007,008 | **NOT_STARTED** | [#32](https://github.com/R-RERISON/hub-handoff-multichannel/issues/32) | [Spec Kit](../../specs/009-auditor-evidence/spec.md) |
| 010 | Monitoria | P1 | W2 | 006B,007,008 | **NOT_STARTED** | [#33](https://github.com/R-RERISON/hub-handoff-multichannel/issues/33) | [Spec Kit](../../specs/010-assisted-monitoring/spec.md) |
| 011 | Mídia segura | P1 | W2 | 006B,009,016 para prod | **NOT_STARTED** | [#34](https://github.com/R-RERISON/hub-handoff-multichannel/issues/34) | [Spec Kit](../../specs/011-secure-attachments/spec.md) |
| 012 | Teams Embedded | P0 | W3 | 014,015,016,011 mídia opcional | **NOT_STARTED** | [#35](https://github.com/R-RERISON/hub-handoff-multichannel/issues/35) | [Spec Kit](../../specs/012-teams-embedded-adapter/spec.md) |
| 013 | SLA / SRE | P1 | W3–W4 | 008,009,010,012 | **NOT_STARTED** | [#36](https://github.com/R-RERISON/hub-handoff-multichannel/issues/36) | [Spec Kit](../../specs/013-service-analytics-readiness/spec.md) |
| 014 | Entra ID/OIDC | P0 | W1/W3 | 006C,007; antes de dados reais | **NOT_STARTED** | [#37](https://github.com/R-RERISON/hub-handoff-multichannel/issues/37) | [Spec Kit](../../specs/014-enterprise-identity/spec.md) |
| 015 | SQL Server / Workers | P0 | W1/W3 | 006C,006B,014 para prod | **NOT_STARTED** | [#38](https://github.com/R-RERISON/hub-handoff-multichannel/issues/38) | [Spec Kit](../../specs/015-durable-persistence-workers/spec.md) |
| 016 | LGPD / WORM | P0 | W1/W3 | 006B,009; antes de dados reais | **NOT_STARTED** | [#39](https://github.com/R-RERISON/hub-handoff-multichannel/issues/39) | [Spec Kit](../../specs/016-privacy-governance-audit/spec.md) |
| 017 | Teams Native e multibot | P2 | W4 | 012,014,015,016 | **NOT_STARTED** | [#40](https://github.com/R-RERISON/hub-handoff-multichannel/issues/40) | [Spec Kit](../../specs/017-native-multichannel/spec.md) |
| 018 | Premium UX / a11y | P0 | W1/transversal | 006C; atende 007–017 | **NOT_STARTED** | [#41](https://github.com/R-RERISON/hub-handoff-multichannel/issues/41) | [Spec Kit](../../specs/018-premium-workspace-ux/spec.md) |

**Interpretação:** `NOT_STARTED` = SPEC/plan/tasks disponíveis para revisão, nenhum desenvolvimento da feature validado nesta carteira. `BLOCKED` = dependências/gates formais faltando. SPECs históricas 001–006B permanecem em `docs/specs`; suas realizações estão em PRs de desenvolvimento, **não** homologadas na `main`.

## 3. Ondas e critical path

- **W0 — Recuperar controle:** SPEC-006C; terminar UX-08/UX-02/UX-05, diff/security review, matriz de evidência e decisão expressa sobre PR #28. Nenhuma feature deve ser confundida com autorização para merge da POC.
- **W1 — Base de produto:** 018 design system e componentes incrementais, 007 administração, iniciar desenhos 014 (IAM), 015 (SQL Server/worker) e 016 (política de dados). Essas frentes podem ter discovery paralelo; integrações reais seguem bloqueadas.
- **W2 — Workspaces:** 008 supervisão, 009 auditoria, 010 monitoria bidirecional, 011 mídia; executar fatias e dependências de segurança, não mega-PRs.
- **W3 — Canal real e operação:** gates de 014/015/016 aprovados, 012 Embedded text-first, 013 SLAs/observabilidade/readiness. Mídia externa só com capabilities e 011 homologada.
- **W4 — Expansão:** 017 Teams Native/segundo bot, robustez de 013 e release corporativo separado.

**Critical path:** `006C → (018/007) → 008/009 → 014+015+016 → 012 → 013/017`. Workstreams paralelos não eliminam gates de segurança. 010/011 seguem trilhas próprias sobre grants/proveniência.

## 4. Regras de controle do programa

1. **Cada SPEC tem uma única issue de tracking** (#29–#41) e artefatos `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`; PRs de implementação sempre mencionam a issue e a matriz de aceite.
2. **States**: `DRAFT → READY_FOR_PLAN → PLANNED → IN_PROGRESS → IN_REVIEW → QA_PENDING → ACCEPTED`, com `BLOCKED` e `REWORK` explícitos. `ACCEPTED` = aceita para a baseline de código, não `PROD_READY`. Issue aberta até aceite real.
3. **Transição somente por evidência**: tarefa marcada [x] exige commit/PR, ID do caso, versão do banco, ambiente, SHA final e resultado; descrição de código não é prova de execução.
4. **Release gates**: revisar `docs/program/RELEASE-GATES.md`, `docs/qa/PR-028-ui-final-gates.md`, riscos, rollback, autorizações e resultados no SHA final.
5. **WIP limit**: uma implementação crítica ativa + um discovery paralelo por vez, salvo decisão registrada em issue mestra. Nunca juntar 007–018 num único PR de runtime.
6. **Revisão periódica no GitHub**: atualizar esta matriz com estado real, blockers, decisões, próximo incremento e links das provas a cada PR e homologação. Nenhum progresso é inferido automaticamente por merge ou issue fechada.
7. **Governança SPECKIT**: `/speckit-specify`, `/speckit-clarify` quando necessário, `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`, `/speckit-converge`. Para execução, ativar **uma** feature por vez, não gravar `.specify/feature.json` do portfólio.

## 5. Definições de pronto — níveis distintos

- **SPEC_READY**: necessidades, cenários, FR/SC, dependências, risco e limites acordados; aprovação de produto e arquitetura.
- **CODE_ACCEPTED**: implementado por fatia, testes locais e cenários negativos no SHA, review e rollback válidos, documentação sincronizada.
- **MAIN_INTEGRATED**: PR aprovado explicitamente para merge e SHA confirmado na main; não equivale a uso real.
- **PRODUCTION_READY**: gates independentes de IAM, DB/workers, canal real, LGPD/WORM, DR/carga, observabilidade, segurança e autorização de operação.

## 6. Painel de próximos passos reais

1. [#29 — SPEC-006C](https://github.com/R-RERISON/hub-handoff-multichannel/issues/29): completar evidência browser estável UX-08 em Histórico e Mesa, UX-02 Supervisor N1/N2 e UX-05 transferência verificada.
2. Auditar 148 arquivos do diff PR #28 e conciliar RFC lateral #14, alternativa #15 e design #17 **sem merges automáticos**.
3. Reexecutar gates afetados no SHA final local Windows e decidir explicitamente a promoção à main.
4. Promover 018 e 007 a `READY_FOR_PLAN` somente depois da baseline e do design review.

## 7. Risco de deriva documental

`docs/roadmap.md` histórico contém numeração POC-005/006 diferente de SPEC-005/006 e conteúdo anterior ao release 006B. Para decisões atuais **este MASTER-TRACKER prevalece apenas após aceite do PR de planejamento**; até lá, é proposta. Ver [crosswalk](./SPEC-CROSSWALK.md) e [riscos](./DECISIONS-RISKS.md).

## Incremento em andamento: SPEC-006C-1 (19/10/2026)

- Branch: feat/006c1-ux02-ux05-synthetic-evidence, baseada na branch de planejamento. Contém fixture de transferência N1→N2 no laboratório TEMP e checker de evidências PNG por SHA.
- Implementação de ferramentas QA apenas: nenhum endpoint de produção, migração, código React ou SQLite original alterado.
- Gate local start.cmd --check e QA real de UX-02/05/08: PENDENTES. Resultados reportados por scripts e testes que não foram executados não podem ser marcados PASS.
- PR #28 segue Draft; PR de implementação da 006C-1 separado da reorganização (#43). Não interpretar esta fatia como pronta para promoção à main.
