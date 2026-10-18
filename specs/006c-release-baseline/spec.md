# Feature Specification — SPEC-006C: Baseline verificável e promoção controlada da POC

**Feature Branch**: `spec/006c-release-baseline` (proposta de execução futura; não criada)
**Created**: 2026-10-18
**Status**: Draft — especificação proposta; não implementada nesta entrega
**Priority / Wave**: P0 / W0
**Input**: solicitação de consolidação do Handoff Hub via Spec Kit e reconciliação da arquitetura existente.
**Dependencies**: PR #28 Draft, banco TEMP 006b4, Constituição v1.1

## User Scenarios & Testing

### User Story 1 — Decidir a promoção com evidências (Priority: P1)

Como **revisor de release**, preciso consultar os gates por SHA e impedir a promoção se houver pendência crítica.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dado um PR Draft com qualquer gate bloqueador pendente, quando alguém solicitar aprovação, então a matriz apresenta BLOCKED e nenhuma instrução de merge é emitida.
2. Dado todos os gates aprovados com evidência sanitizada, quando for feita a revisão, então o responsável pode registrar decisão explícita, distinta de produção.

### User Story 2 — Homologar UX e isolamento (Priority: P2)

Como **analista de QA**, preciso reproduzir cada cenário sem dados reais.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dado laboratório TEMP 006b4, quando executar UX-02/05/08 e demais cenários, então cada resultado fica vinculado ao SHA, persona, resolução e resultado observado.
2. Dado mudança de SHA após aprovação, quando conferir o gate, então testes afetados retornam ao estado REVALIDATE.

### Edge Cases

- Mudança do head durante homologação invalida evidências afetadas.
- Browser sem viewport comprovável não satisfaz UX-08.
- Banco de homologação fora de TEMP interrompe imediatamente a execução.

## Requirements

### Functional Requirements

- **FR-001**: Bloquear qualquer promoção à main enquanto UX-08 (390×844, 1366×768, 1920×1080, histórico e Mesa do Operador), UX-02, UX-05 ou revisão integral do diff estiver sem evidência aprovada.
- **FR-002**: Exigir matriz única de critérios QA, segurança, migração, RBAC, concorrência, privacidade, rollback e revisão por SHA com estados NOT_RUN, PASS, FAIL, BLOCKED, WAIVED (justificativa e aprovação).
- **FR-003**: Permitir somente dados sintéticos e scripts no diretório TEMP 006b4 para testes mutantes; proteger o SQLite original data/handoff-poc.db contra escrita, adoção ou migração.
- **FR-004**: Não promover PR #28 nem autorizar produção automaticamente; a decisão humana deve ser registrada com evidência e riscos residuais.
- **FR-005**: Reconciliar PRs empilhados e documentos paralelos #14/#15/#17 sem duplicar branches nem fechar PRs automaticamente.

### Security and data invariants

- Backend é autoridade de RBAC/escopo e ownership; negar acesso a filas, operações e segmentos não concedidos.
- Sem segredos, PII reais ou migrações no `data/handoff-poc.db`; toda implementação deve passar por banco sintético e migrations versionadas.
- Evidenciar falhas, concorrência, reversibilidade e retenção; não anunciar Teams real, SQL Server, OIDC ou produção antes dos respectivos gates.

### Key Entities

- ReleaseCandidate: SHA exato, branch, diff, versão, responsável e estado.
- GateEvidence: gate, SHA, ambiente, perfil, viewport, método, resultado, anexo sanitizado.
- ReleaseDecision: aprovador, decisão, justificativa, pendências e rollback.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% dos gates bloqueadores com evidência atrelada ao SHA final antes de considerar merge.
- **SC-002**: 0 escritas, migrações ou grants executados sobre o SQLite original.
- **SC-003**: 100% dos problemas P0/P1 fechados ou formalmente bloqueando a promoção.
- **SC-004**: Todos os cenários de aceite da SPEC possuem resultado verificável e evidência no PR do incremento antes da aprovação.

## Scope exclusions

- Produção, Teams real, Entra ID ou SQL Server.
- Merge automático, deploy, modificação da base POC original.

## Assumptions

- Personas envolvidas: revisor técnico, QA, responsável pela homologação.
- Nenhuma SPEC futura equivale a funcionalidade já entregue; **planejado não é implementado**.
- A arquitetura e o contrato de segurança existentes serão preservados até decisão registrada em ADR.
- Mudanças que afetem direitos de acesso, retenção e uso de dados reais exigem revisão de segurança e aprovação formal.
