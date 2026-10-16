# SPEC-006A — Fundações: concessões por fila e migração Alembic

**Estado:** IMPLEMENTADO EM BRANCH / PENDENTE DE TESTES WINDOWS E HOMOLOGAÇÃO  
**Base:** `feat/005-rbac-auto-dispatch` (POC 0.5 homologada)  
**Branch:** `feat/006-queue-scoped-auth-foundation`  
**Referências:** RFC-006 e PLAN-006–013 no PR #14.

## Escopo efetivamente implementado

1. **`queue_role_grants`**: usuário, fila e papel SUPERVISOR/AUDITOR; distinto do membership operacional do operador.
2. Autorizações verificadas no **backend a cada request**: recurso/fila, identidade, operação e gerenciamento de operador global. Revogação entra em vigor sem novo login.
3. `GET /v1/dashboard`, `/v1/queues`, `/v1/operators` e `/v1/handoffs` filtram **no SQL**, antes dos agregados e da paginação. Painel não usa dado de outra fila.
4. `GET /v1/queues/{queue_id}/rotation` e `PATCH /v1/queues/{queue_id}/members/{operator_id}` exigem grant da fila, além de regras de gestão da equipe.
5. `GET /v1/handoffs/{id}/messages` e `/timeline` exigem autorização de objeto; em conversas transferidas SUPERVISOR/AUDITOR precisam, **nesta fatia conservadora**, de grants em todas as filas percorridas. Não há leitura parcial segura de segmentos ainda.
6. ADMIN não pode obter conteúdo das conversas por privilégio administrativo implícito. `/v1/outbox` com conteúdo deixa de ser acessível aos papéis autenticados locais; permanece restrito ao contexto de testes legados com chave explícita.
7. Operadores continuam enxergando nomes das filas de destino da mesma operação para transferir atendimentos, sem contadores de backlog dessas filas. Suas caixas pessoais/ownership permanecem protegidos.
8. APIs **novas**: `GET /v1/me/queues`, `GET /v1/admin/queue-grants`, `POST /v1/admin/queue-grants` e `DELETE /v1/admin/queue-grants/{user_id}/{queue_id}/{role}`.
9. Seed inicial concede SUPERVISOR e AUDITOR demonstrativos às filas N1/N2 **uma única vez**, não recriando grants removidos após reiniciar.
10. **Alembic** `0001_poc_baseline` + `0002_queue_grants`: SQLite persistente usa migrations em vez de `create_all`. Bancos existentes com esquema completo 0.5 são validados, copiados com `sqlite3.backup` (incluindo WAL) e *stamped* na revisão anterior à aplicação da nova tabela.

## Modelo de permissões implementado

| Papel | Leitura de filas | Gestão | Mensagens/Timeline |
|---|---|---|---|
| ADMIN | Filas da própria operação | Delegar acesso, vínculo, capacidade | **Não** por privilégio de admin |
| SUPERVISOR | Apenas grants SUPERVISOR da operação | Filas concedidas, com proteção de capacidade global entre filas | Apenas sessões permitidas; histórico transferido exige todos os grants |
| AUDITOR | Apenas grants AUDITOR da operação | Nenhuma escrita | Apenas sessões permitidas; histórico transferido exige todos os grants |
| OPERATOR | Destinos por nome para transferência | Presença própria, ações em sessões próprias | Somente atendimento atribuído |

**Importante:** esta fatia ainda usa `AuthUser.role` único por usuário. Multi-roles/grants combinados, o perfil MONITOR, auditoria de acesso detalhada, filtros de histórico por `queue_segment_id` e permissões em segmentos são **SPEC-006B / SPEC-007**, não declarar completos.

## Contrato administrativo de concessões (POC)

`POST /v1/admin/queue-grants` aceita JSON:

```json
{"user_id":"<id-do-usuario>","queue_id":"n1","role":"AUDITOR"}
```

O backend valida role real do usuário, operação e fila. Concessão idempotente. Revogação imediatamente efetiva no próximo request; não restaura no próximo bootstrap.

