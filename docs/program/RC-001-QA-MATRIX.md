# RC-001 — Matriz única de QA e aceite

**Status:** todos os gates NOT_RUN. Nenhum PASS herdado de PRs antigos.  
**Candidato:** `integration/rc-001-consolidated-poc-20261019`.  
**Ambiente:** Windows, worktree separada, laboratório 100% TEMP sintético.

## Preparar a mesma revisão para todos os cenários
~~~powershell
git fetch origin
$ref = 'origin/integration/rc-001-consolidated-poc-20261019'
$sha = (git rev-parse $ref).Trim()
$qa = Join-Path $env:TEMP 'handoff-rc001-qa'
if (Test-Path -LiteralPath $qa) { throw 'Worktree QA ja existe; nao sobrescrever' }
git worktree add --detach $qa $sha
if ($LASTEXITCODE -ne 0) { throw 'Falha criando worktree QA' }
Set-Location $qa
git rev-parse HEAD
git status --short
~~~

Instalar/associar dependências no worktree conforme `docs/setup-one-command.md`.
É proibido usar `start.cmd` sem `--lab` ao iniciar serviços para este QA.

## Gates de aceite único
| ID | Escopo | Critério de aceite | Estado |
|---|---|---|---|
| G00 | Integridade da baseline | SHA, árvore, diff, ausência de secrets/dados binários locais, políticas | NOT_RUN |
| G01 | Build e regressão | `.\start.cmd --check` exit 0, todos os testes Python/Ruff/frontend/TypeScript/Vite | NOT_RUN |
| G02 | Segurança RBAC | testes B0.1/B1.0, 401/403/404, cross-operation, grants, revogação | NOT_RUN |
| G03 | Persistência | TEMP 006b4, backup, upgrade opt-in 007a2, integridade, rollback, CAS | NOT_RUN |
| G04 | Fluxo N1→N2 | intake, fila, oferta, aceite, transferência, histórico segmentado, notas privadas | NOT_RUN |
| G05 | Personas | Operador, Supervisor, Auditor, Administrador e sessão revogada, sem conteúdo indevido | NOT_RUN |
| G06 | Administração | Criação/lifecycle de filas, B1.0 pessoas, nenhum grant implícito | NOT_RUN |
| G07 | UX desktop | Edge/Chrome 1366×768 e 1920×1080, zoom 200%, teclado, erros/empty states | NOT_RUN |
| G08 | Evidências e auditoria | logs sanitizados, journals, ausência de segredos/PII real, fail-closed | NOT_RUN |
| G09 | Review independente | diff consolidado, documentação, dependências, branches alternativas e riscos | NOT_RUN |
| G10 | Aceite humano | cenário integrado demonstrado, evidências e aprovação formal explícita | NOT_RUN |

## Comandos para regressão
~~~powershell
.\start.cmd --check
if ($LASTEXITCODE -ne 0) { throw 'G01 reprovado' }

.\.venv\Scripts\python.exe -m pytest -q tests\test_spec007_people_boundaries.py tests\test_spec007_b1_people_inventory.py tests\test_spec007_queue_lifecycle.py
if ($LASTEXITCODE -ne 0) { throw 'G02/G03 reprovado' }

.\.venv\Scripts\python.exe scripts\release_probe.py
if ($LASTEXITCODE -ne 0) { throw 'G02 probe reprovado' }
~~~

## UX integrada
Iniciar `.\start.cmd --lab` e confirmar o diretório TEMP com `synthetic.db`.
A migration 007a2 para lifecycle é opt-in e deve ser feita SOMENTE em cópia
do laboratório com backup e inspeção antes do upgrade. Se não habilitada,
G03/G06 permanecem BLOCKED: não forçar schema no SQLite original.

Para cada passo, anotar `run_id, SHA, executor, persona, queue_id sintética, browser,
viewport real, cenário, esperado, observado, PASS/FAIL/BLOCKED, evidência sanitizada`.
Não anexar capturas com tokens, senhas ou dados reais.

## Regra de parada
Qualquer falha crítica de isolamento, segurança, integridade, regressão, rollback
ou manipulação do banco original bloqueia a promoção. Corrigir na RC sob novo
SHA e revalidar os gates afetados. Sem GitHub Actions e sem merge automático.

## Registro de QA do snapshot
| Campo | Estado |
|---|---|
| Candidate SHA conferido pelo executor | NOT_RUN |
| G00–G10 | NOT_RUN |
| Evidência browser | NENHUMA |
| Aceite usuário | NÃO REALIZADO |
| Integração main | NÃO AUTORIZADA |
