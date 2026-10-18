# Feature Specification — SPEC-016: LGPD, retenção, segurança e auditoria inviolável

**Feature Branch**: `spec/016-privacy-governance-audit` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W1–W3 / P0
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 006B journaling, 009 evidência; política aprovada antes de dados reais

## Objective, scope and behavior contract

**Objective:** Formalizar retenção, descarte, proteção e verificabilidade de auditoria conforme decisão de compliance.

**Functional contract:** Política versionada liga classificação, prazo, legal hold e evento de descarte; journal verificável demonstra integridade.

**Rollback and failure behavior:** Falha de política ou integridade bloqueia descarte/entrega indevida; journal atual não pode ser anunciado como WORM.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Aplicar retenção e descarte (Priority: P1)

Como **administrador autorizado**, quero executar política de retenção sem destruir evidências bloqueadas.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado item com legal hold, quando expira sua retenção, então a rotina não o elimina.
2. Dado item elegível, quando ocorre expurgo, então conteúdo é eliminado e evento mínimo de descarte fica auditável.

### User Story 2 — Comprovar integridade e finalidade (Priority: P2)

Como **auditor autorizado**, quero verificar provas sem acessar dados de outra fila.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado evento de acesso, quando validado, então demonstra autor, escopo, finalidade e integridade.
2. Dado alteração indevida do journal, quando executada verificação, então a divergência é identificada.

### Edge Cases

- Conflito entre apagamento e legal hold.
- Falha de store WORM versus journal local.
- Exportação ainda válida após expurgo do conteúdo.

## Requirements

### Functional Requirements

- **FR-001**: Classificar dados pessoais/conversas/mídias/metadados e definir finalidade, minimização, bases legais e retenção aprovadas por responsáveis..
- **FR-002**: Executar políticas por operação e tipo com legal hold, descarte, exclusão lógica/física quando aplicável e trilha mínima retida legalmente..
- **FR-003**: Projetar trilha inviolável ou verificável (WORM/append-only externo e hash chaining quando adequado) para leituras, grants, exports e ações críticas..
- **FR-004**: Proteger dados em trânsito e repouso, segredos em gerenciador apropriado, acesso de emergência temporário e revisão de privilégios..
- **FR-005**: Garantir solicitações legais/privacidade com escopo e evidência, redaction e comunicação de incidentes..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- DataClassification, RetentionPolicy, LegalHold.
- ImmutableAuditEnvelope, IntegrityVerification, ErasureReceipt.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% das classes de dados com retenção aprovada antes de dados reais.
- **SC-002**: 0 expurgos de objetos sob legal hold.
- **SC-003**: 100% dos eventos críticos com verificação de integridade ou bloqueio documentado.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- Declarar o security_decisions atual WORM (não é).
- Escolher prazo legal de retenção sem decisão do responsável.

## Assumptions

- Personas: responsável de segurança, DPO/compliance, auditor.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
