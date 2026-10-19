# SPEC-006C-1 — Fixture seguro de UX-02 e UX-05

**Status:** implementado na branch de feature; testes locais Windows e homologação visual ainda pendentes.

O utilitário scripts/release_ui_scope_fixture.py cria no laboratório TEMP 006b4
uma sessão sintética N1, mensagem N1, transferência real via API para N2
e mensagem N2. A atribuição ACTIVE a Ana é apenas uma precondição de QA;
este script não atesta a jornada de oferta/aceite.

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
- Resumo JSON não inclui IDs, senhas, tokens, mensagens ou notas.
- manual_ux02=NOT_RUN, manual_ux05=NOT_RUN, manual_ux08=BLOCKED.

## Homologação visual ainda obrigatória

Usar usuários supervisor.demo e auditor.demo em sessões isoladas.
Em Supervisão → Conversas → Segmentos verificados, alternar N1/N2 e
fotografar os dois segmentos da mesma sessão; verificar ausência de ação
operacional. Em Auditor conferir apenas N1. Repetir UX-08 no browser de
viewport estável em 390×844, 1366×768 e 1920×1080, incluindo Mesa de Operador.
Anexar evidência sanitizada ao PR #28 e issue #29, SHA e ambiente.

Cada execução acrescenta uma sessão e duas mensagens no SQLite TEMP.
Nenhuma operação do script modifica data/handoff-poc.db, grants ou main.
