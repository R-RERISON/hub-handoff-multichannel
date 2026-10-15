# POC-003 — Operação humana com oferta, aceite, recusa e transferência

Data: 2026-10-15 | Status: IMPLEMENTED / AWAITING LOCAL VALIDATION

## Contexto

O usuário validou o ciclo anterior de criação, distribuição direta, mensagens e encerramento. A evolução desta etapa constrói a operação **oferta / aceite / recusa** com uma mesa independente de atendimento. O bot originador da conversa continua fora da operação humana.

Este incremento preserva o fluxo de demonstração antigo `POST /v1/dispatch/next` para regressão, mas apresenta o **novo caminho recomendado** usando `POST /v1/dispatch/offer`.

## Fluxo funcional

1. **Conversas:** crie uma solicitação fictícia (estado QUEUED).
2. **Filas:** clique Ofertar próximo na fila Suporte N1. O backend seleciona operador com presença AVAILABLE e capacidade livre; fica OFFERED.
3. **Mesa do Operador:** selecione Ana ou Bruno conforme a oferta. Aceite para ACTIVE ou recuse para QUEUED.
4. **Atendimento:** troque mensagens em simulação local. Resposta humana fica na outbox com status PENDING_ADAPTER (nada é enviado ao Teams).
5. **Transferência:** envie para Suporte N2, informando o motivo. O operador libera capacidade, o atendimento retorna QUEUED em N2 e a trilha é gravada.
6. **Nova oferta em N2:** o supervisor oferta a fila N2 ao operador Bruno. Aceite e conclua.
7. **Encerramento:** operador responsável conclui o atendimento; capacidade é liberada. A outbox não é marcada como entregue.

## Modelo de dados aditivo

| Tabela | Descrição |
|---|---|
| `handoff_offers` | Cada oferta com operador, prazo, estado PENDING/ACCEPTED/DECLINED/EXPIRED e data da decisão |
| `session_transfers` | Histórico de origem/destino, operador anterior, motivo e horário |
| `session_events` | Trilha existente ampliada: OFFERED, ACCEPTED, DECLINED, OFFER_EXPIRED, TRANSFERRED, CLOSED |

As duas novas tabelas são criadas automaticamente pelo `Base.metadata.create_all` na POC; **não há upgrade de colunas existentes nem migração de dados legados**. Essa estratégia de bootstrap não substitui o Alembic planejado.

## Contrato implementado

| Método/Endpoint | Uso |
|---|---|
| POST /v1/dispatch/offer | Cria uma oferta para o primeiro ticket QUEUED elegível |
| GET /v1/operators/{operator_id}/work | Ofertas e atendimentos ativos do operador |
| POST /v1/handoffs/{id}/accept | Aceita uma oferta pendente; corpo `{"operator_id":"op-ana"}` |
| POST /v1/handoffs/{id}/decline | Recusa a oferta, liberando capacidade |
| POST /v1/handoffs/{id}/transfer | Transfere sessão ativa, com operator_id, queue_id e reason |
| POST /v1/operators/{operator_id}/handoffs/{id}/close | Encerramento verificando responsabilidade da sessão |
| POST /v1/offers/expire | Expiração manual de ofertas vencidas, para a POC |
| GET /v1/handoffs/{id}/timeline | Eventos e transferências auditadas |

Os endpoints são autenticados **apenas pela chave de POC compartilhada**; o seletor de operador representa identidade fictícia, não é SSO nem autorização individual. **Não publicar fora de localhost.**

## Políticas temporárias

- Prazo da oferta: 120 segundos.
- Recusa: operador que recusou não recebe a mesma oferta por 120 segundos.
- Capacidade: soma de ofertas em aberto (OFFERED) e atendimentos ativos (ACTIVE).
- Operador precisa estar AVAILABLE e participar da fila.
- O mecanismo atual de reavaliação de expiração é acionado pelo novo dispatcher e pela operação explícita POST /v1/offers/expire; ainda **não existe worker durável**.
- O operador não pode aceitar oferta vencida, atender em fila não autorizada ou transferir atendimento de outra operação.
- Retentativas indevidas resultam em erro 409 e não duplicam efeitos.

## Gaps conhecidos

1. Sem RBAC/Entra ID: os endpoints legados ainda usam chave compartilhada; não tratar como segurança de produção.
2. Sem Alembic: esquema incremental via create_all é somente POC descartável.
3. Sem inbox/outbox worker ou ACK externo: mensagens continuam sem entrega ao Teams.
4. Sem controle de autorização por perfil nos endpoints antigos de demonstração.
5. Sem operação em rede ou multi-instância: SQLite BEGIN IMMEDIATE oferece serialização do escritor local; a estratégia SQL Server será outra.
6. Sem redirecionamento direto operador-para-operador; esta fase transfere para fila.
7. Sem horários, SLAs, turnos ou skill-based routing.

## Homologação pelo VS Code

Fechar o inicializador anterior (Ctrl+C), fazer backup do SQLite antes de atualizar se desejar preservar o estado de demonstração e executar:

```powershell
git status --short
git switch feat/003-operator-workflow
git pull --ff-only origin feat/003-operator-workflow
.\start.cmd --check
.\start.cmd
```

No navegador: Conversas → Nova solicitação → Filas → Ofertar próximo (N1) → Mesa do Operador → Selecionar identidade → Aceitar → Simular conversa → Transferir para N2 → Filas → Ofertar N2 → Mesa do Operador (Bruno) → Aceitar → Encerrar.

**Não utilizar GitHub Actions.**

## Gates de testes propostos

- Execução dos testes locais existentes.
- Testes novos: oferta concorrente/sem sobrealocação, operador errado, aceite duplicado, recusa, transferência e trilha, expiração, controle de capacidade entre modo direto e nova oferta, encerramento vinculado a operador.
- Build TypeScript + Vite da nova Mesa do Operador.
- Revalidação manual no navegador e observação dos estados no SQLite.

**Nota:** a implementação está publicada para testes; nenhum gate da nova etapa será reportado como aprovado até confirmação de execução.
