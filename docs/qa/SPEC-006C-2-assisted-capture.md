# SPEC-006C-2 — Captura real assistida Chrome/Edge (Windows)

**Entrega:** script opcional de execução local que automatiza o viewport,
o PNG e a guarda exclusiva no TEMP, preservando login/navegação humanos.

## Pré-condições

1. O laboratório sintético TEM de ser válido: 006b4, 22 tabelas, cinco contas
e mesma API rodando em 127.0.0.1:8000. O script só abre browser após atestar
o token emitido pelo SQLite TEMP via GET /v1/auth/me.
2. Instalar uma dependência local de QA, sem alterar dependências produtivas:

~~~powershell
.\.venv\Scripts\python.exe -m pip install "playwright>=1.49,<2"
~~~

3. Edge ou Chrome deve existir no Windows; a dependência não baixa browsers.
Executar em outro terminal enquanto start.cmd --lab --lab-dir <TEMP> roda:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.release_ui_capture --lab "<TEMP>" --browser msedge
~~~

## Procedimento

O script cria <TEMP>/qa-evidence/manifest.json com o SHA de HEAD e abre
Edge/Chrome em contextos isolados por identidade de usuário. Cada identidade
de QA deve ser autenticada manualmente usando senha do TEMP (nunca colar no chat
ou registrar screenshot do login).

A cada cenário, navegar manualmente até a página e fila indicadas e pressionar
ENTER no terminal. O runner exige rota local correta, controle de histórico
verificado selecionado quando necessário e viewport exato em window.innerWidth/
innerHeight. Grava uma captura PNG na dimensão esperada SEM sobrescrever arquivos
preexistentes. Se houver scroll horizontal da página, informa como observação,
sem classificar o gate como aprovado.

A captura pode ser retomada: os PNGs já existentes não serão sobrescritos.
A pasta permanece em TEMP e pode ser removida conscientemente ao concluir.
O runner não lê token, cookies, dados do chat ou senhas; os screenshots podem
conter os dados sintéticos do browser, portanto revise/redija antes de qualquer
publicação.

## O que continua PENDENTE mesmo com 11 capturas

- Verificar manualmente que o usuário autenticado corresponde ao perfil previsto.
- Confirmar que as duas filas foram realmente alternadas; avaliar isolamento N1/N2,
nota privada e que a supervisão não atua como operador.
- Inspecionar legibilidade, cortes, rolagens e teclado nas três resoluções.
- Passar start.cmd --check, release_probe.py e o roteiro original do PR #28
no SHA final. Registrar resultados de QA, revisão de privacidade e aprovação
independente. Captura de screenshot NÃO equivale a PASS do gate UX-08.

Nenhum screenshot real foi gerado nesta entrega de código.

## Limite de atestação do SHA

O manifesto verifica o SHA do checkout local que executa o runner e a API
localhost é atestada contra a identidade/banco TEMP; **não existe ainda
endpoint confiável de fingerprint do código do processo Vite/FastAPI em execução**.
O responsável por QA deve encerrar processos antigos, reiniciar o launcher na
branch e SHA pretendidos e registrar o processo/build real antes de aceitar
as evidências. O relatório marca runtime_commit_attested=false até prova
independente. Este script não promove main nem concede PASS visual.

## Sequência correta dos gates (lições da rodada 19/10)

A rodada em `37f48af` atestou backend N1/N2 em TEMP, mas não executou
a etapa de captura; portanto, o `--check` posterior encontrou o pacote
ausente. **Esse resultado é NOT_RUN visual, não FAIL de layout.**

Ordem para o novo SHA (sempre em worktree/lab descartável):

1. Rodar `start.cmd --check` integral, registrar SHA final.
2. Iniciar `start.cmd --lab` num TEMP novo e manter API/Vite ativos.
   Se 8000/5173 estiverem ocupadas, **não encerrar serviços automaticamente**:
   identificar a origem dos processos, seus responsáveis e obter autorização
   explícita. Processos podem reiniciar sob gerenciador/supervisão externa.
3. Executar `release_ui_scope_fixture --lab <TEMP> --confirm-synthetic`
   **uma vez**, certificando `ux05_n2_operator_ready=PASS`.
4. Rodar `release_ui_capture --lab <TEMP> --browser msedge`, navegar
   manualmente aos perfis/filas indicados, fazer login no próprio browser
   com credenciais descartáveis e completar 11 capturas PNG.
5. Somente então rodar `release_ui_evidence_gate --lab <TEMP> --check`;
   o resultado válido é `EVIDENCE_READY_FOR_MANUAL_REVIEW`, não PASS UX.
6. Revisar as evidências antes de removê-las: perfis efetivos,
   conteúdo e notas restritas, responsividade e interações por teclado.
   Registrar SHA, browser, dados sintéticos e decisão de cada gate.

Para UX-05 a Mesa N2 deve ser acessada como `bruno.demo`; após o fixture,
a sessão estará `ACTIVE` por aceite real na fila N2. A atribuição de
Ana em N1 continua sendo uma **precondição sintética**, não uma prova de
aceite N1. Não reutilizar o mesmo banco TEMP para rodar o fixture uma
segunda vez, pois a capacidade do operador N2 já estará ocupada.

Os screenshots são apenas **arquivos locais no TEMP**: o runner não os
publica nem faz sanitização automática. A revisão humana continua
obrigatória, e a existência de PNG não comprova o SHA do processo web
em execução; conferir que o launcher foi reiniciado do checkout correto.
