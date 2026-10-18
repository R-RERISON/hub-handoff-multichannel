# SPEC-006B-3.3 — Reconstrução histórica em dry-run (somente leitura)

**Estado:** código e testes publicados em branch; **gate Windows pendente**.  
**Base:** `feat/006b3b-events-audit` / PR #21. Gate automatizado da 006B-3.2 aprovado no Windows: 78 Pytest, Ruff, 9 testes de frontend, TypeScript e Vite. A auditoria original retornou `NOT_MIGRATED`, `backfill_applied=false`, 17 tabelas e `revision=null`.

## Problema e decisões

`handoff_sessions.queue_id` registra a **fila atual**, e `session_transfers` registra limites de troca; `messages` e `session_events` antigos não carregam ID do segmento. Uma mensagem anterior à troca não pode ser atribuída à fila final N2 apenas porque `handoff_sessions.queue_id=n2`.

O dry-run **não executa backfill**, não escreve qualquer tabela e **não autoriza histórico**. Mesmo uma sequência de transferências coerente gera apenas **candidato a revisão** (`review_candidate`), não `VERIFIED`. O objetivo desta fatia é aferir quantitativamente se há evidência reconstruível e quais casos exigem revisão humana/novo método de comprovação.

## Contrato do analisador

Arquivo `src/handoff_hub/provenance_dry_run.py`, executado com:

```powershell
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
# Ou em uma COPIA: --database ".\data\backups\...\copia.db"
```

1. Primeiro `verify_database` confere integridade SQLite, chaves estrangeiras e assinatura de tabelas, sem DDL.
2. Abre a base com URI `mode=ro`, executa `PRAGMA query_only=ON` e lê uma **transação consistente**, sem usar SQL de escrita.
3. Consulta apenas campos de relacionamento, operação/fila, tipo/autor de evento e timestamps; **não consulta** `messages.content`, `requester_label`, `subject`, `SessionTransfer.reason`, credenciais ou tokens.
4. Para cada atendimento sem proveniência já gravada, compara cadeia de transferências, identidade da fila origem/destino, operação, horários crescentes, eventos `TRANSFERRED` correspondentes e fila final.
5. Sem transferência ou sem evidência suficiente, a sessão é considerada **indeterminada**, mesmo que a fila atual seja conhecida.
6. Com cadeia consistente, classifica apenas a **linha temporal como candidata à revisão**. Mensagens com timestamp estritamente dentro de um intervalo entram em `message_assessment.review_candidate`. Mensagens exatamente no instante da mudança entram em `boundary_ambiguous`. Registros fora dos intervalos ou com datas inválidas não são classificados.
7. Sessões que já possuem linhas em `session_queue_segments` ou qualquer mapeamento anterior são excluídas de reavaliação (`already_has_provenance`).
8. Não atribui eventos antigos a segmentos neste dry-run: `event_assessment.not_assessed=events`. O evento `TRANSFERRED` é apenas evidência para validar a cadeia.
9. Totais das categorias precisam fechar com os totais do banco. Qualquer divergência interrompe o relatório.

## Saída e significado

```json
{
  "mode": "DRY_RUN_READ_ONLY",
  "schema_revision": null,
  "status": "ANALYSIS_ONLY",
  "backfill_applied": false,
  "rows_written": 0,
  "safe_for_history_authorization": false,
  "candidate_is_verified": false,
  "session_assessment": {
    "review_candidate": 0,
    "no_transfer_evidence": 0,
    "missing_transfer_event_evidence": 0,
    "invalid_timestamps": 0,
    "inconsistent_queue_chain": 0,
    "current_queue_mismatch": 0,
    "already_has_provenance": 0
  },
  "message_assessment": {
    "review_candidate": 0,
    "boundary_ambiguous": 0,
    "invalid_timestamp": 0,
    "not_assessed": 0
  }
}
```

Os valores acima são **ilustrativos**, não resultado real; no relatório completo, além dessas chaves, são exibidos totais e eventos. Nenhuma contagem representa autorização para ler mensagens entre filas.

## Gates de segurança

- `READ_ONLY`: a biblioteca SQLite abre a URI em modo leitura e aplica `query_only`, sem SQL de escrita. Não há `INSERT/UPDATE/DELETE` nesta rotina.
- `NO_PII_OUTPUT`: relatório contém exclusivamente agregados; não retornar IDs individuais, texto de mensagem, motivo, usuário ou operador.
- `NO_AUTOMATIC_ASSIGNMENT`: nem mesmo uma linha temporal consistente é elevada a `VERIFIED`.
- `NO_AUDITOR_UNLOCK`: os bloqueios por fila da SPEC-006A permanecem. A SPEC-006B-4 só poderá consultar segmentos verificados e autorizados; candidatos de dry-run não servirão de grant.
- `NO_SCHEMA_CHANGES`: roda também no SQLite não versionado do usuário, que continua com 17 tabelas e `revision=null`.
- `NO_LEGACY_MUTATION`: dados existentes com proveniência já escrita são preservados; não altera `session_transfers`, mensagens, ofertas ou eventos.

## Homologação Windows

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
git switch --track origin/feat/006b3c-history-dry-run
.\start.cmd --check
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
```

Se a branch local **já existir**, usar `git switch feat/006b3c-history-dry-run` seguido de `git merge --ff-only origin/feat/006b3c-history-dry-run`, em vez de `switch --track`.

**Esperado:** Pytest, Ruff, arquitetura frontend, TS e Vite aprovados. SQLite principal: 17 tabelas, `revision=null`, integridade `ok`. Dry-run: `mode=DRY_RUN_READ_ONLY`, `status=ANALYSIS_ONLY`, `backfill_applied=false`, `rows_written=0` e `safe_for_history_authorization=false`. As contagens reais variarão conforme registros criados desde a inspeção.

## Limitações conhecidas e decisão seguinte

- `created_at` pode ter sido preenchido em instantes muito próximos de eventos e transferências, sem um limite transacional histórico explícito; esses casos são marcados como ambíguos.
- O campo `queue_id` atual sozinho não comprova posse anterior, especialmente em sessões sem `session_transfers`.
- Transferências não instrumentadas em versões antigas, edição manual do SQLite ou ausência de `TRANSFERRED` bloqueiam a classificação.
- A cadeia consistente **não comprova que os dados históricos devam ser liberados a outros perfis**. Aprovação humana e evidência de integridade do histórico serão obrigatórias antes de qualquer backfill persistente.
- A reconstrução de eventos antigos precisa de regra específica por tipo de evento. Não classificar eventos só por timestamp.

**Próximo incremento recomendado:** avaliar indicadores reais do dry-run, definir um plano de reconciliação assistida com evidências e aprovação explícita por sessão/segmento e então implementar a SPEC-006B-4 para os eventos **novos já verificados** — sem liberar histórico legado ambíguo.
