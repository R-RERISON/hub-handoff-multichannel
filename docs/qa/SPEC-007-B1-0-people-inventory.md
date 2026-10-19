# SPEC-007/B1.0 — Inventário administrativo de pessoas (desktop-first)

**Estado:** CODED / WINDOWS_QA_REQUIRED / SECURITY_REVIEW_REQUIRED / PR_DRAFT.
**Base congelada:** B0.1 `f00becd35134f5960867528abc649506c33aac71` (PR #49).
**Ambiente:** SQLite POC com fixtures sintéticas no TEMP; nenhuma migração de schema.

## Objetivo e modelo
A B1.0 introduz a projeção GET /v1/admin/people e o componente
AdminPeople na workspace de Administração. Identidade autenticada (AuthUser),
perfil operacional (Operator), vínculo de despacho (QueueMembership) e grants
(QueueRoleGrant) **não** se confundem. O endpoint não retorna grants nem os
altera; membership não concede histórico ou acesso à fila.

## Contrato e segurança
- Bearer individual, ADMIN somente; 401 sem login, 403 em outros papéis.
- Consulta da operação efetiva da sessão, nunca enviada pelo cliente.
- Operadores e contas filtrados por operation_id; vínculos exigem a operação
  correspondente **tanto da Queue quanto do Operator**.
- Contagens ACTIVE/OFFERED restritas à operação; nenhum conteúdo de conversa.
- Retorno de nome/ID de operador, presença, capacidade, ocupação, filas
  associadas; contas: username, papel, atividade e vínculo de perfil operacional.
- Sem hash, senha, token, mensagem, requester_label, conteúdo de sessão,
  grants ou identificadores de conversa.
- Sem endpoint de escrita em /admin/people e sem migrar banco original.
- Interface desktop com tabelas independentes, filtro local de operadores,
  atualização, estado vazio e tratamento de erro sem manter dados obsoletos.

## Casos automatizados adicionados
1. ADMIN/bearer obrigatório, SUPERVISOR/AUDITOR/OPERATOR negados.
2. Operação externa não aparece em operadores, filas ou contas; operador
   local sem membership permanece visível; nenhum efeito colateral.
3. Membership não é usado como concessão: dados separados e alteração
   por AUDITOR recusada.

## Gates pendentes
- Em worktree TEMP isolada, executar .\start.cmd --check no SHA final:
  pytest integral, Ruff, arquitetura frontend, TypeScript e Vite.
- Rodar pytest -q tests/test_spec007_b1_people_inventory.py e regressões
  B0.1 / operações N1→N2 / queue lifecycle.
- QA manual Edge/Chrome com viewport 1366x768 e 1920x1080; navegação Tab,
  zoom 200%, atualização após login/logout e estado 401/403.
- Revisão independente do diff: tenancy, projeções mínimas, LGPD,
  regressões, documentação e eventual integração.
- Sem GitHub Actions, sem deploy, sem merge automático.

## Limites e rollback
B1.0 é inventário **somente leitura**, não faz criação/desativação de pessoa,
não concede/revoga grants nem escreve membership. B1.1/B2 entregarão
operações auditadas e UX de mutação. Rollback consiste em abandonar/reverter
os commits B1.0 sem tocar no banco POC original.
