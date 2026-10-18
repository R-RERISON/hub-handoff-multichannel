# Feature Specification — SPEC-012: Adapter Teams Embedded e mensageria E2E

**Feature Branch**: `spec/012-teams-embedded-adapter` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W3 / P0
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 014 IAM de integrações, 015 durabilidade e trabalhadores, 016 proteção de dados; 011 opcional para fase mídia

## User Scenarios & Testing

### User Story 1 — Handoff real mantendo o canal original (Priority: P1)

Como **usuário do bot original**, quero receber resposta humana na mesma conversa Teams já iniciada.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dada solicitação do bot autenticada, quando o Hub aceita, então o operador recebe sessão correlacionada sem criar identidade Teams própria.
2. Dada resposta humana, quando a entrega externa ocorre, então somente ACK comprovado marca a mensagem como entregue.

### User Story 2 — Recuperar falha de entrega (Priority: P2)

Como **suporte de integração**, quero retentar envio sem perder ou duplicar mensagem.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado timeout depois de entrega remota, quando o adapter retoma, então usa idempotência/correlação para não publicar duplicata.
2. Dada falha duradoura, quando o limite de retries expira, então mantém item rastreável em DLQ com recuperação manual.

### Edge Cases

- ACK chega duplicado ou fora de ordem.
- Bot original indisponível durante resposta do humano.
- Troca de tenant, expiração de autorização e replay de webhook.

## Requirements

### Functional Requirements

- **FR-001**: Implementar protocolo de integração autenticado, versionado e idempotente para ingressos, criação, entrega, ACK e reconciliação..
- **FR-002**: Preservar ownership do bot original sobre conversa, credencial, Teams tenant/conversationId e identidade enviada; Hub não deve assumir bot alheio..
- **FR-003**: Persistir inbox/outbox, correlation IDs, dedupe, backoff, DLQ, lease, ACK explícito e reprocessamento sem marcar entrega simulada como real..
- **FR-004**: Bloquear encaminhamento de mensagens HUMAN_ACTIVE para o LLM do bot original quando o operador está responsável..
- **FR-005**: Usar feature flag, canário, logs sanitizados, limite de taxa, anti-replay e rollback de canal sem perder backlog..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- IntegrationIdentity, ChannelConversationRef, ChannelInboxEvent.
- ChannelOutboxEvent, DeliveryAttempt, DeliveryAcknowledgement.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 mensagens marcadas entregues sem ACK verificável.
- **SC-002**: 100% das entradas duplicadas com efeito idempotente.
- **SC-003**: 100% dos itens não entregues persistidos até reconciliação ou decisão auditada.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- App Native própria Teams (SPEC-017).
- Escalar piloto real antes dos gates IAM, política e operação.

## Assumptions

- Personas: usuário final no bot original, operador, integrador do bot Tornado.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
