# Handoff Hub Multichannel

Plataforma independente de orquestração de atendimento humano para bots, agentes de IA e canais corporativos.

> **Status:** FOUNDATION / SPEC-001. Esta branch contém um esqueleto de aplicação e artefatos de arquitetura; **não existe ainda um serviço de handoff operacional**. Não usar em produção.

## Estratégia aprovada para iniciar

**Embedded-first / Native-ready**. O usuário segue no chat com o bot original do Microsoft Teams. Um adapter autenticado desse bot transporta mensagens para o Hub. O Hub centraliza filas, sessão, operador, SLA e auditoria. O operador atende no workspace próprio, independentemente do bot. No futuro, o Hub terá aplicação/bot próprios para o modo Native.

## Stack

- Python 3.12+ / FastAPI, domínio modular
- SQL Server (SPEC-002), migrations, reservas transacionais e inbox/outbox duráveis
- React + TypeScript (SPEC-004)
- Microsoft Entra ID / OAuth2 / RBAC por tenant/operação
- Integração Cisco Finesse opcional
- Hospedagem on-premises ou híbrida

## Documentação

- [Constituição e gates](CONSTITUTION.md)
- [Instruções para agentes](AGENTS.md)
- [Contexto arquitetural](docs/architecture/overview.md)
- [ADR-0001 — Estratégia de plataforma](docs/architecture/ADR-0001.md)
- [ADR-0002 — Identidade do canal](docs/architecture/ADR-0002-channel-ownership.md)
- [SPEC-001 — Fundação](docs/specs/SPEC-001-foundation.md)
- [Contrato API (rascunho, não implementado)](docs/contracts/openapi.yaml)
- [Roadmap por SPECs](docs/roadmap.md)
- [Segurança](docs/security.md)
- [Compatibilidade com o legado](docs/legacy-compatibility.md)

## Rodar a fundação localmente

Requer Python 3.12 ou mais recente.

    python -m venv .venv
    python -m pip install -e ".[dev]"
    ruff check .
    pytest -q
    uvicorn handoff_hub.main:app --reload

A API implementa apenas:
- GET /health/live — liveness do processo.
- GET /health/ready — 503 **intencional** até existir persistência/auth/worker validados.

A proposta de POST /v1/handoffs está apenas no documento OpenAPI. A SPEC-002 implementará os pré-requisitos para o primeiro endpoint de negócio.

## Segurança e limites

Não publicar código do sistema legado, credenciais, domínios internos, payloads reais, identidade de usuários, histórico corporativo ou URLs privadas. Este repositório é privado, mas isso não substitui a política corporativa de proteção de dados.
