# SPEC-018 — Análise preliminar de coerência e dependências

**Resultado:** PRELIMINARY_STATIC_ANALYSIS / NOT_AN_OFFICIAL_SPECKIT_ANALYZE / DO_NOT_IMPLEMENT_YET
**Referências revisadas:** CONSTITUTION.md, .specify/memory/constitution.md, SPEC-006C, SPEC-010, SPEC-018, frontend de PR #59 e relatório de discovery 21/10/2026.
**PO:** duas decisões aprovadas expressamente em 21/10/2026 (Q1/A e Q2/A); não confundir com aprovação do release.

| ID | Severidade | Finding e resolução |
|---|---|---|
| AN-018-01 | CRITICAL para release | SPEC-006C FR-001 exige UX-08 com 390×844; SPEC-018 o torna exploratório **somente para feature**. Contratos separados com precedência, **sem waiver da 006C**. |
| AN-018-02 | HIGH segurança | SPEC-010 futura prevê papel MONITOR e coaching; FR-002 anterior da SPEC-018 mencionava portal Monitoria como existente. Removido do escopo implementável. Role/autorizações continuam exclusivos da SPEC-010. |
| AN-018-03 | HIGH integração | PR #59 é Draft sobre PR #57 e tem regressão/liveness própria, não pertence à branch documental. T005 bloqueia runtime antes da escolha explícita de SHA. |
| AN-018-04 | HIGH governança | Discovery local alterou spec.md na worktree sem commit; texto do git diff local não está disponível no GitHub. Branch nova contém decisões aprovadas e deverá passar por reconciliação manual, sem reset/checkout destrutivo. |
| AN-018-05 | MEDIUM UX | CSS contém regras longas por shell, tokens pontuais e breakpoints 530/620/700/780/820/1000/1350px; padronização incremental com regressão G07 é preferível a rewrite. |
| AN-018-06 | MEDIUM A11y | Frontend já tem alertdialog, labels, regiões focáveis e avisos; preservar esses contratos enquanto medir foco, contraste, actionability e movimento reduzido. |
| AN-018-07 | HIGH dados | Histórico VERIFIED segmentado e revoke são contratos backend; UI deve limpar stale de imediatamente e descartar respostas atrasadas, jamais simular grant visual. |
| AN-018-08 | MEDIUM confiabilidade | Lifecycle CAS e mutações N1→N2 não podem sofrer retry automático após timeout; reconciliar retorno e estado persistido. |
| AN-018-09 | HIGH evidências | Desktop@200% aprovado em PR histórico não transfere PASS à SPEC-018 nem ao PR #59; screenshot/regressões devem carregar SHA real. |

## Próximas análises obrigatórias
1. Revisão Arquitetura/Segurança formal da SPEC e dependências (T004).
2. Reconciliação do diff local do discovery (T001).
3. Seleção do HEAD de runtime e revisão de PR #59/Issue #58 (T005).
4. Comandos oficiais /speckit-plan /speckit-tasks /speckit-analyze no ambiente que tem Spec Kit; este relatório **não** os substitui.
5. Implementação por blocos U1/U2/U3 + testes Windows, G09 independente, G10 humano; sem merge automático.

**Proteções:** nenhum segredo, PII, SQLite, API, CSS de runtime ou branch QA foi alterado nesta proposta documental.
