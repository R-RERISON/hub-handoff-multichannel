# Registro de decisões, riscos e bloqueadores

**2026-10-18 | Estado proposto:** não declarar decisão técnica aprovada nesta alteração de documentação. Apenas inventário e recomendações passíveis de revisão.

| ID | Tipo | Fato / risco | Impacto | Mitigação / proprietário sugerido | Estado |
|---|---|---|---|---|---|
| R-001 | Release | PR #28 é Draft, muito extenso; QA UX-02/05/08 e diff incompletos | Alto | #29, reviewer arquitetura e QA, sem auto-merge | OPEN |
| R-002 | Segurança | SQLite POC original sem Alembic; adoção inadequada poderia corromper dados | Crítico | Somente laboratório TEMP 006b4; inspeção read-only | CONTROLADO / MONITORAR |
| R-003 | Autorização | Histórico segmentado e grants não garantem WORM, IAM ou produção | Crítico | 009,014,016; rastrear negações e journal | OPEN |
| R-004 | Arquitetura | Código centrado em SQLite single host não garante transação SQL Server nem worker multi-instância | Alto | 015, testes concorrentes multi-worker, revisão DBA | OPEN |
| R-005 | Canal | Mensagens PENDING_ADAPTER não têm entrega real Teams | Alto | 012, ACK/retry/DLQ e feature flag | OPEN |
| R-006 | Produto | Roadmap histórico com numeração e requisitos divergentes | Alto | Crosswalk, matriz única #42, reconciliação sem merge das branches laterais | IN_PROGRESS |
| R-007 | UX | Portais sem design system e responsividade final homologada | Alto | 018 e gate UX-08 obrigatório antes de main | OPEN |
| R-008 | Compliance | Retenção, dados reais e journal WORM não implementados | Crítico | 016, decisão formal DPO/security | OPEN |
| R-009 | Planejamento | Muitas features ativas geram PRs longos e dispersão | Médio | WIP ≤ 1 implementação crítica + 1 discovery paralelo | PROPOSTO |
| R-010 | Sequenciamento | 012 publicado antes de 014/015/016 amplia risco de vazamento e perda de mensagens | Crítico | Critical path e gates de produção independentes | OPEN |

## Decisions needed / ADR backlog

- **D-001**: Definir baseline de integração da POC e destino dos PRs empilhados/alternativos após UX e review; não decidir antecipadamente.
- **D-002**: Definir tenancy/operação, escopo de grants, papel MONITOR e extensão de catálogo de permissões da SPEC-007/010.
- **D-003**: Estratégia de SQL Server/locking + durable worker e migração da POC; sem tocar no banco original.
- **D-004**: Entra ID, identity binding e tenant policies para identidades humanas e serviço.
- **D-005**: Política LGPD/retention/legal hold/WORM e classificação real aprovada.
- **D-006**: Política de integração e capacidade Teams Embedded/Native, payload rich media, Finesse opcional.
- **D-007**: Padrões premium UX/a11y e instrumentos de gate visual reprodutível.

Cada decisão passa por issue/ADR com opções, trade-offs, autorização explícita, efeitos em SPECs e plano de reversão. Nenhuma política legal/enterprise será inventada pelo assistente.
