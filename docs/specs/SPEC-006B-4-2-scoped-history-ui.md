# SPEC-006B-4.2 — Descoberta paginada e interface de histórico verificado

**Status:** implementação em branch para homologação Windows, PR DRAFT.  
**Branch:** `feat/006b4b-scoped-history-ux`  
**Base:** `feat/006b4a-verified-segment-read` (SPEC-006B-4.1, 93 Pytest + 9 testes frontend e gates de lint/build aprovados pelo usuário em 16/10/2026).

## Objetivo

Permitir que Supervisor e Auditor encontrem e visualizem somente atendimentos com **evidências RUNTIME/VERIFIED** na fila que lhes foi concedida. A listagem anterior escondia tickets transferidos e o histórico completo da SPEC-006A continua perigoso em atendimentos multiquela. A experiência deve ser claramente **parcial**, sem omitir o aviso de privacidade nem simular que o restante não exista.

## Escopo de implementação

- `GET /v1/history/verified-sessions?queue_id=n1&page=1&page_size=25`: descoberta paginada de tickets com prova da fila, sem expor assunto, solicitante, fila atual, destino, operador atual, texto de mensagens ou justificativa privada de transferência.
- A listagem aceita apenas papéis `SUPERVISOR`/`AUDITOR` autenticados via Bearer, exige o grant por `queue_id`, filtra a operação do principal **antes de paginar** e exige segmento `VERIFIED` com pelo menos uma mensagem ou evento do mesmo ticket, `confidence=VERIFIED` e `assigned_by=RUNTIME`. `page` é 1..1000; `page_size` é 1..50 (padrão 25).
- A saída contém `schema_ready`, `partial_history=true`, `tickets` (somente `session_id` e `segment_started_at` da fila concedida), `page` e `next_page`. A quantidade de tickets de outras filas e qualquer total global não são expostos.
- Para SQLite original sem Alembic, após validar o grant, devolve HTTP 200 com `schema_ready=false` e `tickets=[]`. Não executa consulta a tabelas ausentes, DDL ou migração. A UI apresenta estado **indisponível por ausência de proveniência**, nunca `Sem conversas` como conclusão geral.
- `GET /v1/handoffs/{id}/verified-history?queue_id=n1` da 006B-4.1 segue como fonte **única** de mensagens e eventos do segmento selecionado; o contrato original `GET /messages` e `GET /timeline` permanece conservador. A sessão pode ser descobrível numa fila autorizada mesmo depois de migrar sua responsabilidade para outra fila: isso **não libera** conteúdo da outra.
- Em `SupervisorConversations`, Supervisor/Auditor recebe abas independentes **Conversas correntes** e **Segmentos verificados**. Novo módulo `ScopedVerifiedHistory.tsx`: seletor alimentado por `/v1/me/queues`, lista sem PII, paginação, detalhes somente leitura, `aria` para avisos e acesso por teclado. Trocar fila, página ou atualizar permissões limpa conteúdo em memória antes da nova resposta.

## Segurança, não regressão e restrições

1. `require_queue` é verificado no backend em **toda requisição**. Revogar um grant invalida a consulta seguinte, mesmo com o mesmo Bearer. Não confiar na visibilidade dos controles React.
2. Operador usa ownership na Mesa; Admin tem permissões próprias; ambos recebem 403 nesta superfície. Supervisor/Auditor não podem usar esta UI para enviar mensagem, encerrar ou transferir.
3. Uma atribuição por timestamp, `handoff_sessions.queue_id` ou `INFERRED` não concede histórico. A ausência de segmento verificado ou a impossibilidade de confirmar seu ticket exclui a linha.
4. O timeline com motivos de transferências permanece **fora** desta superfície; não serializar o objeto `SessionTransfer`.
5. O SQLite POC principal continua com **17 tabelas, revision=null**. Não aplicar `adopt`, `upgrade`, `stamp` ou `create` sobre o principal; manter somente testes com bases sintéticas `tmp_path`.
6. O frontend não define políticas de segurança; o backend filtra antes de serializar, e a API de detalhe recalcula os grants.
7. Em uma eventual migração para SQL Server, redesenhar concorrência, paginação/índices e transações de auditoria antes de produção.

## Testes sintéticos e aceite

Em `tests/test_verified_history.py`, novos testes cobrem:
- Descoberta de ticket que passou por N1 → N2, sem conteúdo, motivos ou metadados da fila não concedida.
- Auditor N1 incapaz de listar N2; Supervisor N2 vê somente tickets com prova N2; admin/operador não usam novo endpoint; não autenticado e fila inexistente não vazam dados.
- Paginação, parâmetro inválido (422), revogação de grant durante sessão (404 na próxima leitura).
- Ticket legado sem segmento e proveniência `UNDETERMINED` não aparece na lista.
- SQLite não versionado sinaliza explicitamente `schema_ready=false` e preserva 17 tabelas.
- Testes de arquitetura frontend protegem a separação de abas, sinalização de parcialidade, rota com Bearer e ausência de ações mutantes.

**Gates Windows**, sem GitHub Actions:

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git status --short
git fetch origin
$branch = "feat/006b4b-scoped-history-ux"
if (@(git branch --list --format="%(refname:short)" $branch) -contains $branch) {
    git switch $branch
} else {
    git switch --create $branch --track "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw "Falha no checkout" }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Falha no fast-forward" }
.\start.cmd --check
if ($LASTEXITCODE -ne 0) { throw "Gates reprovados" }
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
```

**Gate de UI adicional:** usando apenas banco sintético migrado 006B-2 em ambiente descartável e contas demonstrativas, entrar como Auditor e como Supervisor em navegadores distintos; conferir as duas abas, isolamento N1/N2, aviso de parcialidade, paginação, atualização de grants, scroll mobile e navegação por teclado. No SQLite original, confirmar a mensagem de indisponibilidade sem migrar.

## Limitações e próxima SPEC

- `verified-history` ainda devolve todas as mensagens/eventos verificados do segmento solicitado **sem paginação**. Implementar janelas independentes de mensagens/eventos, rate limiting e auditoria imutável de leitura antes de homologação com grandes volumes ou exposição externa.
- Listagem usa paginação `OFFSET` limitada; em ambiente de atualizações simultâneas um item pode mudar de página. Para produção, avaliar paginação por cursor estável e índices.
- Os tickets transferidos **não são adicionados** à antiga `dashboard.handoffs`; permanecem em consulta segregada sem PII. Isso é uma restrição intencional, não perda de dados.
- Auditoria formal de acesso e grants multirrole continuam pendentes da SPEC-006B-5. Entra ID/OIDC, isolamento multioperação de produção e Teams adapter continuam pendentes.
- **Rollback:** voltar ao branch anterior `feat/006b4a-verified-segment-read`. Nenhum dado/tabela é alterado por este incremento; não há rollback de banco.
