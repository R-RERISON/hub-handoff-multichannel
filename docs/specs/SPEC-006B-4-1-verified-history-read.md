# SPEC-006B-4.1 — Leitura isolada por segmento verificado

**Estado:** Implementação inicial publicada em branch para homologação local. **Não promovida.**

**Base:** SPEC-006B-3.3, commit `4bc00af` (dry-run histórico).
**Branch:** `feat/006b4a-verified-segment-read`.
**Pré-requisitos:** CONSTITUTION.md, AGENTS.md, SPEC-006A, SPEC-006B-2/3.1/3.2/3.3.

## 1. Objetivo e recorte

Habilitar a **primeira leitura por fila** de mensagens e eventos cuja proveniência foi criada e marcada como `VERIFIED` pelo runtime em bancos **explicitamente migrados** à revisão `006b2_queue_provenance`. Não interpretar o dry-run como autorização e não mapear histórico anterior automaticamente.

O banco principal POC segue **não versionado, com 17 tabelas**. Não executar `adopt`, `upgrade`, `stamp` nem restaurar cópias sobre o principal para testar esta fatia.

## 2. Contrato REST

`GET /v1/handoffs/{handoff_id}/verified-history?queue_id=n1`

Exige `Authorization: Bearer <token>` real de conta **SUPERVISOR** ou **AUDITOR**. A antiga `X-POC-Key` continua disponível **somente em testes criados explicitamente com `create_app(api_key=...)`**; não concede o papel correto para este endpoint. Um administrador e um operador usam suas rotas já existentes, não esta nova superfície de leitura.

Resposta autorizada (exemplo sintético):

```json
{
  "scope": "RUNTIME_VERIFIED_QUEUE_ONLY",
  "queue_id": "n1",
  "partial_history": true,
  "messages": [{"id": "id-sintetico", "sender": "USER", "content": "Teste", "created_at": "2026-10-16T12:00:00"}],
  "events": [{"type": "QUEUED", "actor": "demo-bot", "at": "2026-10-16T12:00:00"}]
}
```

**Não** retorna metadados do atendimento, fila atual, nomes de outras filas, motivos de transferência, IDs de outros segmentos ou contadores globais. `partial_history=true` é intencional e **não** indica que a conversa original esteja vazia ou completa.

### Condições cumulativas da leitura

1. Papel SUPERVISOR/AUDITOR autenticado; escopo de operação do principal validado.
2. `queue_role_grants` autoriza explicitamente `queue_id` ao mesmo papel, verificado a **cada requisição**, inclusive após revogação.
3. Ticket pertence à operação do principal. Ausência de permissão, operação ou segmento verificável não expõe o recurso (404); papel incompatível retorna 403; não autenticado 401.
4. O banco deve ter `ProvenanceRecorder.enabled=true` (migração 006B-2 conhecida e tabelas presentes). O SQLite original retorna **404**, sem criar tabelas.
5. O segmento deve corresponder a `session_id` + `queue_id` e possuir `provenance_state=VERIFIED`.
6. Cada mensagem/evento precisa estar vinculado ao **mesmo ticket** e a esse segmento, com `confidence=VERIFIED` e `assigned_by=RUNTIME`. `INFERRED`, `UNDETERMINED`, `MIGRATION`, órfãos ou referências de outra sessão não são retornados.
7. Sem fallback por `handoff_sessions.queue_id`, timestamp, ordem ou evento de transferência. Sem backfill e sem alterações persistidas.

## 3. Limite de autorização existente

O atalho é **exclusivo** para o `GET .../verified-history`; a checagem antiga de `require_handoff` continua ativa em `/messages`, `/timeline` e demais rotas de supervisor/auditor. A nova rota executa `require_queue` antes de consultar conteúdo e considera somente o segmento explicitamente solicitado.

**Por que não substituir ainda `/messages` e `/timeline`?** Esses contratos alimentam a interface existente, incluem notas internas de transferência no timeline e possuem apresentação orientada ao ticket completo. Liberá-los sem adequar a UX de histórico parcial pode provocar vazamento ou dar a falsa impressão de conversa completa. A SPEC-006B-4.2 deverá integrar leituras filtradas, listagens de descoberta com metadados mínimos e indicadores de truncamento, após gates negativos desta fatia.

## 4. Segurança, testes e aceite

Arquivo: `src/handoff_hub/verified_history.py`.
Tests: `tests/test_verified_history.py`.

Cobertura adicionada, em bases descartáveis criadas dentro de `tmp_path`:
- Ticket novo N1→N2: Auditor N1 não lê mensagem N2; Supervisor N2 não lê N1; nota interna de transferência não aparece.
- Autenticação obrigatória; admin/operador não usam esta rota; auditor sem grant não obtém histórico N2; acesso a ID inexistente devolve 404.
- Revogação de grant na mesma sessão passa a negar a **próxima consulta**.
- `confidence=UNDETERMINED` e `assigned_by=MIGRATION` não são exibidos; eventos sem confiança verificada tampouco.
- Referência artificial cruzada entre tickets não permite ler mensagem de outra sessão.
- SQLite original continua com 17 tabelas, sem `alembic_version`; endpoint não libera o legado e nem altera a política 006A.

**Gates locais obrigatórios (não executados por CI):**

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
$branch = "feat/006b4a-verified-segment-read"
if (@(git branch --list --format="%(refname:short)" $branch) -contains $branch) {
    git switch $branch
} else {
    git switch --create $branch --track "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw "Falha ao selecionar branch" }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar branch" }

.\start.cmd --check
if ($LASTEXITCODE -ne 0) { throw "Gate de testes falhou" }
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
if ($LASTEXITCODE -ne 0) { throw "Inspeção falhou" }
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
if ($LASTEXITCODE -ne 0) { throw "Dry-run falhou" }
```

**Aceite:** Pytest/Ruff/arquitetura frontend/TypeScript/Vite verdes; inspeção do original com `integrity=ok`, `revision=null`, 17 tabelas; dry-run sem escrita, sem candidato verificado; testes de IDOR negativos e integração N1/N2 sintética comprovados. Não há migração no principal nem execução de testes Windows assumida antecipadamente.

## 5. Limitações e rollback

- Leitura disponível apenas por ID do ticket **já conhecido**; não há busca/listagem de tickets transferidos para papéis escopados nesta fatia. A listagem/dash atuais continuam negando todos os tickets transferidos.
- Ainda não há trilha persistente imutável por acesso, papéis múltiplos nem validação de escala/paginação. O endpoint é de **laboratório**, não de produção e não deve ser publicado além de localhost.
- O conteúdo completo dos segmentos verificados é retornado sem paginação; limitar esse contrato antes de produção.
- **Rollback de código:** retornar à branch `feat/006b3c-history-dry-run` sem tocar no SQLite. Nenhum DDL, `DROP`, migração automática ou mudança de dados foi introduzida.
- O próximo gate do roadmap, SPEC-006B-4.2, integra UI e contratos existentes **somente** com filtragem/visibilidade comprovadamente segura; SPEC-006B-5 aborda concessões multirrole.
