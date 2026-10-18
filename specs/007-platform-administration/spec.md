# Feature Specification — SPEC-007: Administração de operações, filas, pessoas e permissões

**Feature Branch**: `spec/007-platform-administration` (proposta de execução futura; não criada)
**Created**: 2026-10-18
**Status**: Draft — especificação proposta; não implementada nesta entrega
**Priority / Wave**: P0 / W1
**Input**: solicitação de consolidação do Handoff Hub via Spec Kit e reconciliação da arquitetura existente.
**Dependencies**: 006C para desenvolvimento integrado; SPEC-006A/006B para grants e esquema; SPEC-018 para UX

## User Scenarios & Testing

### User Story 1 — Gerenciar filas e operação (Priority: P1)

Como **administrador**, preciso criar, ativar, pausar e arquivar uma fila sem perder atendimentos e trilhas.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dada fila sem sessões ativas, quando for arquivada, então deixa de receber novas ofertas e seu histórico permanece disponível conforme autorização.
2. Dada fila com sessões em andamento, quando for solicitada exclusão, então a ação destrutiva é rejeitada e apresenta plano de tratamento.

### User Story 2 — Gerenciar perfis e equipe (Priority: P2)

Como **administrador**, preciso associar usuário, operador, membership e grant por fila com papéis separados.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dada pessoa sem grant N2, quando receber somente membership N2, então não adquire leitura de histórico N2.
2. Dada revogação de grant, quando a próxima leitura ocorrer, então o conteúdo protegido é negado.

### Edge Cases

- Fila pausada enquanto há ofertas já emitidas.
- Desativação de operador com conversa ativa.
- Dois administradores alteram capacidade simultaneamente.

## Requirements

### Functional Requirements

- **FR-001**: Oferecer gerenciamento de operações, filas, pessoas, vínculo de operadores, capacidade, presença administrativa e ciclo de vida DRAFT/ACTIVE/PAUSED/ARCHIVED com identificadores estáveis.
- **FR-002**: Distinguir conta autenticada, perfil de operador, membership de despacho e grants de leitura/gestão, sem heranças implícitas de papel.
- **FR-003**: Restringir alterações administrativas pela operação e permissão efetiva e registrar trilha de quem/quando/o quê, sem segredos e dados de conversas.
- **FR-004**: Impedir exclusão física de entidades com sessões, eventos ou provas de auditoria e preservar integridade referencial.
- **FR-005**: Exibir resultado de validação, conflito de concorrência, autorização negada e situação pós-salvamento sem estados otimistas enganosos.

### Security and data invariants

- Backend é autoridade de RBAC/escopo e ownership; negar acesso a filas, operações e segmentos não concedidos.
- Sem segredos, PII reais ou migrações no `data/handoff-poc.db`; toda implementação deve passar por banco sintético e migrations versionadas.
- Evidenciar falhas, concorrência, reversibilidade e retenção; não anunciar Teams real, SQL Server, OIDC ou produção antes dos respectivos gates.

### Key Entities

- Operation, Queue e QueuePolicy com lifecycle.
- UserAccount, OperatorProfile e QueueMembership.
- RoleGrant e AdministrativeChangeEvent.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% das mutações auditáveis e autorizadas no backend.
- **SC-002**: 0 concessões implícitas por membership ou papel visual.
- **SC-003**: 100% dos casos de exclusão com vínculo histórico protegidos.
- **SC-004**: Todos os cenários de aceite da SPEC possuem resultado verificável e evidência no PR do incremento antes da aprovação.

## Scope exclusions

- Gestão de credenciais corporativas Entra ID (SPEC-014).
- Publicar integração de canal real sem SPEC-012.

## Assumptions

- Personas envolvidas: administrador de plataforma, responsável por operação.
- Nenhuma SPEC futura equivale a funcionalidade já entregue; **planejado não é implementado**.
- A arquitetura e o contrato de segurança existentes serão preservados até decisão registrada em ADR.
- Mudanças que afetem direitos de acesso, retenção e uso de dados reais exigem revisão de segurança e aprovação formal.
