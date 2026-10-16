# SPEC-006B-2 — Schema de segmentos e proveniência histórica por fila

**Estado:** IMPLEMENTADO NO GITHUB — PR DRAFT, AGUARDANDO GATES WINDOWS.
**Base:** SPEC-006B-1 (`feat/006b1-safe-alembic-baseline`).
**Escopo limitado:** DDL aditiva, inspeção assinada por revisão e upgrade manual com backup. **NÃO** atribui mensagens antigas a filas nem muda consultas/autorizações existentes.

## Objetivo

Registrar no banco as estruturas necessárias para identificar a que trecho/fila do atendimento pertencem mensagens e eventos, sem usar a fila *atual* do ticket como prova de acesso ao histórico anterior.

A POC possui `handoff_sessions.queue_id` (fila atual) e `session_transfers` (transferências), mas as mensagens e eventos ainda não têm proveniência segmentada. A SPEC-006A bloqueia conservadoramente históricos transferidos para supervisor/auditor. **Este bloqueio continua até SPEC-006B-3/4**, mesmo após a migração da estrutura.

## Contrato das tabelas

| Tabela nova | Propósito | Dado importante |
|---|---|---|
| `session_queue_segments` | Episódios ordenados de responsabilidade por fila para cada ticket | `session_id`, `queue_id`, `ordinal`, `started_at`, `ended_at`, `transfer_id`, `provenance_state` |
| `message_queue_provenance` | Liga cada mensagem a um episódio identificado quando houver evidência | `message_id`, `segment_id` opcional, `assigned_by`, `confidence` |
| `session_event_queue_provenance` | Proveniência dos eventos do histórico | `event_id`, `segment_id` opcional, `assigned_by`, `confidence` |

A migration `006b2_queue_provenance` (down_revision `006b1_poc_baseline`) cria as três tabelas **vazias**, com FKs, PKs, índice por fila/data e índice por sessão/ordem. É aditiva: não atualiza ou remove registros de `messages`, `session_transfers`, `session_events`, `handoff_sessions`, `auth_users` ou `queue_role_grants`.

As declarações dessas tabelas ficam propositalmente em `provenance_schema.py` com `MetaData` separado. Assim `Base.metadata.create_all()` no bootstrap POC **não cria** as estruturas novas quando o usuário executa `start.cmd`.

`UNDETERMINED` significa proveniência insuficiente. A SPEC-006B-3 fará backfill conservador e escrita de novas mensagens; a SPEC-006B-4 aplicará o filtro de autorização por segmento. **Nenhuma permissão adicional é concedida por esta migration.**

## Gestão de versão

O utilitário `schema_admin` passa a reconhecer estes estados:

- **Unversioned** (`revision = null`): esquema POC anterior. Somente `inspect` e `adopt --confirm-offline` são adequados; `upgrade` recusa até adoção da baseline 006B-1.
- **006B-1** (`006b1_poc_baseline`): 17 tabelas originais. Elegível a `upgrade --confirm-offline`, **sempre com backup consistente antes**.
- **006B-2** (`006b2_queue_provenance`): 20 tabelas, incluindo 3 novas vazias na migração inicial. `inspect` valida assinatura de esquema e retorna contagens; outra tentativa de `upgrade` recusa por revisão incompatível.

`create --confirm-offline` cria um **banco novo** na revisão mais recente 006B-2, com as 20 tabelas e sem dados de usuários.

## Gates automatizados

- 006B-1: os 63 Pytest, Ruff, 9 testes de arquitetura frontend, TypeScript e Vite continuam obrigatórios.
- Testes 006B-2: upgrade em SQLite temporário baseline previamente adotado; preservação exata das contagens das tabelas antigas e do texto de mensagens; rejeição de banco não versionado; revisão nova em criação limpa; três tabelas vazias; integridade FK/índices; backup também inspecionável em 006B-2.
- Nenhum teste utiliza o SQLite de homologação do usuário; não criar workflows GitHub Actions.

