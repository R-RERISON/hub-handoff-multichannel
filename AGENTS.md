## POC-005 — Identidade, autorização e roteamento (obrigatório)

- A navegação por perfil deve refletir **autorizações do backend**, nunca somente menus ocultos.
- Operador é definido pelo login autenticado. Não permitir simulação de identidade operacional nem atuação cruzada.
- Supervisor e admin não assumem ou respondem conversas do operador. Auditor possui somente leitura.
- A chave compartilhada antiga é válida apenas em testes explícitos create_app(api_key=...), não no runtime do launcher.
- Senhas de demo geradas na máquina do desenvolvedor, em data/demo-credentials.txt ignorado pelo Git; não publicar passwords, hashes, tokens ou IDs sensíveis.
- Worker local usa BEGIN IMMEDIATE + status online/heartbeat + capacidade + QueueMembership + DispatchTurn por fila. Não transformar em atribuição na memória.
- FIFO de tickets e round-robin persistido por fila. Nova oferta envia destinatário ao fim da ordem; cooldown para recusas e expiração.
- Modal de ofertas em Mesa do Operador, alertas do navegador com consentimento, e API protegida por papel.
- Sem GitHub Actions. Sempre fornecer git pull, start.cmd --check, start.cmd e evidências/pendências.
- Para produção: OIDC/Entra ID, Alembic, multioperação, worker externo e Teams adapter ainda são gates.

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

## Entregas com Git e VS Code
- Fonte oficial: branch do GitHub, com atualização por `git pull --ff-only`.
- Para cada entrega, informar branch, mudanças, comandos de atualização, execução e testes locais, com resultados reais e pendências.
- Não utilizar GitHub Actions. Não substituir Git por pacotes ZIP como forma principal de entrega.
- Instruções completas em `docs/local-development.md`.

## Inicializador local (padrão vigente)
Usar `start.cmd` na raiz como **entrada única** para FastAPI e React/Vite no mesmo terminal.
- `start.cmd --lab` cria novo SQLite TEMP sintético Alembic 006b4 com credenciais próprias e inicia ambos os servidores para homologação. `start.cmd --lab --lab-dir <TEMP>` retoma exatamente o mesmo laboratório.
- `start.cmd` sem `--lab` continua o comportamento habitual com o SQLite POC original; **não utilizar para homologação de migrações, RBAC ou auditoria sintética**.
- `start.cmd --check` executa Python/Ruff/testes frontend e build. Não herdar `HANDOFF_DB_URL` no runtime da POC original nem nos gates.
- Não usar `start.cmd --reset-users` na POC original para testes do laboratório, nem permitir cópia de credenciais entre modos.
- Sempre documentar mudanças e evidências reais em `docs/setup-one-command.md` e no PR #28. Sem GitHub Actions.


## POC-004 — Contrato definitivo de workspaces

- Workspaces de Operador, Supervisão e Administração possuem **URLs e shells independentes**. Não reintroduzir operações de resposta/transferência nos painéis de supervisão.
- Laboratório possui rota própria; não distribuir botões de simulação entre páginas operacionais.
- `web/src/App.tsx` coordena os snapshots, autenticação de laboratório e roteamento; funcionalidades das páginas ficam em `web/src/workspaces/` ou no componente específico da Mesa do Operador.
- Novo fluxo: autenticação local → escolha de portal → navegação contextual. Isso **não substitui RBAC**.
- Testes obrigatórios via `.\start.cmd --check`: Pytest, Ruff, `npm run test:architecture`, TypeScript e Vite. Não usar GitHub Actions.
- Workspace novo não pode esconder comandos essenciais abaixo do viewport. Validar múltiplas resoluções e acesso por teclado.
