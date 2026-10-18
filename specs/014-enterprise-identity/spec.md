# Feature Specification — SPEC-014: Identidade corporativa Entra ID, OIDC e autorização granular

**Feature Branch**: `spec/014-enterprise-identity` (futura; não criada)
**Created**: 2026-10-18
**Status**: Draft / not implemented in this planning change
**Wave / Priority**: W1–W3 / P0
**Input**: reorganização do Handoff Hub Multichannel em features SPECKIT rastreáveis.
**Dependencies**: 006C baseline segura; 007 para gestão administrativa, antes de canal real

## Objective, scope and behavior contract

**Objective:** Validar identidade humana e técnica corporativa, revogação e isolamento de tenant/operação/fila.

**Functional contract:** Fluxos OIDC e tokens de integração são verificados por issuer/audience/tenant/exp; grants não são inferidos automaticamente.

**Rollback and failure behavior:** Token incorreto ou chaves indisponíveis resultam em deny; ambiente de produção não faz fallback para contas demo.

**Limit:** os critérios de aceite nesta SPEC definem comportamento; decisões de stack e forma de implementação ficam em [plan.md](plan.md). A etapa de planejamento não executa nem aprova runtime.

## User Scenarios & Testing

### User Story 1 — Entrar com identidade corporativa (Priority: P1)

Como **usuário corporativo**, quero autenticar com políticas da organização sem depender de senhas POC.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dado token inválido/expirado ou tenant incorreto, quando acessar API, então o acesso é negado no servidor.
2. Dada conta sem grant de fila, quando autentica corretamente, então não herda acesso a filas.

### User Story 2 — Revogar permissões efetivamente (Priority: P2)

Como **gestor de segurança**, quero suspender acesso em sessão ativa e auditar decisão.

**Independent Test**: executar a jornada isolada em ambiente autorizado com dados sintéticos.

**Acceptance Scenarios**:
1. Dada revogação de papel/grant, quando usuário repete consulta, então o acesso é negado sem reiniciar sessão.
2. Dado serviço de integração, quando usa token app-only, então não age como OPERATOR nem usa perfil humano.

### Edge Cases

- Rotação de chaves JWKS durante sessão.
- Grupos e claims sobrepostos.
- Tenant errado ou token destinado a outra API.

## Requirements

### Functional Requirements

- **FR-001**: Validar OIDC/OAuth2 token issuer, audience, exp, assinatura/JWKS, tenant, claims e políticas necessárias com rejeição fail-closed..
- **FR-002**: Separar usuários de contas não humanas, e definir scopes de integração, privilégios mínimos e ciclo de vida de autorização..
- **FR-003**: Persistir vinculação estável de identidade corporativa com usuário e grants por operação/fila, sem role via claim auto-concedida..
- **FR-004**: Garantir revogação efetiva, sessões, expiração, logout e logs de decisões, inclusive testes de IDOR e cross-tenant..
- **FR-005**: Manter autenticação POC apenas no launcher de laboratório, sem fallback local em ambiente corporativo..

### Security and data invariants

- Autorização obrigatoriamente no backend com grants por operação/fila, segmento, objeto e identidade efetiva.
- Proteger `data/handoff-poc.db` original; qualquer escrita/migração experimental somente em ambiente sintético controlado.
- Não publicar segredos, dados reais ou afirmar suporte a canal/produção sem E2E e gates correspondentes.

### Key Entities

- IdentityBinding, Principal, EnterpriseSession.
- IntegrationCredentialReference, RoleAssignment, GrantAudit.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 aceites de token expirado, forjado, audience/issuer incorreto.
- **SC-002**: 100% das rotas sensíveis com enforcement backend.
- **SC-003**: 0 contas de integração com papel humano implícito.
- **SC-004**: 100% dos critérios de aceite com evidência objetiva e revisão de segurança antes de declarar a SPEC aceita.

## Scope exclusions

- Distribuir senhas demo fora do laboratório.
- Quebrar mecanismos existentes de homologação sintética.

## Assumptions

- Personas: usuário corporativo, administrador IAM, serviço de integração.
- Esta SPEC não altera o código atual; prioridade e waves são propostas para revisão com Product Owner.
- Mudanças de modelo/contrato exigem ADR; direitos de acesso, dados pessoais e integrações exigem gates específicos.
