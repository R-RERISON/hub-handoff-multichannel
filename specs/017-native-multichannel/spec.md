# Feature Specification — SPEC-017: Teams Native e expansão multicanal/multibot

**Feature Branch**: `spec/017-native-multichannel` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W4 / P2
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 012 Embedded comprovado, 014, 015, 016; capability matrix de 011

## Objective, scope and behavior contract

**Objective:** Expandir canais por adapters independentes mantendo identidades e capacidades próprias.

**Functional contract:** Registro de bots/aplicativos expõe capabilities e escopo, cada canal mantém credenciais/conversation IDs distintos.

**Rollback and failure behavior:** Capacidade ausente gera falha explícita e status rastreável, sem falsa entrega; rollback por canal.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Conversar no app nativo (Priority: P1)

Como **usuário Teams**, quero iniciar conversa independente do bot de origem.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dada instalação permitida, quando usuário inicia no App próprio do Hub, então é criada conversa vinculada à identidade própria do app.
2. Dada conversa Embedded anterior, quando o usuário usa Native, então credenciais e conversation IDs permanecem isolados.

### User Story 2 — Adicionar outro bot/canal (Priority: P2)

Como **administrador**, quero configurar adapter com capacidades explícitas e observabilidade.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado canal somente texto, quando recebe imagem, então API indica capacidade indisponível sem perda nem falsa entrega.
2. Dada integração desativada, quando chega mensagem, então autenticação/ingresso é recusado sem alterar sessões.

### Edge Cases

- Teams tenant sem permissão de instalação.
- Canal sem suporte a conteúdo rico.
- Mensagem duplicada por dois adapters distintos.

## Requirements

### Functional Requirements

- **FR-001**: Implementar app/bot Teams próprio com processo de instalação, tenant/políticas e identidade própria, sem reaproveitar tokens/conversations do bot Embedded..
- **FR-002**: Ter registro de integração/canal com credenciais seguras, capability negotiation, health e configuração por operação..
- **FR-003**: Oferecer segundo adapter heterogêneo de forma testável, com protocolo canônico, quotas, isolamentos e feature flags..
- **FR-004**: Compatibilidade Copilot Studio/Direct Line deve ser PoC separada e explicitamente comprovada, não pressuposta..
- **FR-005**: Exigir E2E de canal, acessibilidade, fallback e rollback por integração..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- ChannelRegistration, NativeAppInstallation, ChannelCapability.
- ExternalIdentityBinding, IntegrationRoutingPolicy.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 compartilhamento de credenciais ou conversation ID entre bots.
- **SC-002**: 100% de capacidades declaradas com comportamento e testes.
- **SC-003**: 0 entregas marcadas concluídas sem ACK do canal.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- Integração universal automática com qualquer bot.
- Publicação fora do tenant piloto sem revisão de segurança.

## Assumptions

- Personas: usuário final, administrador de integração e canal.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
