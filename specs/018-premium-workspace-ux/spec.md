# Feature Specification — SPEC-018: Design system premium, acessibilidade e experiência operacional

**Feature Branch (implementação local)**: `feat/spec018-u2-operational-journeys-20261022`, baseada no U1 `4ad1ffed1e5202698009777135f5bd55d224a32b`; decisões de escopo vêm do PR #60.
**Created**: 2026-10-18
**Status**: PO_APPROVED_Q1_Q2 / U2_FUNCTIONAL_QA_PASS_WORKTREE / T004_T005_PENDING / NOT_ACCEPTED
**Wave / Priority**: W1 transversal / P0
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 006C primeiro; demais SPECs consomem componentes e padrões

## Clarificações aprovadas pelo Product Owner — 21/10/2026

- **Q1, opção A APROVADA:** SPEC-018 exige 1366×768 e 1920×1080, zoom real 100% e 200%; 390×844 é exploratório somente para o aceite isolado desta feature. A SPEC-006C FR-001 mantém UX-08 com 390×844 como gate de release bloqueante. O aceite da SPEC-018 NÃO autoriza ignorar a SPEC-006C.
- **Q2, opção A APROVADA:** manter portais/roles atuais; Monitoria com identidade MONITOR, autorização e dados próprios segue exclusivamente como trabalho da SPEC-010.
- **Precedência:** CONSTITUTION.md e especificações de segurança/release não são alteradas por essa decisão.
- **Origem:** aprovação expressa do Product Owner na conversa após discovery em 21/10/2026. O texto alterado na worktree local de discovery NÃO está publicado nesta branch e precisará de reconciliação antes de integrar.
- **Estado:** decisões de escopo aprovadas; UX detalhada, prioridade de implementação, revisão de Segurança/Arquitetura, baseline de código, evidência e G09/G10 continuam pendentes.

## Objective, scope and behavior contract

**Objective:** Fornecer experiência premium homogênea e acessível sem fundir os portais nem comprometer segurança.

**Functional contract:** Tokens, componentes e shells distintos preservam estados carregando/erro/vazio, foco e isolamento. São bloqueantes para a SPEC-018 os viewports 1366×768 e 1920×1080, ambos com zoom real 100% e 200%; 390×844 é exploratório na SPEC-018, porém segue OBRIGATÓRIO para o gate de release UX-08 da SPEC-006C.

**Rollback and failure behavior:** Falha de fetch, revogação e troca de fila limpam dados stale; layout deve preservar ações essenciais sem overflow.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Atender em qualquer viewport suportado (Priority: P1)

Como **operador**, quero responder e transferir sem controles cortados.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dados 1366×768 ou 1920×1080 com zoom real 100% ou 200%, quando abrir a Mesa e uma conversa, então compositor e ações essenciais são visíveis, acionáveis por mouse/teclado e não apresentam overflow horizontal no documento. A avaliação 390×844 é exploratória nesta feature, mas sua evidência continua bloqueante no release SPEC-006C UX-08.
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

- **FR-001**: Criar foundations e componentes reutilizáveis de tipografia, cores semânticas, espaçamento, foco, formulários, diálogo, tabelas e estados loading/vazio/erro/feedback com visual leve, consistente e pouco sombreado; não introduzir framework visual novo sem ADR.
- **FR-002**: Manter shells independentes para Operador, Supervisão, Administração, Auditoria e Laboratório, respeitando os papéis e rotas existentes. Esta feature NÃO implementa Monitoria, papel MONITOR ou qualquer grant novo; portal e RBAC de Monitoria pertencem à SPEC-010. Não promover links, visibilidade ou CSS à condição de autorização.
- **FR-003**: Garantir WCAG 2.2 AA aplicável, foco visível e não obscurecido, rótulos acessíveis, movimento reduzido e operação mouse/teclado; homologar 1366×768 e 1920×1080 com zoom real 100% e 200% como gate da SPEC-018. Documentar exploração 390×844 sem dispensar UX-08 mobile da SPEC-006C.
- **FR-004**: Limpar cache e estado protegido em logout, revogação, troca de identidade, fila e escopo; rejeitar resultados assíncronos obsoletos (request generation) sem reexibir outra fila. Backend permanece única fronteira de autorização.
- **FR-005**: Inventariar jornadas críticas existentes, testar mouse/Tab/Enter/zoom e regressão visual por shell em laboratório sintético, com SHA, viewport, zoom real, papel, cenário e evidência sanitizada.

#### Additional requirements

- **FR-006**: Não reenviar automaticamente mutações de fila, atendimento ou transferência após timeout; confirmar sucesso por resposta e reconciliação do estado com CAS/idempotência. Mensagens de interface não podem afirmar persistência sem confirmação.
- **FR-007**: Preservar os contratos de ações N1→N2, nota interna segregada, histórico VERIFIED restrito, Admin lifecycle DRAFT→ARCHIVED, auditor read-only, cancelamento de fetch stale e ausência de scroll horizontal global durante refinamento visual.

## Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- DesignToken, AccessibleComponentContract, WorkspaceShell.
- ViewportEvidence, UXAcceptanceRecord.

### Acceptable evidence and decision boundaries

A matriz UX18-01..08 mede jornadas por persona, mouse e teclado, viewport real, zoom, estado de autorização e resultado. Cada evidência inclui SHA, ambiente TEMP, browser, resolução, zoom, screenshots sanitizadas e resultado PASS/FAIL/BLOCKED. Não usar snapshots de dados reais nem credentials. Mudança de SHA invalida a herança automática de evidências. A SPEC-006C UX-08 mobile é acompanhada separadamente.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 controles essenciais cortados, cobertos por avisos ou não acionáveis nos quatro pares desktop/zoom 1366×768 @ 100% e 200%, 1920×1080 @ 100% e 200%; QA mobile 390×844 é obrigação distinta da SPEC-006C.
- **SC-002**: 100% das tarefas críticas da matriz aprovadas por teclado e mouse, com foco visível, ausência de intercepção de clique e feedback coerente.
- **SC-003**: 0 conteúdo protegido stale após revogação, troca de fila/identidade ou resposta de fetch atrasada.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

- **SC-005**: 0 mutações mutantes reenviadas automaticamente pela interface após timeout; 0 avisos de sucesso sem resposta confirmada; 0 expansão de papéis/rotas.
- **SC-006**: 100% dos cenários bloqueantes com evidência do SHA exato e revisão independente. Revisão estática ou contrato CSS não substitui teste de navegador.

## Scope exclusions

- Refazer a SPA inteira antes de entrega funcional.
- Framework visual novo sem ADR ou necessidade comprovada.
- Portal MONITOR, mudanças RBAC/backend, produção, integração real de Teams, alteração da POC SQLite original.

## Assumptions

- Personas implementadas nesta feature: operador, supervisor, administrador e auditor; laboratório é contexto sintético. Monitoria e role MONITOR são futuros na SPEC-010, não capacidades existentes.
- O Product Owner aprovou em 21/10/2026 APENAS Q1 (desktop/zoom bloqueantes para SPEC-018) e Q2 (Monitoria na SPEC-010). A prioridade da wave, identidade visual, arquitetura e entrega de runtime exigem as revisões próprias. Nenhuma autorização de merge/produção.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
