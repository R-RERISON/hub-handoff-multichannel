# SPEC-006B-3.1 — Proveniência em tempo de execução (gravação conservadora)

**Status:** IMPLEMENTAÇÃO NO GITHUB / HOMOLOGAÇÃO WINDOWS PENDENTE.  
**Base:** `feat/006b2-segment-provenance-schema`, cuja migration em cópia recebeu aprovação funcional.  
**Escopo desta fatia:** instrumentar intake, mensagens e transferência operacional em bancos **explicitamente migrados** para `006b2_queue_provenance`. Sem backfill e sem alteração do contrato da interface.

## Premissas e proteção do SQLite da POC

O banco real do usuário continua **não versionado** (`revision=null`, 17 tabelas) e **não será migrado automaticamente**. A classe `ProvenanceRecorder` é instanciada no startup, verifica a revisão Alembic e só ativa as escritas quando o SQLite já possui `006b2_queue_provenance` e as três tabelas esperadas.

- `revision=null`: recorder inativo, comportamento atual idêntico e sem criar tabelas novas.
- `006b1_poc_baseline`: recorder inativo, sem escrita em tabelas inexistentes.
- `006b2_queue_provenance`: recorder ativo **apenas após reiniciar o aplicativo**, com transações SQLite existentes.
- Revisão desconhecida ou tabelas ausentes: startup falha, sem tentar ajustar o esquema por conta própria.
- `Base.metadata.create_all` não foi alterado e segue ignorando as três tabelas Alembic, por estarem num `MetaData` separado.

**Regra:** NÃO executar `schema_admin adopt` ou `upgrade` no banco original para homologar esta fatia. Os testes `tmp_path` criam e migram exclusivamente bases sintéticas. A migração do banco principal continua pendente de gate de rollout separado.

## Semântica de proveniência comprovada

1. **Novo atendimento:** depois que `HandoffSession` é gravado e antes do commit, criar o segmento inicial `ordinal=0`, fila de intake, `started_at=created_at`, `provenance_state=VERIFIED`. Registrar também a proveniência do evento inicial `QUEUED`.
2. **Nova mensagem:** após criar a linha de mensagem, gravar referência em `message_queue_provenance` ao segmento **aberto e coincidente com a fila corrente**. Senão, gravar `segment_id=NULL`, `confidence=UNDETERMINED`. Mensagens duplicadas por `external_message_id` não criam nova referência.
3. **Transferência aceita N1 → N2:** depois da persistência de `SessionTransfer`, encerrar o segmento aberto de N1 com `ended_at=transfer.created_at`; criar segmento N2 com ordinal crescente, `started_at=transfer.created_at`, `transfer_id` e `VERIFIED`. Registrar `TRANSFERRED` no segmento de origem **quando este for comprovado**, caso contrário `UNDETERMINED`.
4. **Atendimento legado sem segmento:** nunca retroatribuir automaticamente mensagens ou eventos anteriores à fila atual. Após uma nova transferência, a **fila de destino** é comprovável a partir daquele instante, portanto ganha segmento; a proveniência anterior permanece desconhecida.
5. **Atomicidade:** mensagem/segmento/evento são gravados na mesma transação existente do respectivo endpoint. Erro de FK, segmento conflitante ou transição inválida deve impedir o commit completo.

## Segurança e cobertura intencionalmente incompleta

- Esta implementação **não** libera histórico cross-queue: o bloqueio temporário de supervisor/auditor da SPEC-006A continua. A SPEC-006B-4 implementará verificação de permissões de leitura por segmento, exigindo `confidence=VERIFIED` ou política específica para `INFERRED`.
- Eventos automáticos de despacho, presença, fechamento e aceite **ainda não recebem proveniência por esta fatia**. Os dois eventos instrumentados são `QUEUED` no intake e `TRANSFERRED` na transferência. Eventos sem referência **não devem ser presumidos de nenhum segmento**.
- Sessões legadas com evidência histórica precisam de um plano de backfill conservador e reversível, a ser elaborado e testado na 006B-3.2. Não inferir proveniência por timestamp quando múltiplas transferências ou registros simultâneos tornarem a fronteira ambígua.
- O registro da justificativa de transferência continua em `session_transfers.reason`; não há nova mensagem visível ao usuário nem envio ao Teams/outbox.
- O fluxo N1→N2, o dispatcher FIFO e a Mesa da Ana/Bruno não devem apresentar diferenças em bancos não versionados.

## Arquivos entregues

- `src/handoff_hub/provenance_writer.py`: implementação version-gated das operações `intake`, `message`, `transfer`, `event`.
- `src/handoff_hub/poc_api.py`: pontos de integração em criação de atendimento e mensagens.
- `src/handoff_hub/operator_workflow.py`: gravação dos segmentos no comando de transferência.
- `tests/test_runtime_provenance.py`: testes em SQLite temporário 006B-2 (novo atendimento/mensagens/transferência), legado migrado sem inferência indevida e banco não versionado sem DDL adicional.

## Gate Windows — somente testes

```powershell
cd C:\Projetos\hub-handoff\hub-handoff-multichannel
git fetch origin
git switch --track origin/feat/006b3-provenance-writer
.\start.cmd --check
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
```

**Expectativa:** Pytest, Ruff, testes de arquitetura frontend, TypeScript e Vite aprovados. A inspeção no SQLite original ainda deve retornar **`revision=null` e 17 tabelas**. Não é necessário abrir o sistema para testar a migration; os testes exercitam bases isoladas.

## Próximas fatias

- **006B-3.2:** instrumentação dos eventos operacionais faltantes, plano read-only de backfill (com confiança e métricas de `UNDETERMINED`), testes de dados legados e fail-closed.
- **006B-4:** somente depois, autorizações de leitura por fila/segmento, event timeline filtrado, contadores seguros e testes negativos IDOR.
- **006B-5:** concessões multirrole e auditoria/monitoria avançada.
