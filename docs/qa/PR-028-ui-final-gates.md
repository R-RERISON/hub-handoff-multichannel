# PR #28 — Gates visuais e funcionais finais (006B / POC 0.5)

**Escopo:** somente laboratório `start.cmd --lab --lab-dir <TEMP>`. Não usar
`start.cmd` sem `--lab` para estes cenários. Registrar achados concretos,
sem simular aprovação pela mera presença de um componente no código.

## Pré-condições

- Um terminal permanece com `start.cmd --lab --lab-dir <TEMP>` ativo.
- API `127.0.0.1:8000` e frontend `127.0.0.1:5173` acessíveis; caminho do
  laboratório exibido deve ser o mesmo dos utilitários de QA.
- Duas janelas isoladas de navegação (normal e privada ou perfis separados)
  para impedir reuso acidental do token entre Auditor, Supervisor e Operador.
- Usar somente conversas/mensagens sintéticas. Nunca incluir senhas,
  tokens, IDs completos de pessoas ou conteúdo histórico real em capturas.

## Matriz de aceitação manual

| Gate | Ação reproduzível | Condição de aprovação | Evidência |
|---|---|---|---|
| SEC-03 / UI | Como Auditor, após `restore=PASS`, clicar `Atualizar permissões` | N1 reaparece e histórico N1 fica consultável; N2 ausente | Captura do seletor N1 e do detalhe sintético |
| SEC-01 | Com Auditor N1, tentar consultar detalhes de N2 por requisição autenticada no laboratório, sem alterar grants | HTTP 404 sem conteúdo nem identificação de sessões N2 | Apenas status e nome do cenário, nunca token/response body |
| UX-02 | Como Supervisor, alternar N1/N2 | Segmentos filtrados por fila; nenhuma ação de Operador disponível | Capturas de cada fila |
| UX-05 | Criar atendimento sintético N1, transferir N1→N2, gerar mensagem posterior em N2 | Histórico N1 não contém mensagem N2; N2 não contém mensagem N1; nota privada não entra em VERIFIED | Captura sintética de ambos os perfis |
| UX-06 / A | Gerar >1 página de sessões na mesma fila e acionar Próxima/Anterior | Indicação de página correta; botão Próxima desabilitado na última; detalhe anterior não persiste após troca | Capturas página 1 / 2 |
| UX-06 / B | Gerar >1 página de mensagens, alternar somente paginação de mensagens | Eventos continuam na mesma página; mensagens avançam e voltam sem duplicidade | Página de mensagens e eventos visíveis |
| UX-06 / C | Gerar >1 página de eventos, alternar somente paginação de eventos | Mensagens permanecem na página corrente; eventos avançam e voltam sem duplicidade | Página de eventos e mensagens visíveis |
| UX-07 | Tab e Shift+Tab em seletor, atualização, tickets, paginação; Enter/Space nos botões | Ordem lógica; foco visível; botões desabilitados não recebem ação indevida; nenhum controle essencial inacessível | Navegador/resolução e observações |
| UX-08 / 390 | DevTools → largura 390 px; navegar em Histórico Verificado e Mesa do Operador | Sem scroll horizontal da página; botões e textos não cortados; áreas internas roláveis | Captura da largura e interface |
| UX-08 / 1366 | DevTools ou monitor em 1366×768 | Conteúdo e ações disponíveis sem sobreposições; scroll gerenciável | Captura |
| UX-08 / 1920 | DevTools ou monitor em 1920×1080 | Espaçamento e painel lateral equilibrados; sem painéis vazios desproporcionais | Captura |
| AUD-01 | `python -m scripts.release_audit_evidence --lab <TEMP>` | `result=PASS` e quatro gates internos PASS (ou listar pendências reais) | JSON sanitizado |

### Observações necessárias

Paginação >1 página exige **massa sintética suficiente**; ausência de dados
não é aprovação nem falha. Registrar `NOT_RUN_NO_FIXTURE` e preparar dados
descartáveis somente pelo Laboratório/API sintética quando necessário.
Testes de teclado/responsividade **não** são cobertos pelos 13 testes estáticos
de arquitetura frontend; exigem execução real no navegador, ou posterior
automação E2E.

Não usar DevTools para copiar o conteúdo de `Authorization`. O backend
sempre decide autorização; ocultar opção de N2 no seletor é uma confirmação
de UX, não substitui o HTTP 404 de SEC-01.

## Protocolo de evidências e regressões

Um gate recebe `PASS`, `FAIL`, `BLOCKED` ou `NOT_RUN`, com: data,
commit, navegador, viewport, papel autenticado, cenário de teste, resultado
observado e referência à captura (sem segredos). Toda falha de segurança ou
vazamento cross-queue impede release, mesmo com build verde.

Se um gate falhar, abrir correção específica e repetir:
`start.cmd --check`, `release_probe.py`, cenário negativo de RBAC e
reteste visual pertinente. Não aprovar `main` automaticamente.

## Próxima fronteira depois do PR #28

O fechamento dos gates de POC não representa pronto para ambiente
corporativo. Permanecem por fase: identidade corporativa Entra ID/OIDC,
modelo de isolamento multioperação, SQL Server com estratégia transacional
própria, observabilidade/retencão de logs, workers de entrega/outbox e
adapter Teams Embedded com ACK e reconciliação.
