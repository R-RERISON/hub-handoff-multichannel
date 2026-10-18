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

## Preparar massa de UX-06 somente no laboratório descartável

Depois de aprovar `start.cmd --check` no commit candidato, mantenha
`start.cmd --lab --lab-dir $lab` executando **no mesmo TEMP** em um terminal.
No outro terminal execute:

```powershell
$lab = Join-Path $env:TEMP 'handoff-qa-006b4-1ohg0707'
.\.venv\Scripts\python.exe -m scripts.release_ui_pagination_fixture --lab $lab --confirm-synthetic
if ($LASTEXITCODE -ne 0) { throw 'Fixture UX-06 reprovada' }
```

O runner valida a revisão 006b4, a estrutura, as contas demo,
o escopo N1/N2 e a identidade da API local **antes de qualquer criação
de dados**. Todos os POSTs pertencem exclusivamente ao SQLite TEMP
validado, sem chamadas mutáveis à API ao vivo. Ele cria 27 atendimentos
de QA, 27 mensagens no último atendimento e 27 eventos de teste
identificados **`QA_PAGE_EVENT`** (marcados como sintéticos e associados
ao segmento por `ProvenanceRecorder`). Esses eventos **não são ações
operacionais reais**; servem apenas para validar a paginação visual.

A saída não inclui IDs, tokens ou conteúdo, e só retorna `PASS` se
a API do banco sintético comprovar segunda página para sessões, mensagens
e eventos, com controles de página independentes. Executar novamente
**acrescenta nova massa sintética**; não limpa dados existentes.

Após o PASS, entre como `auditor.demo`, abra
Supervisão → Conversas → Segmentos verificados e clique em
`Atualizar permissões`. Na N1, teste página 1/2 de sessões e selecione
o **último atendimento sintético criado** (deve estar na página 1,
entre os mais recentes); nesse atendimento, teste as páginas 1/2 de
mensagens e eventos separadamente. Verifique que o painel não mostra
itens da página anterior enquanto a nova está carregando, e que os
botões `Anterior`/`Próxima` ficam bloqueados nos limites.

**Aprovação de backend da fixture não equivale à aprovação visual.**
Documentar resultado e viewport de cada cenário. Não executar o comando
fora do laboratório descartável; não utilizar o SQLite POC original.

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
Testes de teclado/responsividade **não** são cobertos pelos 14 testes estáticos
de arquitetura frontend; exigem execução real no navegador, ou posterior
automação E2E.

Não usar DevTools para copiar o conteúdo de `Authorization`. O backend
sempre decide autorização; ocultar opção de N2 no seletor é uma confirmação
de UX, não substitui o HTTP 404 de SEC-01.

## Protocolo de evidências e regressões

### Ajuste UX-06: eventos volumosos sem cortar controles

Invariante: as duas paginações do detalhe permanecem dentro do painel limitado;
o volume de eventos não pode empurrar a paginação inferior para uma região
recortada por `overflow:hidden`. A área de eventos tem rolagem interna, foco
visível e nome acessível, sem alterar dados, autorização ou páginas da API.

Aceite: com 25 eventos na primeira página, o painel não tem conteúdo recortado,
ambas as paginações podem ser acionadas com mouse e teclado e a região
`Eventos comprovados` pode ser rolada pelo teclado. Validar geometria no
navegador real, além do contrato estático frontend e de `start.cmd --check`.

Um gate recebe `PASS`, `FAIL`, `BLOCKED` ou `NOT_RUN`, com: data,
commit, navegador, viewport, papel autenticado, cenário de teste, resultado
observado e referência à captura (sem segredos). Toda falha de segurança ou
vazamento cross-queue impede release, mesmo com build verde.

Se um gate falhar, abrir correção específica e repetir:
`start.cmd --check`, `release_probe.py`, cenário negativo de RBAC e
reteste visual pertinente. Não aprovar `main` automaticamente.

## Execução local Windows — 2026-10-18

Base `6da3061`, branch `feat/006b5b-security-decisions-journal`, mais a
correção de rolagem descrita acima, entregue nesta branch.
Somente o laboratório TEMP retomado pelo launcher; banco original preservado.
Navegador integrado do VS Code: Chromium 150 / Electron 43, Windows.
Papel autenticado nos cenários abaixo: `auditor.demo`.