**Este é um endpoint inicial.** UI de grants/cadastros será desenvolvida na SPEC-007; não improvisar gestão manual das permissões diretamente em SQLite.

## Migração de esquema sem perda de dados

- `0001_poc_baseline` contém inventário fixado das 16 tabelas da POC 0.5, sem `queue_role_grants`. No banco existente completo, Alembic registra o baseline **sem executar `create_all` nele**.
- `0002_queue_grants` cria somente a tabela e o índice de concessões.
- Antes de modificar um SQLite preexistente, cria backup ao lado: `<banco>.before-spec006-<UTC>.bak`, com API nativa de backup (snapshot do WAL).
- Banco inesperadamente parcial é bloqueado com erro e exige diagnóstico. Não apaga tabelas ou dados para prosseguir.
- Migração repetida é no-op. Nova revisão Alembic deve ser explícita, com testes de upgrade e backup.
- `downgrade` destrutivo não é executado automaticamente. Para recuperar falha, **pare os serviços**, preserve o DB que falhou e restaure o snapshot somente após investigar e validar backups.
- `data/demo-credentials.txt`, handoffs, mensagens, sessões e hashes de senha não são substituídos.

**Gate antes de produção:** a revisão de baseline usa o snapshot do modelo POC 0.5 com inventário fixo de tabelas, uma ponte de compatibilidade. Congelar DDL reproduzível em futuras migrações/SQL Server e testar restauração completa ainda são tarefas enterprise.

## Testes adicionados

- `tests/test_queue_scoped_auth.py`: grants por fila, revogação em sessão aberta, dashboard/contagem/paginação com escopo, negativas de acesso HTTP, gestão restrita, N1→N2 com fail-closed, catálogo de destinos do operador.
- `tests/test_spec006_migrations.py`: banco limpo recebe Alembic, banco legado completo tem dados preservados + backup, repetição não duplica backup, esquema parcial é rejeitado sem apagar registros.
- Todos os 47+ gates da POC anterior permanecem em `start.cmd --check`.

**Validação nesta branch:** inspeção estática de integração e contratos realizada; **Pytest/Ruff/Vite/Windows ainda não foram executados nesta revisão**. Não promover PR até receber evidências.

## Comandos de homologação (PowerShell)

Pare o `start.cmd` anterior. Verifique alterações locais antes de trocar de branch:

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
git switch --track origin/feat/006-queue-scoped-auth-foundation
git pull --ff-only origin feat/006-queue-scoped-auth-foundation

# Testes em bancos temporários separados
.\start.cmd --check

# Só depois dos testes, iniciar e migrar o SQLite de homologação
.\start.cmd
```

Se branch já existir localmente: `git switch feat/006-queue-scoped-auth-foundation` em vez de `--track`. Se houver conflito ou divergência de commits, não executar reset --hard, enviar `git status` e `git log --oneline -5`.

**Teste funcional**: login Supervisor e Auditor N1/N2 com grants iniciais → Dashboard normal → Admin consulta grants, remove grant N2 do Auditor → sem novo login, Auditor só vê N1 → operador Ana continua atendendo e transferindo para N2 → Bruno continua aceitando normalmente → Admin restaura grant N2 → verificar histórico transferido, sem exposição entre filas.

## Pendências para concluir toda a SPEC-006 (próxima fatia B)

1. Tabela `session_queue_segments` com proveniência temporal, backfill confiável de mensagens/eventos e leitura **somente do segmento autorizado** em histórico de conversas transferidas.
2. Auditoria de acesso a mensagens, exportação e consultas sensíveis (`audit_access_events`), inclusive negações relevantes.
3. Normalizar grants/roles por operação e permitir múltiplos papéis de uma mesma identidade com grants específicos, sem depender de `AuthUser.role` singular.
4. Testes cross-operation completos, revogação sob concorrência, paginação e auditoria de metadados.
5. Promover para construção de CRUD/Admin somente após gates de segurança e migrations B.

## Regra de engenharia

Nenhum GitHub Actions, nenhum canal Teams real, nenhuma manipulação de dados do legado e **nenhum reset do SQLite** para fazer os testes passarem.
