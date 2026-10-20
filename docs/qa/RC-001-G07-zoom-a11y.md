# RC-001 / G07 — Correção controlada de acessibilidade com zoom 200%

**Base:** PR #51 / commit `20ff982444310ef5c7dbce15d9d208ee0c1724b0`.  
**Entrega:** hotfix em `fix/rc001-g07-zoom-a11y`, não integrado à baseline RC-001.  
**Status:** CODED / QA_NEW_HEAD_NOT_RUN / BROWSER_RETEST_REQUIRED / NO_MERGE.

## Evidência de origem: rodada visual informada pelo executor

O executor informou, no Windows com navegador integrado, frontend/API HTTP 200,
worktree limpa em `20ff982444310ef5c7dbce15d9d208ee0c1724b0`, SQLite sintético em TEMP e nenhuma alteração na
POC original. Reportou 173 testes aprovados, 1 skipped, Ruff,
arquitetura frontend, TypeScript, Vite e release probe aprovados no SHA original,
além de cenário B1.0 (2 filas, 2 operadores, 5 contas) e isolamento visual.
Isso **não é evidência de testes desta nova branch**. As capturas estavam
visíveis na conversa original, não foram anexadas ou inspecionadas diretamente
neste commit.

Falhas G07 reportadas em zoom 200%:
1. CSS ocultava o botão **Ativar alertas** ao atingir viewport <=780px.
2. Tabelas da Administração forçavam 1040px de largura mínima sem contêiner
   focável por Tab nem instrução de rolagem horizontal.

## Correção de escopo estrito
- Remover regra de ocultação de alertas do breakpoint compacto e manter
  a seção superior ajustável à altura real dos controles; botão permanece
  visível, inclusive quando notificações não são suportadas (nesse caso,
  continua desabilitado pela lógica preexistente).
- Manter todas as colunas de Administração; três contêineres de rolagem
  recebem role=region, aria-label, aria-describedby e tabIndex=0.
- Exibir instrução de teclado, reforçar scrollbar e foco visível.
- Dois testes de arquitetura frontend para os contratos G07.
- Sem alteração de API, autenticação, autorização, banco, migração,
  fluxo de atendimento, configuração de deploy ou tokens.

## Gate de revisão na nova branch
1. Conferir HEAD do hotfix e worktree TEMP nova, sem reaproveitar o diretório
   detached congelado da RC-001.
2. `./start.cmd --check` em Windows no SHA **final do hotfix**; registrar exit 0
   e total atualizado de testes, Ruff, TypeScript e Vite.
3. Abrir `./start.cmd --lab` em laboratório sintético **novo**, ou retomar
   laboratório antigo somente se a revisão de schema for compatível e não
   houver dados reais. Não executar `start.cmd` sem `--lab`.
4. Operador Ana, 1366x768 e 1920x1080, 100%/200% zoom real:
   Ativar alertas visível, acessível com Tab e sem recorte; quando o navegador
   não oferecer Notification, conferir controle visível mas disabled.
5. ADMIN 1366x768 e 1920x1080, 100%/200% zoom real:
   Tab alcança região das filas e **ambas** as regiões de pessoas; foco visível,
   setas percorrem horizontalmente até as últimas colunas, sem perda de dados
   e sem overflow do documento inteiro.
6. Conferir Mesa com oferta N1, diálogo de aceitação, mensagens e transferência
   N1→N2, pois altura do cabeçalho mudou no layout compacto.
7. Anexar capturas sanitizadas, dimensões reais, SHA e resultados G07.
8. Revisar diff de segurança e aprovação explícita antes de incorporar o hotfix
   ao candidato RC-001. Se incorporado, novo SHA RC-001 exige gate atualizado.

## Estado dos gates históricos
G00, G01 e G06 no commit original foram reportados PASS pelo executor.
G07 original foi reportado FAIL; G02, G05 parciais e demais pendentes.
**Nenhum gate foi aprovado automaticamente para a revisão hotfix.**

## Rollback
Abandonar branch/PR do hotfix; RC-001 `20ff982444310ef5c7dbce15d9d208ee0c1724b0` continua imutável.


## Reteste Windows informado em 20/10/2026 — snapshot anterior do hotfix

**SHA:** `5174bfbaf8454140d6f4de9284f0cd6b0dd9bb81`.
Executor relatou `start.cmd --check`: **173 Python PASS, 1 SKIP, Ruff,
19 arquitetura frontend, TypeScript e Vite PASS**. No browser integrado,
viewport real 1366×768 e 1920×1080 a 100%/200%: botão **Ativar alertas**
visível, focável por Tab, três tabelas focáveis e rolagem por setas até a
última coluna. Fluxo sintético N1→N2, com aceite, mensagens e encerramento,
concluído. Tudo isso **pertence exclusivamente ao SHA acima** e não comprova
a correção adicional feita depois.

### Issue #53 — correção adicional na mesma linha de estabilização

**Causa:** `desk-feedback` usava `position:absolute` dentro do painel
da Mesa, com os filhos `pointer-events:auto`. Um aviso de sucesso
sobrepunha-se ao botão **Encerrar**, impedindo o clique até o aviso
ser dispensado.

**Remediação:** aviso inserido no fluxo flex (sem posição absoluta ou
coordenadas de sobreposição), com espaço próprio, limite de altura e
rolagem vertical **do próprio aviso** quando necessário; botão de dispensa
com nome acessível; preservados `role=status`, `aria-live` e lógica de
notificações. Os avisos não encobrem botões operacionais nem exigem
fechamento para executar ações.

**Impacto esperado:** o painel de atendimentos perde temporariamente a
altura ocupada pelo aviso (sem bloqueio por camada visual). Layout compacto
com zoom 200% e altura baixa deve ser verificado para não ocultar o
compositor, menu de transferência ou botões ativos.

