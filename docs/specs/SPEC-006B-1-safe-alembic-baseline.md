# SPEC-006B-1 — Alembic baseline com adoção segura e backup SQLite

**Estado:** IMPLEMENTADO EM PR DRAFT, PENDENTE DE GATES WINDOWS.  
**Base:** `feat/006-queue-scoped-authorization` já homologada para N1→N2, orientação interna e 13 checks RBAC.  
**Escopo:** versionamento inicial + ferramentas offline. **Nenhum backfill/segmento, mudança do chat ou migração automática nesta fatia.**

## O que foi entregue

- Dependência `alembic>=1.14,<2`; `migrations/env.py` e revisão `006b1_poc_baseline`.
- Banco **novo**: a revisão cria integralmente as tabelas do esquema atual, inclusive roles de fila, ofertas, sessões, mensagens, outbox e transferências.
- Banco **existente**: nunca executar `alembic upgrade head` diretamente. O comando `adopt` verifica a assinatura da estrutura atual (tabelas, colunas, tipos, PK, nulabilidade, FKs e índices), valida integridade SQLite, produz cópia consistente via `sqlite3.backup` (inclui WAL) e **carimba apenas** `alembic_version`. Não reescreve contas, senhas, mensagens, históricos, ofertas, atendimentos ou grants.
- Adoção falha diante de schema desconhecido, tabela/índice ausente, FK inválida, checksum de integridade inválido, revisão existente ou mudança detectada durante o backup.
- Cada cópia obtém caminho único `data/backups/*.db`, ignorado no Git, acompanhado de SHA-256. Tratar essas cópias como dados confidenciais: não subir para o GitHub.
- Interface CLI via `python -m handoff_hub.schema_admin`, sem integração ao startup. O `start.cmd` **continua** com `Base.metadata.create_all` por compatibilidade com a POC; a substituição por migrações estritas será gate seguinte.
- Testes `tests/test_schema_admin.py` só usam SQLite temporário em `tmp_path`, sem tocar o banco real.

## Preparação / gates automáticos

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git fetch origin
git switch --track origin/feat/006b1-safe-alembic-baseline
.\start.cmd --check
```

O launcher sincronizará Alembic com as dependências Python do projeto quando detectar a mudança no `pyproject.toml`. Sem GitHub Actions.

**Critério de aprovação:** Pytest, Ruff, 8+ testes de arquitetura frontend, TypeScript e Vite aprovados. A adoção real só deve ser tentada após o retorno desses testes.

## Etapa 1 — Inspecionar (somente leitura, API pode estar em execução)

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
```

Retorno esperado: `"integrity": "ok"`, `"revision": null` (ainda não adotado), tabela/contagem, incluindo `messages`, `handoff_sessions` e `queue_role_grants`. Qualquer divergência aborta: **não** usar `alembic stamp` manualmente.

## Etapa 2 — Backup/adoção (somente após autorização e com todos os serviços parados)

1. Encerrar o `start.cmd` com `Ctrl+C`. Verificar que não há processo FastAPI/dispatcher acessando o SQLite nem outro serviço usando o mesmo arquivo.
2. Fazer cópia prévia opcional para conferência:

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin backup
```

3. Adotar formalmente o esquema atual:

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin adopt --confirm-offline
```

A operação `adopt` **faz novo backup obrigatório automaticamente**, antes de registrar a versão. O resultado imprime caminho do arquivo de backup, SHA-256, revisão e contagem de registros preservados. Não inclui credenciais nem conteúdo das mensagens.

4. Verificar depois:

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
.\start.cmd --check
.\start.cmd
```

O `inspect` deverá mostrar `"revision": "006b1_poc_baseline"`, mesma contagem de registros. Validar login, tickets, grants e transferência N1→N2. Não apagar `data/handoff-poc.db` ou `data/demo-credentials.txt`.

### Banco novo descartável (exemplo, NÃO é o banco atual)

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin `
  --database .\data\teste-versao-descartavel.db create --confirm-offline
```

Não usar `create` para banco existente. O utilitário aborta em vez de sobrescrever um arquivo.

## Segurança e limitações declaradas

- Esta é uma **baseline exata do estado da POC**, não o mecanismo final de upgrade de versões históricas POC 0.2/0.3/0.4. Instalação antiga com schema diferente será recusada até existir migração apropriada, sem inventar equivalências.
- O teste de integridade/estrutura não substitui backup independente e restauração verificada antes de mudanças futuras destrutivas. Cópias contêm hashes de sessão e outros dados que não devem ser compartilhados.
- Os serviços **devem estar parados para adotar**; `--confirm-offline` é declaração explícita do executor, não um bloqueio de sistema operacional contra todos os processos.
- O revision script usa `Base.metadata.create_all(checkfirst=False)` **somente ao criar um banco vazio**. Versões posteriores utilizarão operações `op.create_table/op.add_column` etc, sempre aditivas e auditadas.
- Até SPEC-006B-3/4, não há registros de `session_queue_segments` nem liberação do histórico de conversas transferidas a auditores/supervisores. O fail-closed da 006A segue intacto.
- Não há adapter Teams nem alteração de outbox; `PENDING_ADAPTER` continua real.
- Execução no SQLite corporativo/produção **não está autorizada**. O ciclo ainda é demonstrativo local.

## Continuação depois deste gate

- 006B-2: segmentos de fila e proveniência de mensagens/eventos, DDL aditiva versionada.
- 006B-3: escrita do segmento atual em novas mensagens/transferências; backfill conservador dos registros anteriores.
- 006B-4: leitura do histórico filtrada por segmento, testes negativos de acesso interfilas e trilha de auditoria.
- 006B-5: grants multirrole e compatibilidade com administração/monitoria futuras.

Cada etapa terá PR próprio, testes positivos/negativos e plano de reversão que não destrua histórico.
