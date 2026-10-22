# Implementation Plan — SPEC-018: Design system leve, acessível e experiência operacional

**Branch:** feat/spec018-u2-operational-journeys-20261022 (implementação local sobre U1)
**Status:** PO_Q1_Q2_APPROVED / U2_FUNCTIONAL_QA_PASS_WORKTREE / T004_T005_PENDING / NOT_ACCEPTED
**Fonte de verdade:** CONSTITUTION.md > .specify/memory/constitution.md > SPEC-006C para gates de release > SPEC-018 para critérios desta feature. O processo Spec Kit local continua responsável por regenerar/validar após reconciliar a worktree descoberta.

## 1. Decisões e limites

| ID | Decisão | Estado |
|---|---|---|
| DEC-018-01 | 1366×768 e 1920×1080, zoom real 100%/200%, bloqueiam SPEC-018 | APROVADA pelo PO em 21/10/2026 |
| DEC-018-02 | 390×844 exploratório na SPEC-018; SPEC-006C UX-08 mobile continua bloqueante para release | APROVADA sem waiver da SPEC-006C |
| DEC-018-03 | Monitoria e papel MONITOR pertencem à SPEC-010; nenhuma rota/role nova aqui | APROVADA pelo PO |
| DEC-018-04 | Prioridade W1/P0, aprovação visual e início de implementação | PENDENTE de revisão formal |
| DEC-018-05 | SHA de runtime candidato: PR #59 c4bbf981f0d049951d0b04fb5a78d421ceb42808, Draft sobre #57; não misturar código com branch documental | PENDENTE de estabilização e revisão de Segurança/Arquitetura |
| DEC-018-06 | Worktree local spec/018-premium-workspace-ux contém alterações não commitadas reportadas | RECONCILIAR; nunca sobrescrever automaticamente |

## 2. Tech context / constitutional check

Frontend React, TypeScript, Vite e CSS existentes, sem framework novo. Backend FastAPI/SQLAlchemy/SQLite é autoridade RBAC, ownership, dados e mutações; SPEC-018 não altera backend/migrações. QA exclusivamente local em laboratório SQLite sintético TEMP com credenciais protegidas; start.cmd --check, Ruff, node tests, TypeScript e Vite. Não executar GitHub Actions, migrações sobre POC original, deploy, merge ou E2E corporativo.

**Gates antes da implementação:** revisão de Segurança/Arquitetura (grants, requests obsoletas, UI não é RBAC), reconciliação local e freeze do SHA funcional depois do PR #59. Implementar U1/U2/U3 em blocos, cada um com teste local e PR separado, preferindo revisão consolidada.

## 3. Static inventory / existing code

- App.tsx é owner das rotas, sessões, heartbeat e logout; não redistribuir RBAC para menus.
- OperatorDesk.tsx tem modal de oferta, nota interna, transferência, feedback e composer; preservar actions N1→N2 e role=alertdialog/nota.
- AdminLanding.tsx e AdminPeople.tsx têm tabelas focáveis, criação, CAS e estados; CAS PATCH nunca é repetido automaticamente.
- ScopedVerifiedHistory.tsx controla seleção de fila, list/detail e grants; mudanças de escopo devem limpar UI e ignorar resultados defasados.
- SupervisorOverview/Queues/Team/Conversations e DemoLab mantêm shells próprios, sem Monitoria.
- styles.css possui regras legadas concentradas e tokens pontuais; consolidar por aproximação incremental, sem reescrita e sem aumentar peso visual.
- web/scripts/workspaces.test.mjs já contém contratos de G07, administração, escopo e no-retry; **não removê-los** para satisfazer novos testes.

## 4. Design foundations U1 — pacote integrado

**Entregáveis:** inventário de componentes visuais e estados por persona; matriz semântica; tokens para superfícies, texto, borda, hover, focus, status, espaçamento, radius e tipografia com fallback; primitivas de button, field, notice, dialog, data region, loading, empty, denied. Aparência clara, baixa elevação, densidade calibrada, nada de cards/sombras excessivos.

**Riscos:** CSS amplo pode regredir actionability em zoom 200%, ocultar foco ou dar affordance a ação não permitida. Medida: mudança incremental sem tocar na semântica JS/contratos do backend; teste de arquitetura e revisão de diff por shell.

**Gate U1:** capturas sintéticas por tela e 4 pares viewport/zoom desktop, pesquisa por tarefas críticas (Fitts/Hick, consistência e carga cognitiva sem substituir validação), teste de contraste verificável e foco, sem regressão da Mesa/admin/histórico.

## 5. Operational UX U2 — pacote integrado

**Mesa:** oferta modal, Aceitar/Recusar, nota rolável separada do transcript, mensageria, transferência e encerrar acionáveis por mouse/Tab/Enter, inclusive zoom 200%. Não repetir POST/PATCH após timeout.