**Testes novos:** dois contratos de arquitetura frontend (não substituem
Playwright/manual na aplicação real).

### Protocolo para o SHA FINAL do PR #52 (PENDENTE)

- [ ] Confirmar `git rev-parse HEAD` com SHA final, worktree limpa.
- [ ] `.\\start.cmd --check` retorna exit 0; anotar contagem nova.
- [ ] `.\\start.cmd --lab --lab-dir "<TEMP do laboratório validado>"`
  ou criar laboratório TEMP novo, jamais iniciar POC original.
- [ ] Operador N1: criar ticket sintético, aceitar a oferta e enviar uma
  mensagem para exibir o aviso `Resposta registrada...`.
- [ ] **Sem dispensar o aviso:** com mouse clicar **Encerrar**; verificar
  estado persistido `CLOSED` e que a ação não ficou bloqueada.
- [ ] Repetir o teste antes de encerrar usando **Transferir** enquanto
  o aviso estiver visível, em outra sessão sintética.
- [ ] Validar close `Dispensar aviso` por Tab/Enter e que fechar aviso
  **não** execute ação de atendimento nem altere sessão.
- [ ] Repetir a 1366×768 e 1920×1080, zoom real 100%/200%;
  `getComputedStyle(feedback).position === 'static'`, ausência de
  interseção geométrica entre feedback e botões operacionais,
  compositor/chats alcançáveis e sem overflow horizontal do documento.
- [ ] Revalidar G07 original: Ativar alertas visível, três tabelas
  focáveis e navegáveis com setas.
- [ ] Sanitizar screenshots e logs; não compartilhar tokens/senhas.
- [ ] Manter PR #52 Draft, RC-001 original e main sem merge até aceite.

**Status após código da #53:** CODED / HOTFIX_NEW_SHA_QA_NOT_RUN /
BROWSER_RETEST_REQUIRED / NO_MERGE.

## Reteste Windows — 20/10/2026 — Issue #53 resolvida

**SHA testado:** `d6d044f2980a09bf0ed8971ccedbbb2694d4042e`.
O executor informou PASS: `start.cmd --check` (173 testes Python, 1 skipped,
21 frontend, Ruff, TypeScript, Vite); `release_probe.py` PASS;
feedback `position:static` sem interseção e cliques em **Transferir** e
**Encerrar** bem-sucedidos com aviso visível. Browser 1366×768 e 1920×1080,
100%/200% real; 2 conversas QA concluídas CLOSED, sem ofertas pendentes.
A evidência pertence ao SHA acima e foi registrada na Issue #53, fechada
como concluída; a RC-001 original continua separada e sem merge.

## Issue #54 — diálogo de oferta com botões fora da viewport (200%)

**Achado no SHA d6d044f:** em 1366×768, zoom real 200%, `Aceitar
atendimento` ficou fora da viewport e o clique do Playwright falhou com
`element is outside of the viewport`. O operador conseguiu aceitar por
Enter (teclado). O problema é diferente do feedback de status (#53).

**Correção nesta nova revisão do PR #52:**
- Dialog de oferta com `max-height:calc(100dvh - 36px)`, flex vertical e
  `overflow:hidden`. Preserva margem externa de 18px do overlay.
- Conteúdo informativo e nota interna dentro de `offer-dialog__body`
  rolável por teclado (`role=region`, `tabIndex=0`, foco visível).
- `offer-dialog__buttons` fora do conteúdo rolável, com `flex:0 0 auto`:
  botões **Aceitar atendimento** e **Recusar** permanecem visíveis;
  preserva pilha de botões no breakpoint <=700px.
- Dois novos testes de arquitetura frontend. Nada alterado no backend,
  autenticação, dispatcher, schema, credenciais ou SQLite.

### Gate necessário no SHA FINAL (QA AINDA PENDENTE)

- [ ] Confirmar o SHA novo do PR #52 e worktree isolada limpa.
- [ ] `.\\start.cmd --check` (novo total frontend esperado: **23**).
- [ ] `.\\.venv\\Scripts\\python.exe scripts\\release_probe.py`.
- [ ] Novo laboratório sintético ou o laboratório anterior já validado;
  jamais iniciar `start.cmd` sem `--lab`.
- [ ] **1366×768 com 200% REAL**: gerar oferta N1 e confirmar `Aceitar`
  e `Recusar` inteiros dentro da viewport, clique real com mouse, sem
  `element is outside of the viewport` ou JS `element.click()`.
- [ ] Confirmar botões visíveis **antes de qualquer interação de rolagem**;
  leitor/teclado deve conseguir focar o container `Detalhes da oferta`,
  rolar a nota por setas e avançar aos botões com Tab.
- [ ] Testar uma transferência N1→N2 com nota interna sintética longa;
  ações permanecem clicáveis com a nota dentro do dialog.
- [ ] Repetir em 1366×768 e 1920×1080 com zoom 100% e 200%; medir DPR,
  `innerWidth`, `innerHeight`, bounding boxes de botões/dialog, sem
  overflow horizontal do documento.
- [ ] Revalidar regressão #53: toast visível sem cobrir Encerrar/Transferir
  e foco no botão Dispensar aviso.
- [ ] Revalidar Ativar alertas em zoom 200% e as três tabelas ADMIN.
- [ ] Registrar capturas sanitizadas, SHA e notas no PR #52; somente com
  a aprovação formal incorporar hotfix à RC-001.

**Estado:** ISSUE54_CODED / NEW_SHA_QA_NOT_RUN / PR52_DRAFT /
RC001_FROZEN / MAIN_UNCHANGED.
