# AGENTS.md — Engenharia do Handoff Hub

Antes de qualquer desenvolvimento, leia CONSTITUTION.md, docs/architecture/overview.md, docs/poc-data-model.md e docs/roadmap.md.

## Agentes especialistas
- Principal Architect: domínios, ADRs, limites e desacoplamento de canais.
- Backend Engineer: FastAPI, SQLAlchemy, transações, idempotência.
- Database Engineer: SQLite POC, migração futura para SQL Server e modelagem.
- Teams Engineer: canais, bot ownership, conectores e mensagens.
- Frontend Engineer: React/TypeScript, UX responsiva e acessibilidade.
- Security Engineer: threat model, identidade, autenticação, isolamento.
- QA/SRE Engineer: testes locais, falhas, diagnóstico, observabilidade.

## Fluxo de trabalho
1. Revisar scripts legados como referência funcional, jamais copiá-los nem migrar dados.
2. SPEC pequena com invariantes, critérios de aceite e testes.
3. Implementar vertical slice backend, banco e frontend.
4. Executar Pytest, lint e build npm **localmente**, sem GitHub Actions.
5. Atualizar docs e PR com evidências, lacunas e plano de rollback.
6. Evitar dados pessoais, segredos, URLs internas e credenciais nos commits.

## Limites vigentes
- Versão v0.2 usa SQLite somente no host local e X-POC-Key (não corporativa).
- Não declarar integração Teams funcional sem adapter e teste E2E.
- Não apresentar schema create_all como estratégia de migração versionada.
- O frontend deve sinalizar claramente que mensagens são simulações.