| Cenário | Resultado | Observação executada |
|---|---|---|
| Regressão após correção | PASS | 132 Pytest aprovados, 1 ignorado; Ruff; 15/15 contratos frontend; TypeScript e Vite |
| Fixture UX-06 | PASS | 27 sessões, 27 mensagens e 27 eventos QA adicionados exclusivamente ao TEMP; API atestada |
| Release probe após correção | PASS | 22 tabelas 006b4, 2 leituras auditadas, 4 decisões; bloqueio entre filas, revogação, rollback, negativa 404 e ausência de conteúdo sensível nos journals |
| SEC-03 / UI | PASS | Revogar N1, atualizar permissões: filas e histórico removidos; restaurar N1 e atualizar: somente N1 reaparece e detalhe volta a ser consultável |
| UX-06 / A | PASS | Lista com 25 itens na página 1 e 3 na página 2; sem repetição; ida/volta preserva itens; limites desabilitados; detalhe removido ao trocar a lista |
| UX-06 / B | PASS | Mensagens 25/2; eventos permanecem na mesma página; retorno e limites conferidos |
| UX-06 / C | PASS | Eventos 25/3, incluindo o evento inicial além dos 27 eventos QA; página de mensagens não muda; retorno e limites conferidos |
| Conteúdo antigo durante fetch | PASS | Requisições de lista e detalhe retidas por 1 segundo no navegador; lista/detalhe antigos ausentes durante carregamento |
| UX-07 / histórico verificado | PASS | Tab, Shift+Tab, Enter e Space; ordem seletor/atualização/tickets/paginação; controles desabilitados ignorados; foco visível; eventos roláveis pelo teclado |
| Negativa autenticada de escopo | PASS | Requisição do Auditor para segmento N1 sob escopo não autorizado N2 retorna 404; sem divulgar token ou corpo. Não equivale ao cenário manual de selecionar um ID de sessão N2 |
| AUD-01 após revoke/restore | PASS | Quatro gates internos aprovados, Auditor com N1 sem N2, sem pendências; leitura read-only |
| UX-08 completo | BLOCKED | Medições de geometria disponíveis, mas capturas nas três resoluções e Mesa do Operador ainda não homologadas |
| UX-02 e UX-05 visuais | NOT_RUN | Alternância do Supervisor e transferência entre filas não reexecutadas nesta rodada |

Os testes interativos de paginação e as capturas usam viewport real
**1058×595**. Capturas sintéticas locais da sessão: `ux06-list-p1.png`,
`ux06-list-p2.png`, `ux06-detail-p2.png` e `ux06-controls-p1.png`; não são
arquivos versionados nem evidência de outras resoluções.

Defeito reproduzido antes da correção: em 1366×768, detalhe com altura útil
638 px e conteúdo de 761 px, recortado pelo painel. Depois da correção,
`scrollHeight = clientHeight = 638` em 1366×768 e 1920×1080; paginação de
eventos dentro do painel, eventos com rolagem interna e teclado funcional.
Em 390×844 foi medido `document.scrollWidth = 390`, com controles de histórico
dentro da largura. Essas medições **não aprovam UX-08**: a captura no navegador
integrado reajusta o viewport (por exemplo, de 390×844 para 274×595).
Repetir a inspeção visual em navegador com viewport estável, incluindo a Mesa
do Operador autenticada, antes de fechar o gate.

Rollback da correção: desfazer apenas as regras de dimensionamento/rolagem,
a região acessível de eventos e o contrato frontend correspondente desta
rodada, sem alterar backend, schema ou dados. Repetir `start.cmd --check` e
manter UX-06 bloqueado até novo reteste. Não há migração de banco a reverter.

A consulta ao PR #28 pelo conector GitHub retornou 404 nesta sessão; não foi
possível publicar um comentário com estas evidências no PR. As evidências
seguem versionadas nesta branch, sem merge nem mudança de estado do PR.
A `main` continua sem alterações.

## Próxima fronteira depois do PR #28

O fechamento dos gates de POC não representa pronto para ambiente
corporativo. Permanecem por fase: identidade corporativa Entra ID/OIDC,
modelo de isolamento multioperação, SQL Server com estratégia transacional
própria, observabilidade/retencão de logs, workers de entrega/outbox e
adapter Teams Embedded com ACK e reconciliação.
