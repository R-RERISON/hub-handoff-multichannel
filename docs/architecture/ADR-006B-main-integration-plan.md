# Plano de consolidação das branches na `main` — Handoff Hub

**Snapshot verificado no GitHub em 16/10/2026, antes de abrir a 006B-5.2:**
- Repositório privado `R-RERISON/hub-handoff-multichannel`; `main` no SHA `7de0e16976ee856280ebb82366380580ccb956a6`.
- 19 branches (incluída a `main`) e 18 PRs abertos, **todos Draft, nenhum mergeado**.
- `feat/006b5a-history-access-audit` no SHA `d341d28c573ae47f3f385b10b7f3581ae5a126c7`, **344 commits adiante** da `main` e **0 atrás**, `merge-base` igual à `main`. Portanto o desenvolvimento vigente não está incorporado à `main`.
- Após o snapshot, foi criada `feat/006b5b-security-decisions-journal`, aumentando o número de branches; contar novamente após a abertura de qualquer novo PR.

## Cadeia principal (PRs encadeados)

`main` → #1 Fundação → #7 POC-002 → #9 POC-003 → #11 POC-004 → #13 POC-005 → #16 SPEC-006A → #18 006B-1 → #19 006B-2 → #20 006B-3.1 → #21 006B-3.2 → #22 006B-3.3 → #23 006B-4.1 → #24 006B-4.2 → #25 006B-4.3 → #26 006B-5.1 → SPEC-006B-5.2 em homologação.

Os PRs #14 (RFC do modelo enterprise), #15 (006A foundation alternativo) e #17 (design 006B alternativo) **não pertencem à mesma cadeia principal** e exigem reconciliação documental ou fechamento informado; **não mesclar automaticamente suas alterações**.

## Política recomendada para promoção à `main`

1. **Congelar um marco de integração:** depois da SPEC-006B-5.2 atingir gates Windows e homologação visual/E2E pendente das 006B-4.x/5.x, criar PR de integração **do último head da cadeia para `main`**, sem cherry-pick seletivo da proveniência.
2. **Revisar esse diff integralmente**: hoje o head 006B-5.1 já envolve 99 arquivos e 344 commits além da `main`. Verificar Constituição, cobertura, migrações opt-in, autorizações, integridade do banco original, experiência no navegador e regressão de worker/operador.
3. **Gate de segurança obrigatório:** revisões das permissões por operação/fila, versões Alembic, auditoria e bloqueio fail-closed; testar banco novo versionado **em ambiente sintético isolado**, sem dar suporte de escrita ao SQLite original.
4. **Sem GitHub Actions:** anexar resultados `start.cmd --check`, inspeções e evidências manuais ao PR de integração.
5. **Escolher promoção de histórico conscientemente:** como a cadeia é ancestral direta da `main`, pode-se preservar os commits no merge de integração em vez de criar 18 merges redundantes. Confirmar atualização de `main` apenas após revisão e autorização de release. Nunca mesclar todas as branches antigas indiscriminadamente.
6. **Após a promoção:** conferir que `main` alcançou o SHA esperado e que não há commits inéditos nas branches; fechar PRs encadeados já incorporados ou marcados como substituídos **somente após verificação de merge-base e diff**. Apagar branches remotas somente após segurança, rastreabilidade e concordância do responsável.

## Bloqueadores de promoção

- Homologação manual das telas de Supervisor/Auditor, incluindo teclado, responsividade, estados sem proveniência e ambiente sintético.
- Auditoria 006B-5.1/5.2 em runtime com banco temporário 006b3/006b4, revalidação de grants e rollback de writes sob falha de journal.
- Decisões de release e segurança sobre retenção, imutabilidade, OIDC/Entra ID, SQL Server e Teams. **Essas últimas são gates de produção**, não necessariamente requisitos para trazer a POC validada à `main`.

**Conclusão:** atualmente a `main` não representa o produto demonstrado no Windows. Consolidar o código validado é uma tarefa planejada e controlada, distinta de habilitar integração corporativa em produção.
