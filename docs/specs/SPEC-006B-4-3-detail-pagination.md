# SPEC-006B-4.3 — Paginação limitada de histórico verificado

**Estado:** implementação publicada para homologação local (PR DRAFT).  
**Base:** `feat/006b4b-scoped-history-ux` (SPEC-006B-4.2; **97 Pytest, 10/10 frontend architecture, Ruff, TypeScript e Vite aprovados em 16/10/2026**).  
**Branch:** `feat/006b4c-history-detail-pagination`.

## Objetivo e invariantes

Eliminar o retorno ilimitado de mensagens e eventos do endpoint de histórico verificado, sem alterar o isolamento por fila, introduzir inferências de proveniência ou migrar o SQLite POC original.

- Autorização **server-side em cada página** por papel `SUPERVISOR/AUDITOR`, operação, grant explícito e referência a segmento/mensagem/evento `RUNTIME/VERIFIED`.
- O banco original permanece `revision=null`, **17 tabelas** e sem proveniência verificável. Não executar migração automática, `adopt`, `upgrade` ou `stamp` nele.
- Nenhum campo `SessionTransfer.reason`, assunto, nome do solicitante, fila atual ou dado de outra fila é exposto.
- A consulta anterior de listagem `GET /v1/history/verified-sessions` e o bloqueio conservador de `/messages` e `/timeline` permanecem inalterados.
- Segurança não é implementada por esconder a UI: cada requisição é autorizada na API, inclusive quando um grant foi revogado depois da página anterior.

## Contrato de API

`GET /v1/handoffs/{id}/verified-history?queue_id=n1&message_page=1&event_page=1&page_size=25`

| Parâmetro | Padrão | Validação |
|---|---:|---|
| `queue_id` | Obrigatório | Fila existente, concedida ao papel, da mesma operação |
| `message_page` | 1 | Inteiro de 1 a 1000 |
| `event_page` | 1 | Inteiro de 1 a 1000 |
| `page_size` | 25 | Inteiro de 1 a 50 |

As duas coleções são paginadas **independentemente**. Para cada uma, o SELECT mantém o filtro de proveniência e ordena de forma estável por `(created_at, id)`, aplicando `OFFSET` e `LIMIT page_size+1` **no banco**, não depois de carregar todos os textos/eventos. O registro excedente serve apenas para detectar a próxima página. Não expor `total_count` global nem IDs de segmentos de outras filas.

Além de `scope`, `queue_id`, `partial_history=true`, `messages[]` e `events[]`, a resposta inclui:

```json
{
  "page_size": 25,
  "message_page": 1,
  "event_page": 1,
  "message_next_page": null,
  "event_next_page": null
}
```

O objeto acima mostra só os **campos adicionais**; não substitui o restante do contrato de 006B-4.1. `null` em `*_next_page` significa fim **da coleção verificada consultada**, não ausência de conteúdo histórico oculto.

### Compatibilidade

Chamadas anteriores sem novos parâmetros continuam retornando `messages[]` e `events[]` com o mesmo formato, mas **no máximo 25 de cada** por requisição. O frontend 006B-4.3 implementa controles separados para avançar/voltar em cada coleção. Alternar ticket/fila/página de descoberta ou atualizar grants limpa o detalhe e volta `message_page` e `event_page` para 1.

## Segurança e QA

Testes Python sintéticos `tests/test_verified_history.py`:
1. Sessão N1 → N2: cinco mensagens N1 e mais uma N2; quatro eventos adicionais N1 (além dos eventos do fluxo); `page_size=2` permite inspecionar páginas separadas e não retorna o texto N2 ao auditor N1.
2. Avançar mensagens não modifica a página de eventos. `message_next_page` / `event_next_page` são determinísticos em conjunto estático de teste.
3. A revogação da concessão N1 nega a leitura da **próxima página** mesmo com a sessão Bearer anterior.
4. Rejeita `page_size=51`, `message_page=0` e `event_page=1001` com 422.
5. Banco sem Alembic continua negando o endpoint e mantém 17 tabelas.

Teste frontend `web/scripts/workspaces.test.mjs` exige controles read-only, parâmetros independentes, reset de paginação e `LIMIT` no backend.

### Gates Windows obrigatórios

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin

$branch = "feat/006b4c-history-detail-pagination"
$localBranches = @(git branch --list --format="%(refname:short)" $branch)
if ($localBranches -contains $branch) {
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

**Expectativa não executada neste PR:** 100 Pytest (97 anteriores + 3 testes), Ruff, 11/11 testes frontend (10 anteriores + 1), TypeScript e Vite. Conferir `integrity=ok`, `revision=null`, 17 tabelas no principal, e `rows_written=0` no dry-run.

### Limitações e rollback

- `OFFSET` é apropriado **apenas para POC**; paginação não mantém snapshot entre requisições concorrentes. Antes de produção, avaliar cursor por `(created_at, id)`, índices específicos, rate limiting, observabilidade e testes de carga. Não declarar paginação estável sob inserções concorrentes.
- A chamada ainda carrega duas coleções em uma requisição, porém cada uma está limitada de forma independente; não retorna `total_count` nem comprova integralidade do histórico.
- Auditoria imutável de consultas e concessões multirrole são requisitos **ainda pendentes** da SPEC-006B-5 e exigirão desenho de armazenamento/migração isolada; não tentar criar DDL implícita na POC.
- **Rollback:** `git switch feat/006b4b-scoped-history-ux` e `git merge --ff-only origin/feat/006b4b-scoped-history-ux`. Não há alterações de schema, dados nem migração.
