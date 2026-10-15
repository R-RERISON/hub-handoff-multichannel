# Plano de desenvolvimento

| Fase | Entrega | Gate |
|---|---|---|
| SPEC-001 | Constituição, ADR, API proposta, domínio puro, CI | Revisão da arquitetura e testes |
| SPEC-002 | SQL Server, Auth, sessões, inbox/outbox, filas e despacho atômico | Concorrência, isolamento e recuperação |
| SPEC-003 | Adapter Python/Tornado para Teams Embedded | Handoff bidirecional E2E em homologação |
| SPEC-004 | Workspace operador, cockpit e administração React | SSO, RBAC, UX e testes de operação |
| SPEC-005 | Novo bot Teams Native e conectores adicionais | Dois bots heterogêneos, mesma central |
| SPEC-006 | SLA, telemetria, Finesse, CSAT, observabilidade e DR | Gates de resiliência/carga/segurança |

## Primeiro fluxo vertical
Usuário no Bot CSTI -> adapter chama Hub -> fila -> operador assume no workspace -> operador responde -> adapter envia como Bot CSTI -> usuário responde -> adapter encaminha ao Hub -> operador encerra -> bot retorna ao fluxo automatizado.

A base deve ser implementada por gates, sem duplicar regras de negócio do Tornado atual. Não definir datas de entrega sem estimativa de equipe e capacidade real.
