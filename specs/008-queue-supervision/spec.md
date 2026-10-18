# Feature Specification — SPEC-008: Supervisão operacional por fila

**Feature Branch**: `spec/008-queue-supervision` (proposta de execução futura; não criada)
**Created**: 2026-10-18
**Status**: Draft — especificação proposta; não implementada nesta entrega
**Priority / Wave**: P0 / W2
**Input**: solicitação de consolidação do Handoff Hub via Spec Kit e reconciliação da arquitetura existente.
**Dependencies**: 007, 006A/006B, 018

## User Scenarios & Testing

### User Story 1 — Supervisionar uma fila concedida (Priority: P1)

Como **supervisor**, preciso entender backlog, ofertas, capacidade, aging e transferências de sua fila.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dado supervisor com grant N1, quando abrir painel N2 por URL direta, então a API não revela contagens nem conversas N2.
2. Dado alteração de fila no seletor, quando novos dados forem carregados, então nenhum dado da fila anterior permanece visível.

### User Story 2 — Administrar equipe delegada (Priority: P2)

Como **supervisor com permissão**, preciso ajustar capacidade e membership somente em filas delegadas.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dada permissão queue.members.manage em N1, quando tentar alterar vínculo N2, então a operação é negada e não modifica dados.
2. Dada mudança válida, quando outro supervisor consulta a mesma fila, então vê a atualização confirmada e auditável.

### Edge Cases

- Revogação durante tela aberta.
- Fila sem operadores ou capacidade.
- Sessão N1 transferida para N2 durante agregação.

## Requirements

### Functional Requirements

- **FR-001**: Ter workspace por fila, listas paginadas e indicadores autorizados de fila: aguardando, ofertas, ativos, operadores online, tempo de espera e capacidade.
- **FR-002**: Executar filtros no backend antes de agregações/paginação, inclusive para tickets transferidos por segmentos verificados.
- **FR-003**: Suportar equipe, membership, capacidade e ações delegadas por permissão granular, sem tornar supervisor operador nem permitir mensagens ao usuário.
- **FR-004**: Descartar dados de fila anterior ao trocar, revogar ou perder autorização, incluindo eventos de atualização e reconexão.
- **FR-005**: Registrar comandos delegados e conflitos de concorrência, com feedback operacional preciso.

### Security and data invariants

- Backend é autoridade de RBAC/escopo e ownership; negar acesso a filas, operações e segmentos não concedidos.
- Sem segredos, PII reais ou migrações no `data/handoff-poc.db`; toda implementação deve passar por banco sintético e migrations versionadas.
- Evidenciar falhas, concorrência, reversibilidade e retenção; não anunciar Teams real, SQL Server, OIDC ou produção antes dos respectivos gates.

### Key Entities

- QueueOperationalSnapshot e QueueWorkloadMetric.
- QueueMembership e QueuePolicy.
- DelegatedOperationAudit.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 vazamentos de contagem/conteúdo entre filas em testes negativos.
- **SC-002**: 100% dos comandos mutantes com grant verificado e auditoria.
- **SC-003**: Ações essenciais executáveis com teclado nas resoluções homologadas.
- **SC-004**: Todos os cenários de aceite da SPEC possuem resultado verificável e evidência no PR do incremento antes da aprovação.

## Scope exclusions

- Assumir ou enviar mensagens como operador.
- Monitoria/coaching do SPEC-010.

## Assumptions

- Personas envolvidas: supervisor de fila.
- Nenhuma SPEC futura equivale a funcionalidade já entregue; **planejado não é implementado**.
- A arquitetura e o contrato de segurança existentes serão preservados até decisão registrada em ADR.
- Mudanças que afetem direitos de acesso, retenção e uso de dados reais exigem revisão de segurança e aprovação formal.
