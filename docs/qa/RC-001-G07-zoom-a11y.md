# RC-001 / G07 — Correção controlada de acessibilidade com zoom 200%

**Base:** PR #51 / commit `20ff982444310ef5c7dbce15d9d208ee0c1724b0`.  
**Entrega:** hotfix em `fix/rc001-g07-zoom-a11y`, não integrado à baseline RC-001.  
**Status:** CODED / QA_WINDOWS_NOT_RUN / BROWSER_RETEST_REQUIRED / NO_MERGE.

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
