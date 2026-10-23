# SPEC-019 — Auditoria e homologação Premium UX

## Baseline e limites

- **Branch publicada**: `feat/spec018-ux-premium-batch-20261022`
- **Base publicada U2**: `641ea2fc3c77c7f365f36f8af939f7e404a44c84`
- **Commit de implementação testado**: `8aa60368a5a33deb8c8446b5db6126353af3286a`
- **Estado da entrega**: branch pushed; [PR #62](https://github.com/R-RERISON/hub-handoff-multichannel/pull/62) Draft; sem merge ou deploy.
- **Escopo**: login/seleção, Operador, Visão geral, Conversas, Filas, Equipe, Administração, histórico verificado e Laboratório.
- **Ambiente**: laboratório sintético TEMP 007a2; backup offline verificado antes da migração. A POC SQLite original e as credenciais do modo normal não foram usadas.
- **Limite de release**: este registro não aprova UX-08 da SPEC-006C, G09, G10, produção ou entrega real por Teams.

## Inventário de rotas e personas

| Rota/modo | Personas atuais | Tarefa principal |
|---|---|---|
| `/` | Operador, Supervisor, Admin, Auditor | Entrar com a identidade local autenticada. |
| `/inicio` | Admin | Escolher um dos espaços autorizados. |
| `/operador` | Operador | Receber oferta e atender somente como o operador autenticado. |
| `/supervisao` | Supervisor, Admin, Auditor | Consultar visão geral e capacidades reais da POC. |
| `/supervisao/conversas` | Supervisor, Admin, Auditor | Consultar conversas; histórico verificado somente para Supervisor/Auditor. |
| `/supervisao/filas` | Supervisor, Admin | Consultar rotação e gerenciar vínculos de despacho. |
| `/supervisao/equipe` | Supervisor, Admin | Consultar equipe e alterar presença/capacidade com confirmação. |
| `/administracao` | Admin | Consultar inventário, cadastrar fila e confirmar lifecycle. |
| `/laboratorio` | Supervisor, Admin | Criar solicitações sintéticas para homologação local. |

A matriz descreve a navegação do cliente; ela não concede autorização. RBAC e escopo continuam sendo aplicados pelo backend.

## Gate automatizado

Com `HANDOFF_DB_URL` removido, `.\start.cmd --check` terminou com exit code 0:

- Pytest: **199 passed, 1 skipped**.
- Ruff: **All checks passed**.
- Contratos frontend: **49 passed, 0 failed**.
- TypeScript: aprovado.
- Vite: **1606 módulos transformados**, build aprovado.
- `git diff --check`: aprovado na validação final.

## Evidência no navegador integrado

| Persona/superfície | Viewports efetivamente medidos | Resultado |
|---|---|---|
| Login e seleção Admin | 390×844 @100%; 1366×768 @200%; 1920×1080 @100% | Formulário semântico, foco inicial na tela, erro de login genérico em português com `role=alert` assertivo; seleção tem saída explícita. Sem overflow horizontal. |
| Administração | 390×844; 1366×768 e 1920×1080 @100% e @200% | Três tabelas com captions, row/column headers e regiões de rolagem focáveis; rolagem da tabela não alarga o documento. Formulário empilhado no mobile. |
| Administração — lifecycle | 390×844 @100%; 1920×1080 @200% real | Cancelamento enviou zero PATCH; foco inicial no Cancelar, Tab/Shift+Tab alternou as duas ações e o foco voltou ao botão acionador. A 200%, o diálogo (520×223 CSS px) e ações couberam em 960×540, sem falhas de contraste no diálogo. Confirmar arquivamento enviou exatamente um PATCH e mostrou o estado Arquivado confirmado. |
| Administração → Supervisão | 390×844 @100% | Após cadastrar uma fila, a visão da Supervisão já mostrou a fila sem aguardar o próximo polling; cadastro confirmado com um POST. |
| Supervisão — Visão geral, Conversas, Filas, Equipe e Laboratório | 390×844; 1366×768 e 1920×1080 @100% e @200% | Todas as rotas responderam no browser, com `main` e título de página focado; `document.scrollWidth` não ultrapassou a viewport. |
| Supervisão — tabelas e mutations | 390×844 e 1366×768 @200% | Equipe usa tabela semântica e labels persistentes em mobile; wrapper interno rolável sem overflow do documento. Mudança de capacidade exigiu confirmação: Cancelar enviou zero PATCH; confirmar e restaurar enviaram um PATCH cada. |
| Supervisão — revogação/erro | 1366×768 @200% | 403 sintético na rotação removeu os membros anteriores, mostrou estado negado e deixou atualizar/revalidar; a resposta revalidada restaurou a lista. Nenhuma mutation foi enviada durante a negação. |
| Auditor — Conversas/Histórico verificado | 390×844 @100%; 1366×768 @200% | Navegação mostrou somente Visão geral e Conversas; segmentos verificados identificados como somente leitura, sem controles de resposta. Acesso direto a `/supervisao/filas` foi negado e “Ir para meu workspace” retornou a Conversas. |
| Operador — oferta e conversa | 390×844; 1366×768 e 1920×1080 @100% e @200% | Oferta mostrou o estado “sem orientação interna”; no zoom real de 200% em 1366×768, o modal e ambas as ações ficaram dentro da viewport e o foco inicial foi Aceitar. Aceite enviou um POST e moveu o foco ao compositor. A conversa continuou explicitamente simulada/não enviada ao Teams. |
| Operador — resultado incerto | 1366×768 @200% | POST sintético 503 produziu exatamente uma tentativa, sem retry; a UI exibiu “Resultado não confirmado” e bloqueou composer/ações até reconciliação explícita. |
| Operador — autorização revogada | 390×844 @100% | Após carregar conteúdo-sentinela sintético, polling com 403 removeu o texto, seleção e compositor; o alerta explicou que o conteúdo protegido foi apagado. |
| Laboratório | 390×844; 1366×768 e 1920×1080 @100% e @200% | A criação sintética exibiu feedback persistente na tela do Laboratório, realizou um POST e não navegou para longe do resultado. Copy não sugere entrega real a bots/Teams. |

O zoom real do browser foi confirmado por DPR 2 e viewport CSS reduzida pela metade: 1366×768 → 683×384 e 1920×1080 → 960×540. Em 390×844 @100%, `document.scrollWidth` não ultrapassou a largura da viewport; tabelas largas rolaram dentro das regiões identificadas.

Uma inspeção automática local dos estilos computados sobre o texto visível encontrou **zero pares abaixo dos limiares de contraste aplicáveis** nas telas/estados examinados a 390×844 e a 200% real. O scanner não certifica conteúdo gráfico, todos os estados hover, nem substitui auditoria WCAG 2.2 AA completa.

As capturas foram inspecionadas diretamente no browser integrado e não foram exportadas para o repositório. Nenhuma captura, log ou artefato desta homologação contém credenciais.
Após parar API e Vite, o diretório TEMP sintético e os logs do launcher criados nesta rodada foram descartados.

## Pendências e gates não aprovados

- Revisão independente de Segurança/Arquitetura, freeze e integração ainda não foram aprovados.
- Matriz de evidências vinculada ao commit de implementação acima; revisão independente ainda pendente.
- UX-08 mobile da SPEC-006C, avaliação WCAG integral, G09 e G10 continuam gates separados.
- Não foi criado/atualizado PR, não houve push, merge ou deploy.

## Convergência — rodada complementar

As observações abaixo foram executadas antes do commit de implementação
`8aa60368a5a33deb8c8446b5db6126353af3286a`; o commit contém o mesmo código e a
matriz agora está vinculada a esse SHA.

O `.\start.cmd --check` final foi executado com `HANDOFF_DB_URL` removido e serviços
parados: **199 testes Python aprovados, 1 ignorado; Ruff aprovado; 52 contratos
frontend aprovados; TypeScript aprovado; Vite aprovou 1606 módulos**.
`git diff --check` também passou após as atualizações de evidência.

| Critério | Verificação integrada | Resultado |
|---|---|---|
| Lifecycle — timeout | PATCH sintético abortado como timeout: 1 requisição; fila permaneceu em Rascunho; nenhuma confirmação de sucesso. O foco que antes caía em `BODY` passou para o parágrafo `role=alert`, `tabIndex=-1`, com foco visível. |
| Lifecycle — sucesso | 1 PATCH; fila mudou para Ativo e a mensagem de confirmação `role=status` recebeu foco. |
| Vínculo de fila | Inclusão e remoção foram percorridas por Tab/Enter, um PATCH por confirmação, com restauração da associação inicial. Depois da correção, sucesso e conflito colocaram foco no feedback acessível; o 409 preservou estado não confirmado e bloqueou alterações até revalidar. |
| Contraste — controles | Em Administração, bordas de controles computadas como `#718599`; foco de campo/ação como `#217ac8`. Na navegação escura, o foco computado foi `#9eafc0`. |
| Contraste — estados | Aba histórica selecionada exibiu `aria-pressed=true` e indicador `#1c5da6`; hover do botão Outline usou fundo `#f0f5fa` e borda `#718599`. |
| Mobile do Operador | Em 390×844, o painel selecionado exibiu `aria-pressed=true` e indicador `#1c5da6`; o botão Conversa desabilitado passou a usar texto/fundo/borda semânticos e opacidade 1. `document.scrollWidth` permaneceu igual à viewport. |

Os contratos frontend foram ampliados para pares de texto e indicadores de foco,
seleção, desabilitado, hover e erro. Isso não é certificação WCAG integral; estados
gráficos adicionais, tecnologia assistiva e a auditoria WCAG formal permanecem gates.

**T034 — keyboard-only validado no browser integrado, laboratório sintético TEMP:**

| Persona/superfície | Jornada por teclado | Resultado |
|---|---|---|
| Login e espaço Admin | Tab para usuário/senha/submit; Enter para autenticar e selecionar Administração. | Chegou a `/administracao` sem mouse. |
| Administração | Tab para campos, digitação e Enter para criar fila; Tab até lifecycle, Enter para abrir, Tab/Enter para confirmar. | Cadastro confirmado; lifecycle enviou 1 PATCH e focou o status confirmado. |
| Supervisor — navegação, filas e equipe | Tab/Enter entre Visão geral, Filas, Equipe, Conversas e Laboratório; Tab/Enter para vínculo; setas para capacidade/presença; Tab/Enter nas confirmações. | Vínculo adicionado/removido com 1 PATCH por ação e foco no feedback; lifecycle de equipe cancelado sem PATCH e confirmado/restaurado com 1 PATCH cada. Conflito sintético preservou o vínculo, enviou 1 PATCH e focou o alerta. |
| Supervisor — histórico | Tab/Enter para Segmentos verificados; setas para a fila; Tab/Enter para selecionar segmento. | Evidência abriu em modo somente leitura, sem controles de resposta. |
| Operador | Login por Tab/Enter; Enter para aceitar oferta; digitação/Enter para responder; Tab/Enter e setas para transferir; Tab/Enter para encerrar. | Aceite, resposta, transferência e encerramento foram concluídos. As mutações registradas foram únicas; a resposta permaneceu explicitamente local/não enviada ao Teams. |
| Auditor | Login por Tab/Enter; navegação para Conversas; Tab/Enter para Segmentos verificados e seleção de fila/segmento. | Apenas Visão geral e Conversas ficaram disponíveis; histórico permaneceu somente leitura e sem comandos de escrita. |
| Laboratório | Tab/Enter para criar solicitação sintética. | Solicitação criada e exibida no laboratório. |

Isso valida as tarefas primárias keyboard-only desta matriz, não uma certificação
integral de leitor de tela/WCAG. UX-08, WCAG integral, G09 e G10 continuam gates
separados.

O laboratório TEMP complementar e os logs foram removidos; as portas 8000/5173 estão
livres. A branch está publicada e [PR #62](https://github.com/R-RERISON/hub-handoff-multichannel/pull/62) permanece Draft, sem merge ou deploy.

## G09 — correções dos achados independentes

| Achado | Correção | Evidência integrada |
|---|---|---|
| Nome acessível das contagens de navegação | O nome de Conversas/Filas agora inclui contagem e significado; o badge visual é ocultado da árvore para evitar duplicação. | O browser encontrou ambos os links pelos nomes acessíveis com contagem e descrição. |
| Foco após negação de conversa | Todas as rotas que removem a seleção protegida direcionam o foco ao título da worklist e retornam o painel mobile para Atendimentos. | 403 sintético após exibir conteúdo sentinela: 1 GET negado; sentinela removido; foco em “Meus atendimentos”; painel `work`; sem ações de conversa. |
| Foco após negação de mutation de equipe | 401/403/404 foca o título do estado negado; revalidação bem-sucedida retorna foco ao título da tabela. | PATCH sintético 403: 1 tentativa; tabela removida; foco no título da negação e botão “Revalidar acesso” disponível. |

Os contratos focados e o gate completo final passaram após alinhar um contrato
de navegação legado ao nome acessível dinâmico (`accessibleLabel`): 199 testes
Python aprovados, 1 ignorado; Ruff aprovado; 55 contratos frontend aprovados,
0 falhas; TypeScript aprovado; Vite aprovou 1606 módulos. O gate foi executado
com `HANDOFF_DB_URL` removido e os serviços sintéticos parados. As correções de
código validadas estão no commit `9ed2b7851e638ad401dce99510d1c74f10015a7d`.
G09 ainda requer revisão independente desse commit; até essa re-revisão, não
marcar G09 PASS. G10 e UX-08 da SPEC-006C permanecem gates separados.
