# UX-002 — Pós-homologação: filtros, métricas e eficiência das consultas

Data: 2026-10-15 | Origem: capturas das telas Conversas, Filas e Operadores e log Uvicorn da POC.

## Evidências de homologação

- A jornada guiada foi concluída, com dois atendimentos encerrados.
- Os dois operadores aparecem disponíveis novamente.
- O log registra criação 201, mensagens 201, distribuição e encerramento 200, sem erro de backend observado.
- A outbox possui duas respostas PENDING_ADAPTER porque não existe conector Teams; isso não é entrega nem erro de encerramento.
- A interface realizava quatro GETs de contexto a cada 5 segundos, além das mensagens de sessão: alto volume de logs para um laboratório.

## Ajustes executados

1. GET /v1/dashboard consolida handoffs, queues, operators e contadores outbox sem devolver conteúdo de mensagens.
2. Frontend substitui quatro GETs por um snapshot periódico a cada 15s, suspenso com a aba oculta; mensagens de sessão são consultadas quando a conversa está aberta.
3. O menu Conversas mostra a quantidade de conversas exibidas (até 200 na POC), não somente as ativas.
4. Filtros de conversas Todas, Em atendimento, Na fila e Encerradas passam a filtrar a lista de verdade.
5. Indicação de outbox alterada para **Sem envio externo / Respostas sem envio**: encerramento não implica envio de mensagens ao bot.
6. Alertas de sucesso são descartados ao trocar de página.
7. Criar/atribuir atendimento seleciona a conversa pertinente mesmo que o filtro anterior a escondesse.
8. Teste automatizado: GET /v1/dashboard sem chave retorna 401; abertura, fila, atribuição, resposta, fechamento e contagem de outbox.

## Limites preservados

- Banco e tabelas SQLite permanecem inalterados; sem migração.
- POC em localhost com chave compartilhada. Sem identidades individuais ou adapter Teams.
- O dashboard contém até 200 sessões recentes; não é histórico completo nem relatório analítico.
- O endpoint consolida chamadas HTTP, mas requer medição de latência/carga em cenários maiores.

## Checklist no VS Code

No PowerShell, na raiz:

    git status --short
    git switch feat/002-sqlite-poc
    git pull --ff-only origin feat/002-sqlite-poc
    .\start.cmd --check
    .\start.cmd

Verificar no browser:
- Botão Conversas exibe 2 quando existem dois atendimentos encerrados.
- Filtro Encerradas exibe ambos; Em atendimento exibe nenhum.
- Fila sem atendimento não permite distribuição.
- Respostas sem envio permanecem 2 enquanto não houver adapter; conclusão não retira itens da outbox.
- Rede/terminal passa a apresentar menos GETs, tipicamente /v1/dashboard em vez das quatro rotas separadas; mensagens são lidas apenas no workspace com sessão selecionada.
- Novas solicitações aparecem mesmo após o filtro Encerradas ter sido selecionado.

## Segurança e diagnóstico

O launcher exibe a chave local no terminal para login e o log foi compartilhado. Recomenda-se rotacionar a chave local e não anexar essa linha em próximos logs. Após encerrar os serviços, apagar data/.poc-key, remover eventual variável HANDOFF_POC_KEY e iniciar novamente. Essa medida **não** equivale a autenticação corporativa.

## Próximo passo funcional

Separar workspace de operador e administração/supervisão; modelar ofertas/aceites/recusas/transfers e permissões, antes de conectar canais reais.
