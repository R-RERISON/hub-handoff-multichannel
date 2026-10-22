# SPEC-018 U2 — Jornadas operacionais

- **Branch local:** `feat/spec018-u2-operational-journeys-20261022`
- **Base U1:** `4ad1ffed1e5202698009777135f5bd55d224a32b`
**Status:** gate automatizado e homologação funcional/visual desktop PASS na worktree local; T004/T005, evidência por SHA e aceite final pendentes.

## Escopo deste incremento

- O diálogo de oferta mantém foco dentro do modal, recupera foco após a decisão e conserva a nota de transferência como conteúdo interno.
- A Mesa serializa mutações, não repete POST após resultado incerto e bloqueia novas ações até uma atualização explícita confirmar o estado.
- A conversa do operador remove mensagens anteriores antes de carregar outro detalhe e falha fechada se a leitura autorizada falhar.
- Supervisão e histórico verificado distinguem carregamento, erro, vazio e revogação; respostas obsoletas e conteúdo protegido são descartados.
- O lifecycle administrativo mantém CAS por `expected_version` e bloqueia submissões simultâneas.
- O formulário de criação de fila Admin empilha os controles em largura móvel estreita e limita o botão ao contêiner.
- Nenhuma alteração de backend, RBAC, rotas, schema, migrations, integração Teams ou banco SQLite original.

## Execução automatizada local

Na raiz do worktree U2:

```powershell
.\start.cmd --check
```

O comando cobre Pytest, Ruff, contratos frontend, TypeScript e build Vite. A evidência final deve registrar o SHA do commit U2; enquanto o trabalho estiver sem commit, não declarar um SHA de código U2 aprovado.

Evidência automatizada obtida no worktree local, ainda sem commit U2:

- `.\start.cmd --check`: exit code 0; Pytest 199 passed / 1 skipped, Ruff aprovado, 38 contratos frontend, TypeScript e Vite aprovados (1604 módulos).
- `npm run build`: 38 contratos aprovados, TypeScript e Vite aprovados.
- `git diff --check`: aprovado.
- A execução corresponde à worktree baseada no SHA U1 acima; como as alterações U2 ainda não foram commitadas, não há SHA imutável de código U2 aprovado.

## Homologação funcional/visual executada

Usar somente laboratório sintético TEMP iniciado pelo launcher, com schema 007a2 quando o cenário exigir lifecycle. Não usar `data/handoff-poc.db`, não executar `--reset-users`, e não copiar credenciais para logs, comentários ou evidências.

Executada em laboratórios sintéticos TEMP; telas verificadas nos quatro pares desktop/zoom.

| Jornada / resultado | Evidência observada |
|---|---|
| Operador N1→N2 | Ana aceitou no N1, respondeu, transferiu com nota interna; Bruno recebeu a nota antes do aceite, respondeu e encerrou. A nota foi exibida como `role=note`, fora do transcript. |
| Modal e teclado | No zoom real de 200% em 1366×768, foco inicial no aceite, Tab/Shift+Tab confinado, footer de ações permaneceu visível; o corpo rolável tinha `scrollHeight=341` e `clientHeight=201`. Enter aceitou a oferta e o foco retornou ao composer. |
| Timeout de mensagem | POST abortado por fault injection: uma única chamada, UI exibiu resultado não confirmado e bloqueou novas mutações. Atualização explícita reconciliou; um envio manual posterior apareceu uma vez. |
| Admin lifecycle | Fila sintética passou DRAFT→ACTIVE→PAUSED→ARCHIVED; diário 007a2 confirmou 4 eventos e versão final 4. Confirmação funcionou por Tab/Enter. Teste de resposta 409 simulada ao duplo clique enviou um PATCH, manteve DRAFT e solicitou atualização de versão. |
| Supervisor | Loading visível durante fetch atrasado; resposta obsoleta após trocar seleção não apareceu (`STALE_SUPERVISOR_SENTINEL` ausente). Resposta 403 simulada removeu o detalhe e exibiu estado de erro. Lista vazia foi observada em sessão sem atendimentos correntes. |
| Auditor | Segmento VERIFIED N1 foi somente leitura; nota interna e mensagem N2 não apareceram. Grant N1 foi revogado/restaurado com o utilitário sintético; a UI limpou conteúdo ao revalidar. O seletor manteve N2 vedada. |
| Auth/revogação | Heartbeat/dashboard 401 simulados levaram à tela de login e removeram os dados anteriores. |
| Auditoria backend | `release_audit_scenarios` e `release_audit_evidence` PASS no laboratório 006b4: LIST/DETAIL autorizados, negativas cross-queue 404, grant cycle e journals confirmados. `release_probe.py` PASS em banco efêmero. |
| Layout desktop | Operador, Administração, Supervisão/Conversas e Visão geral sem overflow horizontal em 1366×768 e 1920×1080, a 100% e 200% (DPR 2 nas medições 200%). Rolagem horizontal da tabela Admin funcionou por teclado. |
| Mobile exploratório | Admin e Supervisão/Conversas em 390×844 sem overflow horizontal; o formulário Admin agora empilha campos e botão sem corte. Isso não certifica os demais portais nem satisfaz o gate UX-08 mobile da SPEC-006C. |

Uma captura sanitizada do formulário Admin em 390×844 foi preservada em
`$env:TEMP\handoff-spec018-u2-evidence\admin-390x844-fixed.png`; ela não está no repositório nem fixa um SHA U2. As demais capturas foram inspecionadas no navegador integrado, mas não arquivadas. A matriz por SHA de T017 permanece pendente. Não incluir credenciais, tokens, conteúdo pessoal ou IDs sensíveis em arquivos/logs.

## Pendências e gates

- T004 — revisão formal independente de Segurança/Arquitetura.
- T005 — freeze formal da baseline, distinto da seleção local do branch.
- T015/T016 — PASS nesta worktree; repetir após commit para fixar evidência no SHA U2.
- T017 — capturas sanitizadas/rastreabilidade por SHA e matriz completa de personas ainda pendentes.
- T009/T010 — fechamento da evidência e gate formal U1.
- G09/G10 — revisão independente e aceite humano continuam fora deste incremento.

O início da implementação por solicitação do Product Owner não aprova esses gates, não autoriza merge e não declara produção.

Os serviços anteriores foram encerrados conforme solicitado; a homologação U2 usou o launcher e a página integrada em laboratório TEMP. Os laboratórios sintéticos permanecem temporários para inspeção e descarte explícito após aceite.

## Rollback

O incremento é frontend-only e não exige migração. Interromper a homologação se houver dado stale ou mutação duplicada; reverter somente as alterações U2 nesta branch e repetir os gates no SHA revisado. Não restaurar, migrar ou modificar a POC original.
