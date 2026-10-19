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
