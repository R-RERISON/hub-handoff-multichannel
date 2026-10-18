# Feature Specification — SPEC-011: Anexos, imagens e prints seguros

**Feature Branch**: `spec/011-secure-attachments` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W2 / P1
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 006B VERIFIED, 009 histórico e 016 regras de retenção antes de produção

## User Scenarios & Testing

### User Story 1 — Enviar print permitido (Priority: P1)

Como **operador responsável**, quero anexar uma imagem comprovadamente segura a uma sessão própria.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado JPEG válido e tamanho permitido, quando o operador envia, então o arquivo fica em quarentena até validação e só depois pode ser usado.
2. Dado arquivo executável renomeado para .png, quando é enviado, então a verificação real do conteúdo rejeita.

### User Story 2 — Consultar mídia por escopo (Priority: P2)

Como **auditor N1**, quero baixar somente o que pertence a segmento VERIFIED autorizado.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dada mídia da fila N2, quando Auditor N1 solicita por ID direto, então recebe negativa sem bytes e sem existência revelada.
2. Dado grant revogado, quando download pendente é solicitado, então a autorização é reavaliada e o conteúdo não é servido.

### Edge Cases

- Mime spoofing, zip bomb e arquivo descomprimido acima do limite.
- Transferência N1→N2 com visibilidade restrita.
- Falha de antivírus deixa objeto em quarentena, nunca CLEAN.

## Requirements

### Functional Requirements

- **FR-001**: Validar tipo real do arquivo, tamanho, quantidade, checksum, nome opaco e varredura/quarentena antes de servir os bytes..
- **FR-002**: Guardar bytes em armazenamento privado fora do webroot e registrar somente metadados e proveniência persistentes..
- **FR-003**: Autorizar upload, preview, download e exclusão lógica por operação, fila, segmento e ownership, sem links públicos permanentes..
- **FR-004**: Impor estados UPLOADING/QUARANTINED/CLEAN/REJECTED/DELETED com retenção auditável e sem reutilizar ids externos..
- **FR-005**: Nunca anunciar suporte de imagem no Teams antes de capability negotiation do adapter..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- Attachment, AttachmentScan, AttachmentAccessAudit.
- StorageObjectRef, SegmentMediaGrant.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 downloads de conteúdo não CLEAN ou não autorizado.
- **SC-002**: 100% dos arquivos com checksum e decisão de varredura.
- **SC-003**: 0 anexos N2 expostos a grants exclusivos N1.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- Upload arbitrário de executáveis e arquivos HTML/SVG.
- Entrega externa por bot antes da SPEC-012.

## Assumptions

- Personas: operador, usuário final, auditor autorizado.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
