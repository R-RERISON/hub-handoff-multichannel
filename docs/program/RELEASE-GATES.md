> **Importante em 19/10/2026:** os dados abaixo são registros históricos
> por PR, NÃO aprovação do estado integrado atual. O gate único de integração
> vigente para o snapshot é [RC-001-QA-MATRIX](RC-001-QA-MATRIX.md), inteiramente
> NOT_RUN. A `main` permanece intacta.
>
# Handoff Hub — Release Gates e separação de aceites

**Snapshot**: 2026-10-18 | [PR #28](https://github.com/R-RERISON/hub-handoff-multichannel/pull/28) | Estado: **DRAFT / NÃO MERGEAR**.

## 1. Gate de incorporação da POC à main (SPEC-006C)

| Gate | Resultado documentado | Efeito | Evidência a registrar |
|---|---|---|---|
| CI local: Pytest, Ruff, frontend tests, TS/Vite | PASS relatado: 132 passed, 1 skipped, 15/15 frontend | Revalidar quando SHA mudar em código afetado | SHA, comando local, código de saída, relatório sanitizado |
| `release_probe.py`, AUD-01, SEC-01 | PASS relatado no lab sintético | Não equivale a validação externa | JSON sanitizado e banco/schema TEMP |
| SEC-02 e SEC-03 UI | PASS relatado (revogação/restauração) | Proteger contra regressão | Evidência da rodada |
| UX-06 paginação, UX-07 teclado no histórico | PASS relatado | Mantê-los no gate de regressão | Capturas e roteiro |
| **UX-08**: 1366×768 e 1920×1080 Histórico + Operador (desktop-only) | **PENDING HUMAN REVIEW** | **Bloqueia main** | Capturas em viewport estável, sem corte/overflow |
| **UX-02**: Supervisor N1/N2 | **NOT_RUN** | **Bloqueia main** | Evidência isolamentos e papéis |
| **UX-05**: N1→N2 | **NOT_RUN** na rodada final | **Bloqueia main** | Mensagens e notas internas segregadas |
| Diff/segredos/concorrência, PRs paralelos | PENDING | **Bloqueia main** | Review de diff integral e pareceres |
| Decisão formal de promoção | PENDING | **Bloqueia main** | Aprovação/justificativa/rollback e SHA |

**Nota sobre evidência:** valores acima vêm de documentação do próprio PR e não foram executados nesta revisão de portfólio. Não reinterpretar `BLOCKED` como `PASS` por medidas geométricas preliminares. A decisão do Product Owner de 19/10/2026 retirou o suporte mobile do escopo obrigatório; imagens mobile anteriores permanecem inválidas, não aprovadas. O desktop permanece sujeito a revisão de conteúdo e interatividade.

## 2. Procedimento obrigatório de QA

1. Usar apenas `start.cmd --lab --lab-dir <TEMP>` ou novo `start.cmd --lab`, com banco 006b4 exclusivamente sintético. Não iniciar modo normal para esses testes.
2. Registrar `run_id, SHA, persona, queue_id fictícia, cenário, browser, viewport real, PASS/FAIL, nota e captura sanitizada`.
3. Usar `docs/qa/PR-028-ui-final-gates.md` para roteiro e `docs/qa/PR-028-release-acceptance.md` para evidências de segurança.
4. Atualizar issue #29 com resultados, inclusive falhas e bloqueios; issue e PR podem divergir até revisão humana.
5. Revisar alcance no SHA final, código sensível, diff acumulado, migrações opt-in e README antes da decisão.
6. **Nunca promover automaticamente**, executar migração no SQLite original ou anexar credentials, tokens e conteúdo real.

## 3. Gate de publicação corporativa posterior e independente

| Pilar | SPEC | Estado inicial (2026-10-18) |
|---|---|---|
| SSO Entra ID/OIDC, autorização enterprise, app scopes | 014 | NÃO IMPLEMENTADO / NÃO HOMOLOGADO |
| SQL Server, lock concorrente, migrações e worker externo | 015 | NÃO IMPLEMENTADO / NÃO HOMOLOGADO |
| LGPD, retenção, legal hold, proteção de dados, WORM | 016 | POLÍTICA/IMPLEMENTAÇÃO PENDENTES |
| Teams Embedded real, ACK, DLQ e E2E | 012 | NÃO IMPLEMENTADO / NÃO HOMOLOGADO |
| Telemetria, SLA, DR, capacidade e carga | 013 | PENDENTE |
| Média/anexos seguros se habilitados | 011 | PENDENTE |

Todos os itens exigem avaliação de segurança e aceite próprios em ambiente autorizado. Mesclar a POC à main **não aprova nenhum item desta tabela**.