## Homologação Windows — primeiro somente testes e inspect

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git fetch origin
git switch --track origin/feat/006b2-segment-provenance-schema
.\start.cmd --check
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
```

**Esperado para o banco original da POC:** 17 tabelas e `revision=null`, pois a migração é explícita. Nesse momento, **não executar upgrade no banco principal**.

## Homologação automatizada com proteção contra alteração do original

**Procedimento preferencial:** foi adicionado o script versionado `scripts/homologate-spec006b2.ps1` (Windows PowerShell 5.1/7). Ele automatiza a homologação abaixo, exige confirmação de serviços parados, verifica se as portas de desenvolvimento ainda estão em uso e **nunca passa o banco original aos comandos `adopt` ou `upgrade`**.

```powershell
# Com FastAPI, Vite e dispatcher parados:
.\scripts\homologate-spec006b2.ps1 -ConfirmServicesStopped
```

O script verifica a assinatura do original (`revision=null`, 17 tabelas), cria snapshot `sqlite3.backup` com hash SHA-256, confere que o arquivo está dentro de `data/backups/homolog006b2/snapshots`, adota a baseline `006b1_poc_baseline` **somente nessa cópia**, executa upgrade `006b2_queue_provenance` nela e verifica que:

- As contagens de todas as 17 tabelas legadas são idênticas antes/depois;
- A cópia passou a conter 20 tabelas com as três novas vazias;
- O original segue com `revision=null`, 17 tabelas e contagens preservadas;
- Os backups pré-adoção e pré-upgrade foram criados em subpastas locais ignoradas no Git.

**Não executar** `adopt --confirm-offline` ou `upgrade --confirm-offline` contra `data/handoff-poc.db` nesta etapa. O script ainda precisa passar pela execução real no Windows antes de ser considerado homologado; não enviar arquivos de backup nem tokens por chat.

## Homologação de upgrade — somente em cópia, com todos os serviços parados

O banco de origem continua sem Alembic. O roteiro abaixo cria uma cópia consistente, adota a baseline **somente nela**, e aplica a 006B-2 **somente nela**, com cópias de segurança em cada passagem:

```powershell
$python = ".\.venv\Scripts\python.exe"

# Um snapshot do banco principal, ainda sem revision.
$backup = & $python -m handoff_hub.schema_admin backup | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Backup falhou" }
$copia = $backup.path

# Prepara a copia. O banco original NAO sera alterado.
& $python -m handoff_hub.schema_admin --database "$copia" `
  --backup-dir ".\data\backups\006b2-adoption" adopt --confirm-offline
if ($LASTEXITCODE -ne 0) { throw "Adoção da cópia falhou" }

# Atualiza somente a copia 006B-1 para a revisão 006B-2.
& $python -m handoff_hub.schema_admin --database "$copia" `
  --backup-dir ".\data\backups\006b2-upgrade" upgrade --confirm-offline
if ($LASTEXITCODE -ne 0) { throw "Upgrade da cópia falhou" }

& $python -m handoff_hub.schema_admin --database "$copia" inspect
& $python -m handoff_hub.schema_admin inspect
```

**Esperado:** cópia = revisão `006b2_queue_provenance`, 20 tabelas, novas tabelas vazias e todas as contagens legadas iguais. Original = `revision=null`, 17 tabelas, sem alterações.

Parar antes de executar qualquer `adopt` ou `upgrade` no SQLite principal. Cópias podem conter credenciais criptografadas, chats e dados pessoais; não compartilhar nem subir ao GitHub.

## Limitações e rollout

A migração é aditiva e reversível **somente enquanto as novas tabelas estiverem vazias**. O downgrade direto de Alembic recusa apagar proveniência já gravada. Durante esta entrega, não existe UI para segmentos e `GET /v1/handoffs/{id}/messages` não consulta esses novos registros.

Após o gate de migração em cópia: **SPEC-006B-3** introduzirá a escrita por segmento e backfill seguro de dados anteriores, com testes negativos para valores ambíguos; **SPEC-006B-4** implementará autorização de leitura por episódio de fila.
