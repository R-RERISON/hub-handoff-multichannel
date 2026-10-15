# Desenvolvimento local via Git e VS Code

**Fluxo preferencial:** ` .\start.cmd ` inicia backend e frontend no mesmo terminal, instala dependências quando necessário, gera a chave local, abre o navegador e encerra os dois processos com Ctrl+C. Para testes locais, execute ` .\start.cmd --check `. Mais detalhes em [Setup em um comando](setup-one-command.md).

O GitHub é a fonte das versões. O desenvolvedor clona e atualiza via Git; não usamos GitHub Actions.

## Primeira instalação (PowerShell)

```powershell
git clone --branch feat/002-sqlite-poc https://github.com/R-RERISON/hub-handoff-multichannel.git
cd hub-handoff-multichannel
code .
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Atualização do código (PowerShell na raiz)

```powershell
git status --short
git switch feat/002-sqlite-poc
git pull --ff-only origin feat/002-sqlite-poc
```

Se houver arquivos modificados, preserve-os antes de atualizar.

## Revisão da POC (UX-002)

A leitura de contexto foi consolidada em `GET /v1/dashboard`; o frontend agora consulta o snapshot com intervalo de 15 segundos quando a aba está visível. Os filtros de conversas são interativos e as respostas da outbox aparecem como sem envio externo. Homologar com `.\\start.cmd --check` e `.\\start.cmd`. Veja [UX-002](ux/UX-002-operations-review.md).

## POC-003 — Operação humana

A branch de homologação da nova Mesa do Operador é `feat/003-operator-workflow`. Execute:

```powershell
git status --short
git switch --track origin/feat/003-operator-workflow
git pull --ff-only origin feat/003-operator-workflow
.\start.cmd --check
.\start.cmd
```

Se a branch já existir localmente, utilize `git switch feat/003-operator-workflow`, sem `--track`. Na primeira atualização, use `git fetch origin` antes de criar a branch local, se necessário.

A nova versão insere apenas as tabelas `handoff_offers` e `session_transfers` no SQLite. Para preservar estado de laboratório, encerre os serviços antes de copiar/arquivar seu arquivo SQLite.

[Contrato completo e cenários de homologação](specs/POC-003-operator-workflow.md).

## Testes backend

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

## Executar backend

```powershell
$env:HANDOFF_POC_KEY = "SUBSTITUA-POR-CHAVE-LOCAL"
.\.venv\Scripts\python.exe -m uvicorn handoff_hub.main:app --host 127.0.0.1 --port 8000 --reload
```

API de teste: http://127.0.0.1:8000/docs

## Executar e validar frontend

Em outro terminal, na raiz do projeto:

```powershell
cd web
npm install
npm run build
npm run dev
```

Frontend: http://127.0.0.1:5173

Use a mesma chave configurada no backend para acessar a simulação. Somente localhost, dados fictícios; não há integração Teams nesta fase.

## Contrato de futuras entregas

Cada entrega deve incluir: branch, commit/PR, resumo, comando Git para atualização, comandos de execução, comandos de teste, resultado de testes de fato executados e limitações conhecidas. Não usar pipelines GitHub Actions.
