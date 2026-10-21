# SPEC-018 — Inventário estático inicial para U1 (sem implementar CSS)

**Inspecionado:** head PR #59 c4bbf981f0d049951d0b04fb5a78d421ceb42808, Draft, 21/10/2026.
**Confiabilidade:** inspeção estática de arquivos e contratos; não equivale a screenshots, teste de zoom ou auditoria automática de contraste.

| Área | Estado observado | Guardrails U1 |
|---|---|---|
| web/src/styles.css (~988 linhas) | Regras antigas e locais, tokens pontuais --hub-bg/--hub-border/--hub-ink, vários @media; não foi identificada regra prefers-reduced-motion na inspeção | Estabelecer tokens sem reescrever CSS; avaliar contraste e motion explicitamente |
| web/src/App.tsx (~327 linhas) | Routing por persona, login/logout, heartbeat, avisos; separação supervisão/operador/admin | Não alterar autorização backend nem expor rota MONITOR |
| web/src/OperatorDesk.tsx (~413 linhas) | Modal role=alertdialog, corpo scrollável, nota separada, feedback, transferência, textarea | Preservar focabilidade, não cobrir Aceitar/Recusar, Transferir/Encerrar, nota não integrada ao chat |
| web/src/workspaces/AdminLanding.tsx (~211 linhas) | Criação de filas e lifecycle CAS, avisos, tabelas com scroll regional | Sem retry automático de PATCH; exibir loading/erro e versão com clareza |
| web/src/workspaces/ScopedVerifiedHistory.tsx (~271 linhas) | LIST/DETAIL VERIFIED, seleção por fila, paginação, estados e aria | Descartar dados de scope antigo e respostas tardias, não mostrar N2 para N1 |
| web/src/workspaces/Supervisor*.tsx | Shells distintos para equipes/filas/conversas/overview | Não confundir read-only Auditor com Supervisor |
| web/scripts/workspaces.test.mjs (~374 linhas) | G07: modal, feedback, scroll region, auth, CAS frontend sem retry | Manter e ampliar testes, jamais eliminar testes para permitir refactor |

## Prioridades recomendadas para desenho
**P0:** foco e clickability em zoom 200%; clear-on-revoke/fetch stale; feedback transacional e retry-safe.
**P1:** tipografia, densidade, cor semântica, hierarquia sem excesso de sombras, componentes consistentes.
**P2:** microinterações condicionadas a prefers-reduced-motion, responsividade mobile exploratória.

## Gate de saída de U1
Inventário assinado por UX/Segurança, fontes de tokens revisadas, evidência real dos quatro cenários viewport/zoom, keyboard+mouse e regressão G07 no SHA exato. Nenhuma aprovação U1 foi atribuída aqui.
