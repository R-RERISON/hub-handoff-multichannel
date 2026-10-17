# Execução local — Handoff Hub POC 0.5 / SPEC-006B-5.2

**Escopo:** simulação localhost. Sem Teams real, autenticação corporativa, SQL Server ou dados de produção.

## Primeiro acesso

No PowerShell, na raiz do projeto:

```powershell
.\start.cmd
```

O launcher prepara dependências se necessário, executa o seed **idempotente** das cinco contas de demonstração, inicia FastAPI em `127.0.0.1:8000` e React/Vite em `127.0.0.1:5173` no mesmo terminal e abre a interface. Cada perfil autentica com **usuário e senha individuais**.

As senhas são geradas somente no ambiente local e escritas no arquivo ignorado pelo Git `data/demo-credentials.txt`. **Não** são uma chave compartilhada, não se deve enviá-las por chat, imprimir em evidências nem publicar o banco ou screenshots com segredos.

Contas: `admin.demo`, `supervisor.demo`, `auditor.demo`, `ana.demo`, `bruno.demo`. `--reset-users` é uma operação de rotação de credenciais com revogação de sessões e **não** deve ser usada como parte do gate de QA sem planejamento.

```powershell
.\start.cmd --setup-only   # apenas dependências
.\start.cmd --no-browser   # inicia serviços sem abrir navegador
.\start.cmd --check        # Pytest, Ruff, testes frontend, TypeScript e Vite
```

A API e a interface encerram ao pressionar Ctrl+C no terminal do launcher. Não criar instâncias paralelas nas portas 8000/5173.

## Preservação do SQLite existente

O banco em `data/handoff-poc.db` é a **POC original**, sem Alembic, com 17 tabelas. O launcher **não** aplica a migração `006b1`/`006b2`/`006b3`/`006b4`. Usar apenas diagnósticos read-only:

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
```

**Não executar** `adopt`, `stamp`, `upgrade`, `upgrade-audit`, `upgrade-security` ou `create` sobre o banco original. Sem inferência de proveniência para histórico legado.

## Homologação da integração na main (PR #28)

O gate automatizado e o laboratório visual usam somente bancos descartáveis:

```powershell
.\start.cmd --check
.\.venv\Scripts\python.exe scripts\release_probe.py
.\scripts\prepare-main-integration-lab.ps1
```

O `release_probe.py` cria, exercita e remove um SQLite temporário 006b4 com credenciais sintéticas, sem serviços externos. O script `prepare-main-integration-lab.ps1` prepara outro SQLite sob `$env:TEMP` e informa **dois launchers temporários** para abrir API e Vite em terminais diferentes, com credenciais de laboratório guardadas no próprio diretório temporário.

**Não usar `start.cmd` para o laboratório sintético**, pois o seu provisionamento de credenciais usa por padrão `data/demo-credentials.txt`, mesmo com `HANDOFF_DB_URL` personalizado. Encerrar os serviços anteriores antes de executar o laboratório. Procedimentos, critérios e matriz de aceite: [PR-028-release-acceptance.md](qa/PR-028-release-acceptance.md).

## Git

Enquanto PR #28 estiver Draft, trabalhar na branch `feat/006b5b-security-decisions-journal`:

```powershell
git status --short
git fetch origin
git switch feat/006b5b-security-decisions-journal
git merge --ff-only origin/feat/006b5b-security-decisions-journal
```

Se a branch ainda não existir localmente, criá-la com `git switch --create feat/006b5b-security-decisions-journal --track origin/feat/006b5b-security-decisions-journal`.

Após o PR ser revisado e aprovado, confirmar o estado da `main` antes de trocar a orientação acima. Não executar GitHub Actions, não mesclar PRs antigos indiscriminadamente e não expor esta POC fora do `127.0.0.1`.
