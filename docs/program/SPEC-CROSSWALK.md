# Crosswalk — Legado, PRs e novas SPECs

## Preservação e reconciliação

- **Não reescrever retroativamente** specs em `docs/specs/`. O Spec Kit usa `specs/{id}-{slug}/` para features **novas**, com numbering coerente ao roadmap já divulgado; `.specify/feature.json` não será alterado por planejamento de várias SPECs.
- **Principal PR #28**: linha funcional POC-002, 003, 004, 005, 006A e 006B-1 a 006B-5.2, sem merge na main. O restante do roadmap não está implementado na branch base por criação destes arquivos.
- **PR #14**: RFC-006 e plano 006–013 propõem personas, administração, supervisão, monitoria, mídias e integração; são **propostas fora da linha principal**, e não devem ser consideradas código incorporado.
- **PR #15**: alternativa anterior para grants/migrações, não compor automaticamente na linha #16 + 006B.
- **PR #17**: desenho anterior 006B, potencial documentação redundante; conferir antes de eventual fechamento.
- **Original issue #2/#3/#4/#5/#6**: numeração de SPECs iniciais sobrepostas a incrementos POC; não fechá-las sem reconciliar critérios de aceite.

| Original | Interpretação histórica | Cobertura / próxima SPEC |
|---|---|---|
| SPEC-001 | Fundações, arquitetura, canal ownership | Preservada; marco POC #1 |
| SPEC-002 / POC-002 | Core SQLite/FastAPI/React | PR #7; integra via #28, 006C decide main |
| SPEC-003 | Adapter Embedded na concepção inicial | **012** detalha protocolo, identidade, inbox/outbox, ACK e E2E |
| POC-003 | Mesa/operador e transferência N1→N2 | PR #9, regressão obrigatória no 006C |
| SPEC-004 | Workspace operador/supervisor | POC-004 PR #11 existente; futuro **008** e **018** não duplicam implementação |
| SPEC-005 | App Teams Native e segundo canal | Futuro **017**, somente depois do Embedded 012 |
| POC-005 | RBAC demo, auto-despacho | PR #13, regressão obrigatória |
| SPEC-006 | SLA/Finesse/resiliência na concepção inicial | **013** (métricas/SRE), **015** (resiliência), **016** (retention) e Finesse condicionado a ADR futuro |
| SPEC-006A / 006B | Grants/proveniência/auditoria de leitura e decisões | PRs #16–#27 e integração #28, gate 006C |
| RFC-006 / PLAN-006–013 | Proposta enterprise lateral | Reconciliada como hipótese no portfólio 007–013; 014–018 tratam pré-requisitos não isolados no RFC |

**Política:** evitar colisão de nomenclatura: rotular ticket como `SPEC-0xx` ou `POC-0xx` e usar o link exato. Futuros PRs devem mencionar issue e feature folder; o caminho `specs/` só representa a carteira futura, não aprovação do RFC paralelo.
