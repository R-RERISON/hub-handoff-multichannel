# SPEC-006C-1 — Fixture seguro de UX-02 e UX-05

**Status:** implementado na branch de feature; testes locais Windows e homologação visual ainda pendentes.

O utilitário scripts/release_ui_scope_fixture.py cria no laboratório TEMP 006b4
uma sessão sintética N1, mensagem N1, transferência real via API para N2
e mensagem N2. A atribuição ACTIVE a Ana é apenas uma precondição de QA,
não um teste da oferta/aceite N1. Após verificar os controles de acesso, o
fixture executa o despacho e o aceite **reais pela API** na fila N2 e
confirma que a Mesa de Bruno possui a sessão ACTIVE. Também verifica que
a nota interna pode aparecer na trilha privada do operador, mas nunca nas
mensagens do cliente. Isso prepara a captura UX-05 sem aprovar a UX.

## Execução na máquina Windows

1. Atualize a branch da feature e valide os testes locais com start.cmd --check.
2. Inicie start.cmd --lab --lab-dir <DIRETORIO_TEMP> com a API e Vite no mesmo terminal.
3. Em outro PowerShell execute:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.release_ui_scope_fixture --lab "<DIRETORIO_TEMP>" --confirm-synthetic
~~~

O script rejeita qualquer caminho que não seja um laboratório TEMP
explicitamente validado 006b4, grants inesperados e API de browser apontando
a outro banco ANTES de qualquer escrita.

## Resultado esperado do backend

- Supervisor tem N1/N2, Auditor somente N1.
- VERIFIED N1 contém somente mensagem N1; VERIFIED N2 somente mensagem N2.
- A nota de transferência nunca aparece no histórico verificado.
- Auditor N1 solicitando N2 recebe 404 sem conteúdo protegido.
- Supervisor não publica como operador: 403.
- N2 recebe oferta e aceita a sessão por API, disponível na Mesa do Bruno.
- Resumo JSON não inclui IDs, senhas, tokens, mensagens ou notas.
- manual_ux02=NOT_RUN, manual_ux05=NOT_RUN, manual_ux08=BLOCKED.

## Homologação visual ainda obrigatória

Usar usuários supervisor.demo e auditor.demo em sessões isoladas.
Em Supervisão → Conversas → Segmentos verificados, alternar N1/N2 e
fotografar os dois segmentos da mesma sessão; verificar ausência de ação
operacional. Em Auditor conferir apenas N1. Repetir UX-08 no browser de
viewport estável em 390×844, 1366×768 e 1920×1080, incluindo Mesa de Operador.
Anexar evidência sanitizada ao PR #28 e issue #29, SHA e ambiente.

Uma execução aprovada acrescenta uma sessão e duas mensagens no SQLite TEMP.
Nenhuma operação do script modifica data/handoff-poc.db, grants ou main.

### Atenção à massa de dados

Executar em laboratório TEMP novo, com Bruno AVAILABLE e capacidade livre.
O pré-check verifica, somente leitura, se Bruno tem membership em N2,
se há atendimentos ativos/ofertados a ele e se N2 possui fila pendente.
Se estiver ocupado, recusa **antes** de criar a sessão. Não repetir no
mesmo TEMP sem encerramento ou descarte controlado do cenário anterior.
Use Bruno em /operador para capturar a conversa N2 e sua nota interna.