**Supervisão/Auditoria:** distinct loading, empty, denied, error, revogação e troca de fila; generation key para principal/fila/sessão/solicitação, limpar estados protegidos e descartar fetch tardio, sem conteúdo N2 no N1.

**Admin:** tabela e linhas legíveis, região scroll por teclado, transição com versão CAS, feedback resultado/reconciliação sem afirmar sucesso a partir de timeout.

**Gate U2:** uma sessão N1→N2 e uma administração lifecycle DRAFT→ARCHIVED, auditor 404, logout 401, grant revoke, ausência de vazamento/overflow/botão bloqueado, com amostras de latência API e segurança.

## 6. Certification U3 — pacote integrado

Matriz UX18-01..08 + UX18-E1; cada cenário com SHA, persona, contexto concedido, viewport físico, innerWidth CSS, zoom real, browser/version, input mouse/teclado, resultado, captura sanitizada e riscos.

| Caso | Persona | Critério |
|---|---|---|
| UX18-01 | Operador | Aceitar/Recusar oferta com mouse e Tab/Enter, visíveis em 200% |
| UX18-02 | Operador | Nota extensa e transferência N1→N2 sem interceptação |
| UX18-03 | Operador | Mensagem/error/timeout sem retry mutante nem falso sucesso |
| UX18-04 | Supervisor/Auditor | VERIFIED segmentado N1/N2 sem nota externa |
| UX18-05 | Auditor | Revoke/grant durante fetch sem stale protegido |
| UX18-06 | Admin | Tabelas de filas/pessoas/grants roláveis sem overflow global |
| UX18-07 | Admin | Criar fila, CAS, diário e DRAFT→ARCHIVED sem dupla mutation |
| UX18-08 | Todos atuais | Login/logout, loading/error/empty/denied e foco |
| UX18-E1 | Exploração | 390×844 na SPEC-018; **release UX-08 SPEC-006C separado** |

**Gate U3:** start.cmd --check e suite específica no SHA congelado, análise de diffs, WCAG 2.2 AA aplicável, teclado/mouse, imagens sanitizadas e QA do release mobile SPEC-006C separado. G09 independente e G10 humano antes de merge de RC; aceite de feature não é produção.

## 7. Rollback / risk management

Sem migração ou schema. Rollback isolado de CSS/componente no PR U1/U2; jamais restaurar/modificar SQLite original. Em falha de dados stale ou affordance insegura, bloquear, reverter no branch e refazer gates do SHA atualizado. Mudanças funcionais de PR #59 e posteriores não são trazidas automaticamente à SPEC. Não publicar tokens, dados reais ou capturas contendo segredo.

## 8. Prerequisites and plan gates

- [x] Q1 e Q2 do PO aprovadas na conversa em 21/10/2026; SPEC-006C preservada.
- [x] Inspeção estática da árvore documental e de componentes frontend do SHA do PR #59 realizada para preparar inventário.
- [x] Diff da worktree local spec/018-premium-workspace-ux comparado e preservado antes da reconciliação na branch U2.
- [ ] Aprovação de Segurança/Arquitetura e direção visual.
- [ ] Seleção do SHA estabilizado após revisão independente do incidente #58/PR #59.
- [ ] Executar o Spec Kit local /speckit-plan, /speckit-tasks, /speckit-analyze e /speckit-converge; este arquivo é preparação versionada, não evidência de sua execução.
- [ ] Tests/U1, tests/U2, tests/U3, G09, G10 e decisão formal de merge.

## Registro da implementação local U2

Por solicitação explícita do Product Owner, a implementação U2 começou em uma worktree isolada sobre o SHA U1 `4ad1ffed1e5202698009777135f5bd55d224a32b`. O PR #59/liveness permanece na ancestralidade do baseline; nenhuma branch foi integrada, publicada ou mesclada.

O escopo alterado é frontend-only: foco do modal de oferta, single-flight/reconciliação das mutações, estados de histórico, invalidação de snapshots obsoletos e empilhamento do formulário de criação Admin em viewport estreito. Não houve alteração de backend, RBAC, rotas, schema, migrations ou POC original.

`.\start.cmd --check` passou nesta worktree: Pytest 199 passed / 1 skipped, Ruff, 38 contratos frontend, TypeScript e Vite (1604 módulos). O código U2 segue sem commit, portanto essa evidência ainda não representa um SHA imutável de entrega.

Homologação funcional/visual desktop T015/T016 foi executada em laboratório sintético TEMP no estado de worktree, incluindo foco/scroll em zoom real, mutações N1→N2, revoke/restore, 401/403/404/409 e timeout. Não houve expansão RBAC ou alteração de schema.

T004 (revisão formal de Segurança/Arquitetura), T005 (freeze formal da baseline), T009/T010 (gate formal U1), T017–T023, G09 e G10 permanecem pendentes. Não há SHA U2 imutável porque as mudanças seguem sem commit; repetir o gate automatizado no SHA final antes de publicar. A homologação 390×844/UX-08 da SPEC-006C continua em trilha separada.
