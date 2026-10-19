# SPEC-007/A1.2 — Estados das filas e bloqueio operacional

Estado: CODED / WINDOWS_QA_PASS / SECURITY_REVIEW_REQUIRED / INTEGRATION_PENDING.
Branch: feat/007a2-queue-lifecycle. Base: A1.1 8fd9294, validada.
Reteste Windows: commit 6503d30.
A migração é EXCLUSIVAMENTE opt-in no SQLite TEMP sintético.

## Esquema separado e seguro

A nova revisão Alembic 007a2_queue_lifecycle é sucessora de 006b4.
Cria queue_lifecycle (queue_id, state, version, changed_at, changed_by)
e queue_lifecycle_events (id, queue_id, operation_id, actor_user_id,
from_state, to_state, version, created_at), com FK e índices.
Não altera a tabela legada queues, nem realiza backfill.
Fila existente sem registro explícito permanece ACTIVE/version 0.
Fila nova criada após migração começa DRAFT/version 1,
com evento auditado na mesma transação do QUEUE_CREATED.

## Máquina de estados

DRAFT -> ACTIVE ou ARCHIVED.
ACTIVE -> PAUSED, apenas se zero QUEUED/OFFERED/ACTIVE.
PAUSED -> ACTIVE ou ARCHIVED; arquivar também exige fila livre.
ARCHIVED -> nenhum estado; terminal nesta fase.
API: PATCH /v1/admin/queues/{queue_id}/state
Payload: {"state":"PAUSED","expected_version":2}.
A versão é conferida atomicamente com BEGIN IMMEDIATE.
ADMIN efetivo e operation_id vinculada à identidade.
Estados inválidos/versão desatualizada/fila ocupada: 409.
Fila externa ou inexistente: 404 sem detalhes.
Sem migration 007a2: 503 e sem escrita. Auditoria indisponível:
503 com rollback. Nunca excluir fila/histórico durante transição.

Intake, despacho manual, oferta manual, despacho automático e
transferência bloqueiam filas não ACTIVE. Destinos de transferência
excluem filas DRAFT/PAUSED/ARCHIVED. As sessões em andamento podem
ser concluídas; pausa com trabalho em aberto é recusada.

## Execução segura

Em um novo laboratório TEMP 006b4, com API e despachante parados:
python -m handoff_hub.schema_admin --database <TEMP>/synthetic.db
  --backup-dir <TEMP>/schema-backups upgrade-lifecycle --confirm-offline

Executar os argumentos como uma única linha. Inspecionar novamente:
python -m handoff_hub.schema_admin --database <TEMP>/synthetic.db inspect

O comando de criação de banco permanece fixado na revisão 006b4.
O upgrade 007a2 não é invocado automaticamente pelo launcher.
O caminho original data/handoff-poc.db é expressamente recusado.
Após o upgrade e a inspeção, o mesmo laboratório pode ser iniciado para
homologação visual com `.\start.cmd --lab --lab-dir "<TEMP>"`. O launcher
valida e retoma tanto 006b4 quanto 007a2 sem criar, resetar ou migrar o banco.
Rollback: interromper todos os serviços e restaurar o backup verificado
sob aprovação humana; downgrade destrutivo é recusado quando existem
estados ou eventos. Não copiar senhas, tokens ou o SQLite para GitHub.

## Critérios de qualidade

Executar start.cmd --check completo no SHA do PR, incluindo Python,
Ruff, contratos frontend, TypeScript e Vite. Executar os novos
testes test_spec007_queue_lifecycle.py (migration, segurança, CAS,
rollback, legado, transições, fila ocupada, bloqueios).
Inspecionar UI em Edge/Chrome desktop 1366x768 e 1920x1080,
foco Tab, confirmação de alteração e mensagens de erro.
Documentar a semântica de filas antigas ACTIVE/0 e revisar segurança
do fluxo no diff antes de integrar. Não realizar merge automático.

## Evidência Windows — 2026-10-19

No commit `6503d30`, `.\start.cmd --check` terminou com exit code 0:
162 testes Python aprovados, 1 ignorado, Ruff aprovado, 16 testes de
arquitetura frontend, TypeScript e Vite (1.601 módulos).

No laboratório TEMP, o backup foi validado antes do upgrade offline 006b4 →
007a2. As contagens de todas as tabelas existentes foram preservadas; as
tabelas de ciclo de vida iniciaram vazias. O launcher retomou o mesmo banco
migrado antes e depois de registrar as transições, sem migrar ou semear dados.

No navegador integrado do VS Code, a fila sintética `qa-lifecycle` percorreu
DRAFT/v1 → ACTIVE/v2 → PAUSED/v3 → ARCHIVED/v4; cada transição retornou
HTTP 200 e auditoria APPLIED. A fila terminou com zero memberships e grants.
Foco por Tab alcançou “Confirmar mudança”; não houve overflow horizontal em
1366×768 ou 1920×1080. Capturas PNG verificadas estão no diretório
TEMP `handoff-qa-006b4-air5z1nu\qa-evidence-a1.2`.

Segurança e integração continuam pendentes. Não houve merge nem promoção à
`main`.
