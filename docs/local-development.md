# Desenvolvimento local via Git e VS Code

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
