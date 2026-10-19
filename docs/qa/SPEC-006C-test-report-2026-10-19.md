# SPEC-006C — Registro de testes e correção I001 (19/10/2026)

## Proveniência

Resultado comunicado pelo executor local para uma cópia **temporária isolada**
de `origin/feat/006c2-browser-viewport-capture`, commit
`d342fe693dde43b125c159da5be1da39a780b47c`.

A branch principal de trabalho do executor permaneceu em
`feat/006b5b-security-decisions-journal` (`14e0156`), sem incorporar os
scripts novos. **Não houve alteração no banco POC original.**

O presente registro transcreve a evidência informada; não atribui execução
ou homologação local ao conector GitHub.

## Matriz de gates observada

| Gate | Resultado no commit d342fe6 | Observação |
| --- | --- | --- |
| Pytest | **PASS** | 142 passed, 1 skipped; 154,14 s |
| Ruff | **FAIL** | I001: ordenação de imports em `tests/test_release_ui_capture.py` |
| Frontend architecture | **PASS** | 15 testes |
| TypeScript e Vite | **PASS isolado** | Build de produção executado separadamente |
| `start.cmd --check` completo | **FAIL** | Parou no Ruff, sem alcançar o build frontend dentro desse gate |
| UX-02 Supervisor N1/N2 | **NOT_RUN** | Sem capturas nem homologação visual |
| UX-05 transferência N1→N2 | **NOT_RUN** | Sem capturas nem homologação visual |
| UX-08 responsividade | **BLOCKED** | Viewports 390×844, 1366×768, 1920×1080 não homologados |
| Revisão de segurança/diff do PR #28 | **PENDING** | Gate de decisão humana |
| Promoção à `main` | **BLOCKED** | PR #28 permanece Draft |

## Correção realizada

- Branch: `feat/006c2-browser-viewport-capture`
- Commit da correção: `a39dcc71e0d90602e87f3a8ebba5ac24430678e3`
- Arquivo: `tests/test_release_ui_capture.py`
- Mudança: ordenar os dois imports `scripts` conforme padrão Ruff/isort.
- Evidência estrutural via GitHub compare `d342fe6...a39dcc7`: **1 arquivo,
  1 linha inserida e 1 excluída**, sem alteração de testes ou runtime.

O patch é mínimo e não altera os critérios testados. Ainda assim, **nenhum
resultado da execução em d342fe6 aprova automaticamente o SHA corrigido**.

## Próxima validação obrigatória

1. Em cópia ou worktree isolado atualizar `origin/feat/006c2-browser-viewport-capture`.
2. Confirmar `git rev-parse HEAD` = `a39dcc71e0d90602e87f3a8ebba5ac24430678e3`.
3. Executar `start.cmd --check` inteiro, sem pular Ruff nem build.
4. Registrar contagem, duração, exit code e eventuais novas falhas **do novo SHA**.
5. Após gates locais verdes, iniciar apenas `start.cmd --lab` em TEMP 006b4,
   executar fixture/runner e realizar revisão humana UX-02/05/08.
6. Vincular capturas sanitizadas e decisões à [issue #29](https://github.com/R-RERISON/hub-handoff-multichannel/issues/29)
   e PRs #44/#45. O PR #28 não deve ser mesclado antes dos gates finais.

## Política de estado

**LINT_FIX_COMMITTED / RETEST_REQUIRED**. Não declarar `RELEASE_PASS`,
`UX_PASS`, `MERGED` ou `PRODUCTION_READY` com esta evidência.
