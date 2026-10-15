# SPEC-001 — Foundation e primeiro contrato

Data: 2026-10-15 | Estado: DRAFT/DISCOVERY | Prioridade: P0

## Problema
Bots independentes necessitam de atendimento humano compartilhado, preservando suas conversas de origem sem duplicar regras de fila, operador, SLA e auditoria.

## Objetivo
Baseline de produto, modelo de domínio, arquitetura, contrato inicial, esqueleto FastAPI e teste de máquina de estados; nenhum atendimento real deve ser realizado por esta etapa.

## Funcionais
RF-001: bot autorizado cria solicitação com operation_id, integration_id, external_conversation_id, requester e queue_id.
RF-002: cada sessão pertence a exatamente uma operação e uma integração de origem.
RF-003: sessão muda de estado apenas por transições documentadas.
RF-004: reserva de operador respeita limite de capacidade, atomicamente.
RF-005: inbox registra mensagens externas com external_message_id e origem.
RF-006: outbox preserva mensagens antes de notificar adapter externo.
RF-007: operador usa workspace independente e ações auditáveis.
RF-008: adapter Embedded devolve mensagens ao bot de origem, nunca usando credenciais de outro bot.
RF-009: Native utiliza identidade própria do Hub e pode gerar chat distinto.
RF-010: integração Finesse é opcional; falha não corrompe estado.
RF-011: webhooks e comandos são versionados e idempotentes.
RF-012: segregação por operação/tenant e perfil do ator é obrigatória.

## Não funcionais
RNF-001: OAuth2/OIDC, RBAC e validation de audience/scopes; sem endpoints mutantes antes disso.
RNF-002: SQL Server como fonte de verdade, transactions e migrations.
RNF-003: transições com audit event e timestamps UTC.
RNF-004: retry/backoff, deduplicação e reconciliação de mensagens.
RNF-005: tracing e métricas sem conteúdos pessoais nos logs.
RNF-006: metas reais de disponibilidade/latência e retenção são definidas com baseline operacional, não presumidas.

## Estados preliminares
REQUESTED -> QUEUED -> OFFERED -> ACTIVE -> WRAP_UP -> CLOSED.
OFFERED -> QUEUED (recusa/timeout).
ACTIVE -> TRANSFER_PENDING -> QUEUED.
REQUESTED, QUEUED, OFFERED -> CANCELLED/EXPIRED (conforme política).
ACTIVE -> ABANDONED.
Terminais CLOSED, CANCELLED, ABANDONED, EXPIRED.
Guards de autorização e capacidade ainda dependem de SPEC-002.

## Gates SPEC-001
G0 ADR e especificação consistentes.
G1 Python inicia apenas probes, domínio e testes unitários, lint em CI.
G2 review por segurança, Teams e arquitetura.
G3 backlog e plano de migração aprovados.
G2/G3 exigem revisão formal; existência de arquivos não significa homologação.

## Casos adversos das próximas SPECs
Último operador livre para dois pedidos; duplicate POST; webhook duplicado; ACK perdido; mensagem após CLOSED; oferta expirou antes do aceite; reinício de worker; Finesse indisponível; cross-tenant; bot sem permissão Teams; uso indevido de anexos.

## Piloto objetivo
Bot CSTI/Tornado -> Hub -> fila N1 -> workspace -> resposta publicada pelo Bot CSTI -> encerramento -> retomada do fluxo automatizado. Com feature flag e rollback.
