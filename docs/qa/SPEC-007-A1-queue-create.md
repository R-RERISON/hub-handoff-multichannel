# SPEC-007 / A1.1 — Cadastro de fila com journal transacional

**Tipo:** implementação de fatia vertical, sem migração. **Escopo desktop**.
**Base homologada automatizada:** A0 `86a1438` (146 passed, 1 skipped).
**Status deste incremento:** CODED / WINDOWS_QA_REQUIRED / SECURITY_REVIEW_REQUIRED.
**Banco permitido:** SQLite TEMP 006b4 exclusivamente sintético.

## Contrato backend

`POST /v1/admin/queues`: exige bearer de ADMIN efetivo,
sem aceitar `operation_id` no corpo como autoridade. Corpo:
`{"id":"suporte-n3","name":"Suporte N3"}`. O identificador é estável,
de 2 a 40 caracteres, minúsculo ASCII com dígitos e hífen, começando
com letra. Nome de 3–120 caracteres, sem controles ou espaços extremos.

- 201: `id`, `name`, `operation_id` efetiva, `audit:"APPLIED"`.
- 401: sem token; 403: não ADMIN; 409: ID existente, mesmo de outra operação.
- 422: validação; 503: banco sem journal de segurança 006b4.
- Atomicidade: `BEGIN IMMEDIATE` no SQLite, fila+evento
  `security_decisions(action=QUEUE_CREATED, outcome=APPLIED)` na
  **mesma transação**. Uma falha do journal não pode confirmar criação.
- Nenhum grant ou membership novo é criado automaticamente.
- Idempotência em A1.1: o mesmo ID reapresentado retorna 409 sem
  nova gravação, não é UPSERT. Concurso de admins é serializado pelo SQLite.

**ATENÇÃO:** `security_decisions` funciona como jornal auditável
temporário desta fatia; a SPEC-007 exige entidade administrativa própria
e revisão semântica em A1.2/C. Não anunciar WORM ou auditoria corporativa.

## UX

O portal Administração permite cadastrar fila, mas o inventário é
somente leitura. Feedback de sucesso somente após resposta da API e
`GET /admin/overview` subsequente. Erro de criação não preserva
conteúdo potencialmente incorreto em painéis de outro escopo.
Nenhuma ação de ativar/pausar/arquivar é oferecida.

## Testes escritos (pendentes de execução)

1. 401 sem bearer e 403 para Supervisor, Auditor, Ana, Bruno.
2. 201 somente ADMIN + fila persistida, evento `QUEUE_CREATED` exatamente
   uma vez; membership e grants zero; inventário atualizado.
3. Conflito por ID local ou de outra operação: 409 sem revelar nome externo.
4. Validação inválida: 422 sem mutação.
5. Trigger SQLite que aborta journal: toda criação é revertida.
6. SQLite POC sem Alembic 006b4: 503, sem criação nem esquema implícito.
7. Duas requisições concorrentes no mesmo ID: apenas uma 201 e um evento.

## Gate para QA em Windows

Usar **worktree isolada** de `origin/feat/007a1-queue-create-audited`,
não a branch funcional nem `data/handoff-poc.db`:

```powershell
git fetch origin
$qa = Join-Path $env:TEMP 'handoff-spec007-a1'
if (Test-Path -LiteralPath $qa) { throw 'QA existente: use nome novo' }
git worktree add --detach $qa origin/feat/007a1-queue-create-audited
Push-Location $qa
git rev-parse HEAD
.\start.cmd --check
Pop-Location
```

Conforme a instalação local, configure dependências isoladamente ou
reuse junctions verificadas da worktree principal (sem copiar credenciais).
Em seguida crie lab TEMP **novo** por `start.cmd --lab` e autentique como
`admin.demo` com credencial gerada somente ali. Verifique na UI
1366×768 e 1920×1080: criação, 409, refresh, erro, foco, teclado,
sem controles escondidos, estado pós-salvamento. SQL triggers, esquemas
sem versão e concorrência devem rodar **somente em bancos de pytest**.

## Próxima fatia A1.2

Estados versionados `DRAFT/ACTIVE/PAUSED/ARCHIVED` exigirão
migração aditiva opt-in, verificação schema_admin, propagação de
bloqueio de intake/despacho, tratamento de ofertas/atendimentos
em andamento, auditoria administrativa versionada e rollback.
Não habilitar pausas em A1.1.

## Segurança e release

Sem Teams real, Entra, SQL Server, multi-host, dados reais, POC original
ou migração automática. PR Draft empilhado em A0. Validar gates por
SHA e revisar diff/ameaças. Merge exige autorização humana, não
ocorre durante esta entrega.
