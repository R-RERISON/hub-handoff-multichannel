# SPEC-007 — Incremento A0: Inventário administrativo desktop

**Branch:** `feat/007a0-admin-inventory-desktop`, a partir de
`feat/006c2-browser-viewport-capture` (QA `75ad2e4`). PR de
desenvolvimento Draft, sem alteração de main ou POC original.

## Contrato entregue

- `GET /v1/admin/overview` usa bearer individual no mesmo pipeline
  `authenticate`; exige role `ADMIN`, filtra exclusivamente a
  `operation_id` da identidade efetiva. Retorna operação, filas,
  memberships/role grants agregados, status de sessões por fila
  (queued/offered/active) e resumo de usuários/operadores.
- Sem IDs de conversas, conteúdo de mensagens, nota de transferência,
  credenciais, tokens, dados de auditoria ou comando de escrita.
- A área `/administracao` apresenta KPIs e tabela somente leitura,
  com loading, refresh e erro fail-closed (descarta dados anteriores).
  Campos de lifecycle aparecem como futuros, não falsos botões ativos.
- Sem migration e sem alteração de modelos, migrações, outbox ou Teams.

## Matriz de testes (código criado; ainda não executado nesta sessão)

| Caso | Comportamento esperado |
| --- | --- |
| GET sem bearer | 401 |
| Supervisor/Auditor/Operador | 403 |
| ADMIN demo | 200, duas filas, dois operadores, cinco contas, três grants |
| Operação externa inserida em TEMP | Não aparece em resposta |
| Campos sensíveis | Não retornados |
| POST/PATCH no endpoint de inventário | 405 |
| `start.cmd --check` | Pytest, Ruff, architecture tests, TypeScript/Vite |

## Teste Windows

Em worktree **isolada** do branch, com dependências locais instaladas:
```powershell
git fetch origin
git switch --track origin/feat/007a0-admin-inventory-desktop
.\start.cmd --check
```

Em laboratório `start.cmd --lab` descartável, autenticar
`admin.demo` com credencial somente do TEMP e abrir
`http://127.0.0.1:5173/administracao`. Verificar 1366×768
e 1920×1080, loading/erro, ausência de controles administrativos
mutáveis e isolamento da operação. **Não execute testes sobre
`data/handoff-poc.db`.**

## Pendências A1–C

- Esquema 007 versionado para lifecycle (DRAFT/ACTIVE/PAUSED/ARCHIVED),
  com migração aditiva **exclusivamente em TEMP**; decisão ADR específica.
- Proteção de despacho e intake para fila pausada/arquivada,
  tratamento atômico de ofertas pré-existentes, concorrência e rollback.
- CRUD de memberships/grants com audit trail transacional, optimistic
  concurrency e UX com confirmação.
- Testes negativos, revisão segurança/UX, aceite humano.
