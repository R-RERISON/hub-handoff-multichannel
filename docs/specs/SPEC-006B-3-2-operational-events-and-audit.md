# SPEC-006B-3.2 — Eventos operacionais e diagnóstico read-only de proveniência

**Estado:** implementado em branch de desenvolvimento, **aguardando gates Windows**.  
**Base:** `feat/006b3-provenance-writer` (SPEC-006B-3.1 homologada com 74 Pytest, Ruff, 9 testes frontend, TypeScript/Vite e `inspect` sem alterações no banco original).

## Contrato de segurança

A revisão `006b2_queue_provenance` continua sendo a **única** que habilita o gravador. O SQLite original sem `alembic_version` permanece com 17 tabelas e sem mudanças. Todos os testes usam `tmp_path` e dados sintéticos; não migrar o banco real nesta etapa.

- **Novos eventos:** `QUEUED`, `OFFERED`, `OFFERED_AUTO`, `ACCEPTED`, `DECLINED`, `OFFER_EXPIRED`, `ACTIVE`, `CLOSED` e `TRANSFERRED` passam a ter referência de proveniência quando emitidos pelos caminhos atualmente conhecidos.
- Eventos operacionais são gravados **na mesma transação** que muda o estado do atendimento. O escritor exige **um único segmento aberto**, com a mesma fila da sessão e `provenance_state=VERIFIED`.
- Se não há segmento aberto comprovado (ex.: ticket criado antes da migração), novas ocorrências ganham `segment_id=NULL` e `confidence=UNDETERMINED`. A exceção é o segmento novo comprovado após transferência na SPEC-006B-3.1.
- O evento `TRANSFERRED` continua ligado ao **segmento da fila de origem** quando comprovado, e não é reatribuído à fila N2.
- Divergência de proveniência que geraria segmentos abertos sobrepostos aborta a transação; nenhuma mensagem é atribuída só porque o ticket está atualmente numa fila.
- As justificativas internas de transferência permanecem em `session_transfers.reason`, sem envio ao chat do usuário nem à outbox.

## Auditoria de cobertura sem acesso ao conteúdo

`python -m handoff_hub.provenance_audit` produz **somente contagens agregadas**. O comando usa conexão SQLite em modo leitura e valida previamente `integrity_check`, `foreign_key_check` e assinatura de schema.

- SQLite original não versionado: `status=NOT_MIGRATED`, `provenance_available=false`, contagens agregadas de sessões, transferências, mensagens e eventos.
- SQLite 006B-2: `status=REPORT_READY`, com segmentos totais/verificados/abertos/encerrados; para mensagens e eventos, cobertura `verified`, `undetermined` e `uncovered` (não existe linha de proveniência); total de sessões sem segmento e sinalização de múltiplos segmentos abertos para mesma sessão.
- Os totais verificados, indeterminados e sem cobertura precisam fechar com a contagem original da tabela. Divergência aborta.
- O relatório **nunca** publica texto de mensagem, solicitante, operador, credenciais, tokens nem IDs individuais.
- `safe_for_history_authorization=false` permanece fixo: o relatório **não concede acesso** à fila N1 sobre mensagens da N2 e não altera a restrição 006A.

**Não há backfill nesta fatia.** Os dados legados sem assinatura de origem são classificados apenas como lacunas de cobertura; os registros originais permanecem intactos. O backfill, se tecnicamente demonstrável sem ambiguidade, será uma etapa explícita posterior, com dry-run e backup.

## Arquivos implementados

- `src/handoff_hub/provenance_writer.py`: função `event_for_handoff`, exigindo mesmo segmento/fila e estado verificado; mensagens também passam a exigir `provenance_state=VERIFIED`.
- `src/handoff_hub/operator_workflow.py`: eventos do workflow manual.
- `src/handoff_hub/poc_api.py`: eventos da atribuição direta e do encerramento, além de injetar o gravador no dispatcher em background.
- `src/handoff_hub/auto_dispatch.py`: eventos automáticos de oferta e expiração.
- `src/handoff_hub/provenance_audit.py`: relatório agregado e read-only, sem backfill.
- `tests/test_runtime_provenance.py`: testes adicionais de auditoria, eventos manuais, despacho automático e eventos de recusa.

## Teste no Windows

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
git switch feat/006b3b-events-audit
git merge --ff-only origin/feat/006b3b-events-audit

.\start.cmd --check

# Inspeção e auditoria read-only do banco original (17 tabelas, revision null)
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
.\.venv\Scripts\python.exe -m handoff_hub.provenance_audit
```

Se a branch não existir localmente, use `git switch --track origin/feat/006b3b-events-audit` em vez dos dois comandos `switch` e `merge` acima.

**Esperado no SQLite original:** `inspect` com 17 tabelas, `revision=null`; `provenance_audit` com `status=NOT_MIGRATED`. Nenhum comando acima modifica o banco ou cria tabela.

**Critério de aceite:** Pytest, Ruff, nove testes frontend, TypeScript e Vite aprovados, mais inspeção não destrutiva. Não executar `adopt`, `upgrade` ou `stamp` no banco principal.

## Próximas evoluções

- **SPEC-006B-3.3:** planejar backfill `dry-run` com evidência por transferência, relatórios quantitativos e testes de casos ambíguos; sem alteração de dados até homologação.
- **SPEC-006B-4:** autorização por segmento com cobertura verificável, filtragem de eventos/mensagens/contadores e testes negativos de N1/N2.
- **SPEC-006B-5:** grants multirrole, auditoria avançada e camada administrativa.
