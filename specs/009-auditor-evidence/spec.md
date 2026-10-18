# Feature Specification — SPEC-009: Portal de auditoria e evidências por segmento

**Feature Branch**: `spec/009-auditor-evidence` (proposta de execução futura; não criada)
**Created**: 2026-10-18
**Status**: Draft — especificação proposta; não implementada nesta entrega
**Priority / Wave**: P0 / W2
**Input**: solicitação de consolidação do Handoff Hub via Spec Kit e reconciliação da arquitetura existente.
**Dependencies**: 006B-4.x/5.x, 007, 008 para controles de fila

## Objective, scope and behavior contract

**Objective:** Oferecer consulta auditável e exportação de evidências de conversas estritamente por segmento VERIFIED.

**Functional contract:** Busca, detalhe e exportação exigem grant sobre segmento/tempo e journal de acesso; manifesto inclui escopo, filtros, integridade e justificativa.

**Rollback and failure behavior:** Falha de journal de leitura bloqueia conteúdo; exportação não concluída expira sem liberar bytes; nenhum backfill de UNKNOWN.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Pesquisar e examinar evidência (Priority: P1)

Como **auditor N1**, preciso localizar atendimentos e consultar somente mensagens e eventos VERIFIED de N1.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dada sessão transferida N1→N2, quando auditor N1 consultar, então recebe somente itens VERIFIED de N1.
2. Dada mensagem legado UNKNOWN, quando pesquisar, então ela não aparece como VERIFIED nem é autorizada por inferência.

### User Story 2 — Exportar com responsabilização (Priority: P2)

Como **auditor com permissão explícita**, preciso produzir pacote mínimo e rastreável de evidência.

**Independent Test**: Executar somente este fluxo em laboratório sintético e verificar todos os cenários.

**Acceptance Scenarios**:
1. Dada ausência da permissão de exportar, quando solicitar extração, então há negativa sem arquivo e sem revelar conteúdo.
2. Dada exportação autorizada, quando for criada, então inclui filtros, escopo, justificativa, período, hash e evento de acesso.

### Edge Cases

- Paginação durante revogação de grant.
- Download depois de expiração do link.
- Histórico sem proveniência verificável.

## Requirements

### Functional Requirements

- **FR-001**: Oferecer portal /auditoria separado com pesquisa, filtros de fila/período, paginação estável e detalhe somente por proveniência RUNTIME/VERIFIED.
- **FR-002**: Tratar filas/segmentos históricos como limites de segurança, não a fila atual da sessão; bloquear UNKNOWN/AMBIGUOUS e notas internas não autorizadas.
- **FR-003**: Exigir grants de leitura e exportação independentes, auditando leituras e decisões; falha de journal obrigatório bloqueia entrega do conteúdo.
- **FR-004**: Gerar evidência exportada com metadados de escopo, data, integridade, expiração e minimização, sem token, segredo nem conteúdo extra de outras filas.
- **FR-005**: Aplicar revogação efetiva antes de retornar página, download ou exportação; limpar dados protegidos em cliente após revogação.

### Security and data invariants

- Backend é autoridade de RBAC/escopo e ownership; negar acesso a filas, operações e segmentos não concedidos.
- Sem segredos, PII reais ou migrações no `data/handoff-poc.db`; toda implementação deve passar por banco sintético e migrations versionadas.
- Evidenciar falhas, concorrência, reversibilidade e retenção; não anunciar Teams real, SQL Server, OIDC ou produção antes dos respectivos gates.

### Key Entities

- VerifiedSegment e AuthorizedEvidenceRecord.
- HistoryAccessAudit, SecurityDecision.
- AuditExportJob e ExportManifest.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% das respostas de histórico sob grant de fila e proveniência VERIFIED.
- **SC-002**: 0 itens UNKNOWN ou de outras filas em exportações negativas.
- **SC-003**: 100% das exportações autorizadas com journal e manifesto de integridade.
- **SC-004**: Todos os cenários de aceite da SPEC possuem resultado verificável e evidência no PR do incremento antes da aprovação.

## Scope exclusions

- Backfill permissivo do legado.
- Armazenamento WORM completo (SPEC-016).

## Assumptions

- Personas envolvidas: auditor, segurança e compliance.
- Nenhuma SPEC futura equivale a funcionalidade já entregue; **planejado não é implementado**.
- A arquitetura e o contrato de segurança existentes serão preservados até decisão registrada em ADR.
- Mudanças que afetem direitos de acesso, retenção e uso de dados reais exigem revisão de segurança e aprovação formal.
