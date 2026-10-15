# Setup e inicialização em um único terminal

O Handoff Hub SQLite POC usa Python/FastAPI e React/Vite, mas **não exige abrir dois terminais**.

## Comando único para Windows (PowerShell, na raiz do projeto)

```powershell
.\start.cmd
```

Pode também dar duplo clique em `start.cmd` no Explorador de Arquivos.

O inicializador:
1. Valida Python 3.12+ e npm/Node.js.
2. Cria `.venv` se não existir.
3. Instala/atualiza dependências Python e npm quando detecta alteração em `pyproject.toml` ou `web/package.json`.
4. Lê `HANDOFF_POC_KEY` se for uma chave não demonstrativa; caso contrário gera automaticamente uma nova chave secreta, armazenada em `data/.poc-key` (fora do Git).
5. Inicia FastAPI em `127.0.0.1:8000` e Vite em `127.0.0.1:5173` no **mesmo terminal**, com logs `[API]` e `[WEB]`.
6. Abre o navegador com a interface. Copie a chave de POC apresentada no terminal para acessar.
7. Ao pressionar **Ctrl+C**, encerra os dois processos e seus subprocessos.

Caso as portas estejam ocupadas por execuções antigas, o launcher não inicia uma segunda instância: encerre os terminais antigos e execute novamente.

## Apenas instalação (sem iniciar)

```powershell
.\start.cmd --setup-only
```

## Validar toda a POC localmente

```powershell
.\start.cmd --check
```

Executa Pytest, Ruff (backend) e `npm run build` (frontend), sem GitHub Actions.

## Não abrir navegador

```powershell
.\start.cmd --no-browser
```

## Atualização do código

```powershell
git status --short
git switch feat/002-sqlite-poc
git pull --ff-only origin feat/002-sqlite-poc
.\start.cmd
```

## Restrições

- Apenas localhost e dados fictícios. **Não publicar esta POC na rede corporativa**.
- Não há autenticação corporativa, usuários reais nem conector Teams.
- A chave local **não deve ser enviada ao GitHub**. O diretório `data/` é ignorado pelo Git.
- O SQLite é preservado em `data/handoff-poc.db` entre reinícios.
- O comando `--check` não inicia servidor; use sem serviços em execução para comparar o ambiente com a versão publicada.
