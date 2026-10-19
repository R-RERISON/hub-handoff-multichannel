# Contrato realmente implementado — POC v0.2

Este documento descreve a API executável em localhost. O contrato docs/contracts/openapi.yaml representa uma arquitetura futura e **não é a especificação exata da POC**.

Autenticação local em toda rota /v1: header `X-POC-Key` igual ao segredo de ambiente `HANDOFF_POC_KEY`. Nenhum papel/autorização corporativa. Não publicar fora de localhost.

| Verbo e rota | Ação |
|---|---|
| GET /health/live | Processo vivo, sem autenticação |
| GET /health/ready | 503 sem chave; com chave, prontidão limitada à POC |
| POST /v1/demo/bootstrap | Cria operação, fila, bot e operadores fictícios |
| GET /v1/queues | Filas e número de solicitações aguardando |
| GET /v1/operators | Operadores, presença e capacidade ativa |
| PATCH /v1/operators/{id}/presence | Define AVAILABLE, AWAY ou OFFLINE |
| POST /v1/handoffs | Criar sessão; requer Idempotency-Key |
| GET /v1/handoffs | Até 200 atendimentos mais recentes |
| POST /v1/dispatch/next | Distribuição manual do mais antigo da fila |
| GET /v1/handoffs/{id}/messages | Mensagens da sessão |
| POST /v1/handoffs/{id}/messages | Recebe USER ou OPERATOR, deduplica ID externo |
| GET /v1/outbox | Inspeciona resposta de operador pendente de adapter |
| POST /v1/handoffs/{id}/close | Encerramento idempotente de sessão ativa |

## Exemplo

```bash
curl -X POST http://127.0.0.1:8000/v1/handoffs  -H "X-POC-Key: CHAVE-LOCAL" -H "Idempotency-Key: demo-key-00000001"  -H "Content-Type: application/json"  -d '{"external_conversation_id":"teste-1","requester_label":"Cliente simulado","subject":"Acesso"}'
```

O retorno é 201 com sessão QUEUED; se repetido com mesmo payload retorna mesma sessão, se payload incompatível retorna 409. A atribuição manual pode produzir assigned, empty_queue ou no_operator_available.

## Notas de segurança
- A POC permite que quem conhece a chave simule os dois lados da conversa; não serve para ambientes compartilhados.
- Não inserir nomes, mensagens ou identificadores pessoais reais.
- Idempotência de mensagens: (session_id, external_message_id).
- Outbox com PENDING_ADAPTER não implica envio nem entrega de mensagem real.
