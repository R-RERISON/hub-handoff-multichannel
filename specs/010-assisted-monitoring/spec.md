# Feature Specification — SPEC-010: Monitoria assistida bidirecional

**Feature Branch**: `spec/010-assisted-monitoring` (proposta de execução futura; não criada)
**Created**: 2026-10-18
**Status**: Draft — especificação proposta; não implementada nesta entrega
**Priority / Wave**: P1 / W2
**Input**: solicitação de consolidação do Handoff Hub via Spec Kit e reconciliação da arquitetura existente.
**Dependencies**: 006B, 007, 008 e leitura live restrita

## Objective, scope and behavior contract

**Objective:** Criar apoio bidirecional privado entre operador e monitor sem interferir no canal do cliente.

**Functional contract:** Pedido durável, claim atômico, troca de orientação interna e ACK/cópia de rascunho são eventos independentes da mensagem do usuário.

**Rollback and failure behavior:** Falha de notificação mantém pedido persistido e reprocessável; transferência/revogação restringe acesso imediatamente.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Solicitar auxílio durante atendimento (Priority: P1)

Como **operador responsável**, preciso criar solicitação sem perder o rascunho ou transferir a sessão.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dada sessão ACTIVE própria, quando solicitar auxílio, então gera pedido durável na fila corrente e a conversa permanece com o mesmo operador.
2. Dado pedido idempotente repetido por retry, quando receber novamente, então não cria duas solicitações ativas iguais.

### User Story 2 — Assumir e orientar em privado (Priority: P2)

Como **monitor com grant**, preciso assumir pedido, aconselhar e acompanhar ACK do operador.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dados dois monitores concorrentes, quando ambos tentam assumir, então exatamente um se torna responsável.
2. Dada recomendação privada, quando o monitor envia, então ela não entra em messages nem channel_outbox e só pode virar rascunho após ação do operador.

### Edge Cases

- Monitor offline e pedido envelhece.
- Transferência de N1 a N2 durante auxílio.
- Orientação enviada após revogação de grant.

## Requirements

### Functional Requirements

- **FR-001**: Permitir ao operador autenticado solicitar, acompanhar e cancelar auxílio apenas para sessão ACTIVE de sua propriedade.
- **FR-002**: Manter inbox persistente de auxílios por fila; claim atômico, idempotência, aging, expiração e escalonamento sem transferência automática ao N2.
- **FR-003**: Isolar orientação e recomendação proativa do fluxo de mensagens ao cliente e de outbox; operador confirma, dispensa ou copia ao rascunho, sem envio automático.
- **FR-004**: Revalidar grants de MONITOR e escopo de segmento em cada leitura, orientação, claim e após transferência; aplicar negativa não reveladora quando adequado.
- **FR-005**: Registrar criação, claim, atribuição, orientações, ACK, cancelamento, escalonamento e resolução com dados mínimos e política anti-spam.

### Security and data invariants

- Backend é autoridade de RBAC/escopo e ownership; negar acesso a filas, operações e segmentos não concedidos.
- Sem segredos, PII reais ou migrações no `data/handoff-poc.db`; toda implementação deve passar por banco sintético e migrations versionadas.
- Evidenciar falhas, concorrência, reversibilidade e retenção; não anunciar Teams real, SQL Server, OIDC ou produção antes dos respectivos gates.

### Key Entities

- AssistanceRequest e AssistanceAssignment.
- CoachingRecommendation e RecommendationAck.
- AssistanceEvent / EscalationPolicy.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 recomendações internas encaminhadas ao canal externo automaticamente.
- **SC-002**: 100% dos pedidos concorrentes com no máximo um monitor responsável.
- **SC-003**: 100% dos pedidos e orientações com trilha e verificação de escopo.
- **SC-004**: Todos os cenários de aceite da SPEC possuem resultado verificável e evidência no PR do incremento antes da aprovação.

## Scope exclusions

- LLM gerando respostas automáticas ao usuário.
- Substituir o operador por monitor.

## Assumptions

- Personas envolvidas: operador, monitor autorizado, supervisor.
- Nenhuma SPEC futura equivale a funcionalidade já entregue; **planejado não é implementado**.
- A arquitetura e o contrato de segurança existentes serão preservados até decisão registrada em ADR.
- Mudanças que afetem direitos de acesso, retenção e uso de dados reais exigem revisão de segurança e aprovação formal.
