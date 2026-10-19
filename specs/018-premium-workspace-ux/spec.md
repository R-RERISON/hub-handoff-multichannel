# Feature Specification — SPEC-018: Design system premium, acessibilidade e experiência operacional

**Feature Branch**: `spec/018-premium-workspace-ux` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W1 transversal / P0
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 006C primeiro; demais SPECs consomem componentes e padrões

## Objective, scope and behavior contract

**Objective:** Fornecer experiência premium homogênea e acessível sem fundir os portais nem comprometer segurança.

**Functional contract:** Design tokens e padrões de shell/componentes definem estados de loading/erro/sem dados, a11y e três viewports homologados.

**Rollback and failure behavior:** Falha de fetch, revogação e troca de fila limpam dados stale; layout deve preservar ações essenciais sem overflow.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Atender com acessibilidade nos viewports desktop suportados (Priority: P1)

Como **operador**, quero responder e transferir sem controles cortados.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado viewport desktop 1366×768, quando abrir a Mesa e uma conversa, então composer e ações essenciais permanecem operáveis sem overflow horizontal.
2. Dado teclado sem mouse, quando navega ofertas/transferência, então foco e rótulos de ação são previsíveis.

### User Story 2 — Entender estados e segurança (Priority: P2)

Como **supervisor ou auditor**, quero reconhecer lista vazia, autorização revogada, falha e carregamento.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado grant revogado com detalhe já aberto, quando atualizar autorizações, então conteúdo protegido é limpo antes de qualquer nova requisição.
2. Dado processo de carregamento, quando a API demora, então a interface não exibe dados stale de outra fila.

### Edge Cases

- Evento volumoso altera altura da tabela e esconde comandos.
- Revogação de grant durante fetch.
- Redução de movimento e zoom 200%.

## Requirements

### Functional Requirements

- **FR-001**: Criar tokens e componentes compartilhados de tipografia, cores semânticas, espaçamentos, foco, tabelas, formulários, estado vazio/erro e feedback..
- **FR-002**: Manter shells independentes para Operador, Supervisão, Administração, Auditoria, Monitoria e Laboratório; evitar dashboard genérico sobrecarregado..
- **FR-003**: Garantir operabilidade por teclado e critérios WCAG 2.2 AA aplicáveis; suporte desktop 1366×768 e 1920×1080 com evidência visual..
- **FR-004**: Limpar cache/estado protegido em logout, revogação e troca de escopo; mascarar dados e não confiar na UI como fronteira de segurança..
- **FR-005**: Aplicar pesquisa qualitativa de tarefas críticas e regression screenshots sintéticas por portal, sem retroceder UX aprovada..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- DesignToken, AccessibleComponentContract, WorkspaceShell.
- ViewportEvidence, UXAcceptanceRecord.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 controles essenciais cortados nas duas resoluções desktop exigidas.
- **SC-002**: 100% das tarefas críticas testadas por teclado sem bloqueio.
- **SC-003**: 0 dados protegidos stale após revogação/troca de fila.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- Refazer a SPA inteira antes de entrega funcional.
- Framework visual novo sem ADR ou necessidade comprovada.

## Assumptions

- Personas: operador, supervisor, administrador, auditor, monitor.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
