# SPEC-006B — Migrações versionadas e proveniência por segmento

**Status:** DESIGN / PREPARAÇÃO INICIAL — NENHUMA MIGRAÇÃO EXECUTÁVEL PUBLICADA  
**Baseline:** `feat/006-queue-scoped-authorization`, com 55 testes backend, Ruff e build frontend aprovados; 13 verificações funcionais RBAC aprovadas.  
**Dependência de promoção:** homologação ponta-a-ponta Ana N1 → Bruno N2 e persistência dos grants após reinicialização.

## Problema

`make_session_factory()` em `poc_db.py` executa `Base.metadata.create_all()`; o esquema de uma instalação já populada não possui histórico formal de revisões. `HandoffSession.queue_id` indica a fila **atual**. `SessionTransfer` preserva `from_queue_id/to_queue_id`, mas `Message` e `SessionEvent` não carregam o segmento de fila ao qual pertenciam; portanto, a SPEC-006A nega temporariamente histórico inteiro de qualquer atendimento transferido para supervisores/auditores, evitando leitura de outras filas.

## Primeiro resultado esperado

1. **Alembic, versionamento e reconciliação de bancos existentes:** bootstrap seguro para SQLite antigo sem apagar registros nem presumir que `create_all` equivale a migração. Banco novo e banco existente devem produzir o **mesmo estado-alvo versionado**.
2. **Segmentos de fila:** um ticket pode percorrer N1 → N2 → outras filas mantendo intervalos fechados/abertos da responsabilidade. A autorização de supervisão/auditoria é avaliada na fila do segmento de origem de cada mensagem e evento, não apenas `handoff_sessions.queue_id`.
3. **Concessões multirrole:** evolução planejada de `AuthUser.role` para role assignments scoped sem mudar abruptamente o login/URLs; a migração terá dual-read/dual-write ou adapter transitório, testes e política de fallback.
4. **Rastreabilidade de leitura:** trilhas de acesso a conteúdo e alterações de permissões, sem armazenar bearer token, segredo ou dados desnecessários.

## Contrato para as migrações

- Executar somente com API e dispatcher parados. Bloquear o startup se DB requer upgrade e a migration ainda não foi aplicada, quando o gate Alembic substituir `create_all`.
- Registrar backup pré-migração fora do repositório, SHA-256, integridade SQLite (`PRAGMA integrity_check`) e versão do schema.
- Não usar `DROP TABLE` nem sobrescrever `handoff_sessions/messages/session_events` durante a adoção de baseline.
- A migration baseline deve inspecionar existência e assinatura do schema anterior antes de realizar `stamp`. Em caso de divergência, interromper sem alterar o banco.
- Definir operações reversíveis para DDL aditiva. Rollback de dados históricos deve ser **forward fix/restauração** testada, não exclusão irreversível.
- Transação e concorrência SQLite estão limitadas a nó único; não pressupor que `BEGIN IMMEDIATE` funcione em SQL Server.
- Testes rodam com SQLite temporário, não com `data/handoff-poc.db` de homologação.

## Modelo inicial proposto

`session_queue_segments`:
- `id` UUID/string; `session_id`; `queue_id`; `ordinal` (índice por sessão); `started_at`, `ended_at`;
- `transfer_id` (nullable); `responsible_operator_id` opcional; `provenance_state`: VERIFIED|INFERRED|AMBIGUOUS;
- UNIQUE (`session_id`, `ordinal`); índice (`queue_id`, `started_at`).

`message_queue_provenance`:
- `message_id` PK/FK, `segment_id` FK, `assigned_by` MIGRATION|RUNTIME, `confidence` VERIFIED|INFERRED|UNDETERMINED.
- Para eventos históricos não determinísticos, **não atribuir segmento por chute**. Metadados legados ambíguos ficam UNDETERMINED e restritos até revisão autorizada.

`session_event_queue_provenance`:
- `event_id` PK/FK, `segment_id` nullable, `confidence` e `created_at` preservados.

**Importante:** `SessionTransfer.created_at` registra a fronteira cronológica, mas timestamps e concorrência legadas podem ser ambíguos. Um backfill não pode conceder leitura a segmento se a atribuição não for suficientemente comprovável. Nunca usar só a fila atual para todo o histórico.

## API e autorização

- `GET /v1/handoffs/{id}/messages`: para papéis scoped, retorna apenas mensagens de segmentos concedidos, com paginação/filtros autorizados; o operador atual tem o contexto operacional mínimo explicitamente permitido pela política.
- `GET /v1/handoffs/{id}/timeline`: eventos segmentados e sem vazamentos de IDs/conteúdo; contadores obedecem o mesmo escopo.
- Para tickets multi-fila, listas podem mostrar contexto minimizado de tickets que passaram pela fila do usuário; a consulta detalhada retorna somente segmentos permitidos.
- Não implementar uma UI de auditoria completa nesta SPEC; o portal é SPEC-009.

## Gates obrigatórios

1. Instalação limpa e upgrade de SQLite POC 0.5/006A existente, com backup/verificação/replay e preservação de todas as linhas originais.
2. Simulação de falha durante upgrade → reexecução segura, nenhuma tabela/índice/row parcialmente perdidos.
3. Transferência N1→N2 com mensagens em ambas as filas: Auditor N1 não vê conteúdo N2 e Auditor N2 não vê conteúdo N1.
4. Mensagens de proveniência ambígua não aparecem por inferência permissiva.
5. Revogação de grants vale no request seguinte inclusive para download e histórico.
6. Login, despacho FIFO/round robin, pop-up, composer, transferência/encerramento e outbox PENDING_ADAPTER preservados.
7. Gate local `.\start.cmd --check`; testes novos de schema, invariantes e isolamento; nenhum GitHub Actions.
8. UX não poderá fingir ausência de mensagens: quando o histórico for truncado por segurança, exibir indicação controlada, sem revelar filas não autorizadas.

## Execução incremental

- **006B-1:** inventário e assinatura formal do schema existente; ferramenta de backup/restore/migration dry-run; infraestrutura Alembic com baseline do esquema real. Não aplicar automaticamente em startup.
- **006B-2:** DDL aditiva para segmentos, proveniência e trilha de acesso; testes com datasets antigos e novos.
- **006B-3:** dupla gravação de contexto de fila em cada nova mensagem/transferência/evento; backfill conservador dos legados.
- **006B-4:** autorização por segmento nas leituras, testes de IDOR/cross-queue e remoção do bloqueio total temporário da 006A.
- **006B-5:** grants multirrole, acesso de auditor e monitor, compatibilidade da POC e documentação de migração/reversão.

**Gates de promoção:** nenhum PR de migração pode ser promovido sem execução dos testes locais e restauração de uma cópia sintética/populada. Nunca aplicar migração experimental diretamente no banco de homologação original.
