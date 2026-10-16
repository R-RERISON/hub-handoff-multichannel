# SPEC-006B-5.2 — Auditoria de decisões de segurança (primeira fatia)

**Estado:** IMPLEMENTED / AWAITING WINDOWS GATES — não aprovado para produção.  
**Base de trabalho:** `feat/006b5a-history-access-audit` (SPEC-006B-5.1, 105/105 Python, Ruff, 11/11 frontend, TypeScript e Vite aprovados em 16/10/2026).  
**Branch:** `feat/006b5b-security-decisions-journal`.

## Objetivo

Registrar eventos mínimos de segurança dos leitores de histórico verificado:
- pedidos negados por `HTTP 403/404` **depois da autenticação**, quando o request alcança a função FastAPI de listagem/detalhe;
- mudanças reais (ativação ou revogação) em `PATCH /v1/admin/queue-grants`.

Não alterar as decisões RBAC ou expor campos de outras filas. **Não** registrar nomes, conteúdo, título, justificativa de transferência, session_id solicitado em negativa, token Bearer, corpo do request, senha ou IP. As tentativas negadas não criam histórico de leitura bem-sucedida.

## Modelo e versionamento

- Revisão `006b4_security_decisions` sobre `006b3_history_access_audit`: acrescenta uma tabela `security_decisions` com IDs aleatórios, `actor_user_id` (FK), `actor_role`, `operation_id`, `queue_id` (FK nullable), `target_user_id` (FK nullable), `action`, `outcome`, `created_at`. Índices por operação/tempo e ator/tempo.
- `SECURITY_METADATA` fica separada do `Base.metadata`. `make_session_factory()` e `start.cmd` não aplicam essa DDL.
- Novo comando offline `schema_admin upgrade-security --database <banco-isolado> --confirm-offline` só aceita `006b3`, cria backup de origem e verifica SHA-256, integridade/índices e invariância dos contadores. O comando `upgrade-audit` continua estritamente 006b2→006b3; `upgrade` continua 006b1→006b2.
- `create_new` cria **apenas um banco que não exista** em 006b4; dados anteriores jamais são migrados automaticamente. `verify_database` valida 006b4 e suas tabelas, além das revisões anteriores.
- `provenance_dry_run` e `provenance_audit` reconhecem `006b4` para leitura agregada, nunca para backfill ou autorização histórica de dados legados.
- Downgrade com eventos `security_decisions` presentes é recusado para evitar descarte de evidências. Ainda não é WORM/imutabilidade criptográfica.

## Contrato e decisões

| Ação | Resultado | Forma de gravação |
|---|---|---|
| `HISTORY_LIST_DENIED` | `DENIED` | transação separada após 403/404 em listagem verificada |
| `HISTORY_DETAIL_DENIED` | `DENIED` | transação separada após 403/404 em detalhe verificado |
| `GRANT_ENABLED` | `APPLIED` | **mesma transação** do grant administrativo |
| `GRANT_REVOKED` | `APPLIED` | **mesma transação** da revogação administrativa |

### Invariantes de segurança

1. Negativas não mudam `403` ou `404`, mesmo se o journal estiver indisponível. Eventos negados são **best effort**: falha de persistência gera somente diagnóstico interno genérico e não libera nenhum dado. O próximo recorte deverá introduzir métricas/alerta de falta de eventos.
2. `queue_id` em negativas só é persistido se a fila realmente existir **dentro da operação autenticada**. Nomes de filas inexistentes ou de outras operações não são gravados. Nenhum `session_id` é persistido para consultas negadas.
3. `GRANT_ENABLED/REVOKED` registra `actor_user_id` e `target_user_id` existentes e a fila da mesma operação. Tentativas falhas de mudança de grant não geram `APPLIED`; repetição idempotente sem mudança não gera outro evento.
4. Se o banco 006b4 não aceitar a inserção, a alteração de grant é **inteiramente revertida**; a API não confirma uma permissão sem registrar o evento.
5. Não reescrever o endpoint de histórico completo, o worker ou a UI; manter a segregação `RUNTIME/VERIFIED` e os gates de privacidade de 006B-4.
6. Bancos em `006b1/006b2/006b3` preservam sua compatibilidade anterior. O diário de decisões está ativo **apenas em 006b4**. Para exigência de auditoria corporativa, não se deve usar uma revisão anterior.
7. A cobertura de negativas **não inclui** autenticação inválida, erros 422 de validação nem negativas de operador barradas no `authenticate/assert_access`, antes do endpoint. Nem inclui outras rotas legadas. A evolução da cobertura deverá ser planejada separadamente.

## QA / Gates

Novos testes sintéticos em `tests/test_verified_history.py`:
- N2 vedada para `auditor.demo`: negativa conserva 404, evento auditado, nenhum session_id desconhecido/payload gravado;
- revogação/ativação N1 pelo ADMIN criam eventos `APPLIED` separados; PATCH idempotente não gera novo evento; auditor perde acesso imediatamente após revogação;
- erro de INSERT na tabela `security_decisions` impede commit de revogação;
- falha de gravação de negativa mantém HTTP 404 (não libera dados).

`tests/test_schema_admin.py` testa upgrade explícito e backup, índice faltante, preservação de 17 tabelas no banco sem revisão e proibição de upgrade do original não versionado.

**Gates manuais:** `.\start.cmd --check` com pytest, Ruff, `npm run test:architecture`, TypeScript e Vite; `schema_admin inspect` no SQLite **original** deve continuar `revision=null`, 17 tabelas e `integrity=ok`; `provenance_dry_run` deve continuar `rows_written=0`, `safe_for_history_authorization=false`. Nunca executar `adopt`, `upgrade`, `upgrade-audit`, `upgrade-security` nem `stamp` no original.

## Limites / rollback

Os eventos novos ainda não têm retenção, assinatura/hash chain, armazenamento externo WORM nem API administrativa de consulta; esses são requisitos posteriores. O SQLite de POC opera em um host apenas, sem promessa de escala/SQL Server/Teams/produção.

**Rollback código:** `git switch feat/006b5a-history-access-audit`. Em banco de teste, downgrade de 006b4 para 006b3 apenas quando a tabela de decisões estiver **vazia**. Não apagar evidências de bancos não descartáveis para forçar downgrade.
