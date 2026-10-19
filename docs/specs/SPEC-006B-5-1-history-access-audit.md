# SPEC-006B-5.1 — Diário persistente de leitura verificada, com falha fechada

**Status:** DRAFT, dependente de gate local Windows e revisão de segurança.  
**Branch:** `feat/006b5a-history-access-audit` — base `feat/006b4c-history-detail-pagination`.  
**Premissa comprovada da base:** 100/100 Pytest, Ruff, 11/11 frontend architecture, TypeScript e Vite em 16/10/2026; o SQLite original segue `revision=null`, `integrity=ok`, **17 tabelas**, sem backfill e com `rows_written=0` no dry-run.

## Problema

Até 006B-4.3, supervisores e auditores autenticados podiam consultar evidências `RUNTIME/VERIFIED` por fila concedida, com paginação independente, mas o sistema não possuía **comprovação persistente de cada leitura autorizada**. O log da aplicação não basta para demonstrar quem consultou qual escopo; gravações em memória não são duráveis.

## Recorte entregável

**A primeira etapa registra apenas acessos autorizados bem-sucedidos**, de duas superfícies:

- `GET /v1/history/verified-sessions?queue_id=...&page=...&page_size=...` → `resource=LIST`.
- `GET /v1/handoffs/{id}/verified-history?queue_id=...&message_page=...&event_page=...&page_size=...` → `resource=DETAIL`.

Registra no SQLite **versionado 006b3** os campos `id`, `user_id`, `role`, `operation_id`, `queue_id`, `session_id` (somente DETAILS), `resource`, `message_page`, `event_page`, `page_size`, `returned_messages`, `returned_events`, `returned_sessions` e `created_at`. Cada acesso recebe ID próprio e timestamp UTC. **Não armazena** conteúdo de mensagens, notas privadas de transferência, requester, subject, senha, token Bearer, headers ou IP de usuário.

### Modelo e migração

- Nova revisão `006b3_history_access_audit` dependente de `006b2_queue_provenance`, criando **apenas** `history_access_audit` e dois índices: `ix_history_audit_scope_time` e `ix_history_audit_user_time`. Sem backfill nem alteração dos registros anteriores.
- `audit_schema.py` define o contrato de tabela em `MetaData` **separado** de `Base.metadata.create_all()`.
- `schema_admin.verify_database` aceita 006b1, 006b2 e 006b3 e valida a estrutura; `create_new` cria **somente novo banco descartável** em 006b3; `upgrade_existing` continua responsável **exclusivamente** por 006b1→006b2; novo comando `upgrade-audit --confirm-offline` efetua **006b2→006b3**, exigindo banco off-line, inspeção, backup verificável com SHA-256, dados preservados e tabela nova vazia.
- `ProvenanceRecorder` reconhece as revisões 006b2 e 006b3. Apenas 006b3 com tabela de auditoria existente define `audit_enabled=True`.
- O banco principal POC **não versionado com 17 tabelas** não deve ser adotado nem migrado por esta SPEC. `start.cmd` continua sem migração e sem DDL de auditoria.

### Transação e fail-closed

1. Autenticação e autorização por papel, operação e grant de fila são revalidadas a cada página.
2. Para banco `revision=null`, a listagem pode responder o **estado público de indisponibilidade** `schema_ready=false` sem histórico; o detalhe continua 404; nenhum journal é criado.
3. Para banco 006b2 com proveniência mas **sem diário**, listagem e detalhe retornam **503**, não entregam dados verificados e não executam DDL.
4. Para banco 006b3, o `SELECT` protegido e o `INSERT` no journal acontecem na **mesma transação SQLAlchemy** (`factory.begin()`). A API só devolve dados depois de confirmado o commit. Falha no `INSERT`/commit impede retornar a resposta protegida (erro 5xx), sem retorno parcial.
5. O insert registra somente contagens **limitadas à fila e página**; `LIST` inclui apenas `returned_sessions`, `DETAIL` registra `returned_messages`/`returned_events`. Não registrar totais globais ou conteúdos.
6. A restrição de acesso às rotas anteriores `/messages` e `/timeline` continua conservadora. Não expor endpoint público de consulta da tabela de auditoria neste incremento.

## Segurança / limitações explícitas

Este incremento é um **diário persistente append-only pela API**, *não um WORM ou trilha imutável verificável*. Administradores do SQLite ainda podem alterá-lo fora da aplicação. Não registra acessos negados, falhas de autenticação, eventos de concessão/revogação, acessos ADMIN às rotas legadas nem leituras de operador; o escopo cobre exclusivamente as duas rotas verificadas.

Próximos gates para considerar solução de auditoria corporativa:
- Registrar tentativas negadas e revogações sem afetar 401/403/404 e sem vazar identidades, com transação separada apropriada à negação;
- Retenção, LGPD, integridade/tamper-evidence (hash encadeado ou armazenamento WORM com operador distinto), exportação administrativa segura e visibilidade auditável;
- Testar simultaneidade de SELECT + INSERT com múltiplos readers SQLite WAL, lock contention e falha do journal;
- Reavaliar locking e migrações no SQL Server antes de qualquer publicação externa;
- Adicionar autenticação corporativa OIDC/Entra ID e revisar multioperação.

## Testes e aceite

1. `schema_admin`: testam não migração implícita, backup antes de 006b3, exigência `--confirm-offline`, preservação das linhas da 006b2, tabela vazia, validação de índices e recusa de revisões inadequadas.
2. `verified_history`: consultas LIST e DETAIL geram um registro cada, com papel/fila/usuário/páginas e contagens corretas, **sem mensagens**; falha simulada no diário interrompe a resposta e não divulga texto; SQLite 006b2 sem diário retorna 503; banco original permanece bloqueado.
3. `provenance_dry_run` e `provenance_audit` aceitam 006b3 para fins **somente leitura**, sem atribuir direitos históricos e sem escrita.
4. Todas as bases dos testes são geradas em `tmp_path`, com entidades sintéticas; nenhuma envolve as 22 sessões ou mensagens do SQLite original.
5. Gate Windows obrigatório: `.\start.cmd --check` (Pytest, Ruff, 11 testes de arquitetura frontend, TypeScript/Vite), seguido de `schema_admin inspect` e `provenance_dry_run` contra o SQLite **original**. Sem GitHub Actions.

### Procedimento de homologação local (sem mudar SQLite original)

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
$branch = "feat/006b5a-history-access-audit"
if (@(git branch --list --format="%(refname:short)" $branch) -contains $branch) {
  git switch $branch
} else {
  git switch --create $branch --track "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw "Falha no checkout" }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Falha no fast-forward" }
.\start.cmd --check
if ($LASTEXITCODE -ne 0) { throw "Gate reprovado" }
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
if ($LASTEXITCODE -ne 0) { throw "Inspect reprovado" }
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
if ($LASTEXITCODE -ne 0) { throw "Dry-run reprovado" }
```

**Expectativa antes de executar:** 105 testes Python (100 prévios +3 verified_history +2 schema_admin), Ruff, 11 testes frontend e TypeScript/Vite aprovados. O original deve continuar com 17 tabelas e revisão nula.

## Rollback

`git switch feat/006b4c-history-detail-pagination`. Nenhuma alteração de esquema ou escrita no SQLite principal é necessária ou permitida. Em banco **isolado e explicitamente migrado**, rollback de esquema 006b3→006b2 só é permitido se a tabela de auditoria estiver vazia; migração recusa descartar registros de auditoria. **Nunca apagar registros de auditoria de um ambiente não descartável para forçar downgrade.**
