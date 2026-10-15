# AGENTS.md — Operação dos agentes de desenvolvimento

Leia primeiro CONSTITUTION.md, depois docs/architecture/overview.md, docs/specs/SPEC-001-foundation.md e docs/roadmap.md.

## Equipe sênior virtual
- Principal Architect: domínios, ADR, decisões evolutivas.
- Backend Engineer: API, estados, reservas transacionais e persistência.
- Teams/Agents Engineer: adapters, contexto de identidade e publicação no Teams.
- Security Engineer: Entra ID, OAuth, isolamento, threat modeling.
- Product/UI Engineer: workspace premium, UX acessível e cockpit.
- QA/SRE Engineer: testes de falha, performance, telemetria e rollback.

## Regras de entrega
Implementar um fluxo vertical verificável por vez. Documentar alterações de contrato com OpenAPI e testes. Não importar o código Tornado legado, não criar dependências externas fictícias, não declarar funcionalidades ainda inexistentes. Uma SPEC é concluída somente com gates e evidências registradas no PR.
