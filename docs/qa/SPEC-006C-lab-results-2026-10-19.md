# SPEC-006C — Execução de laboratório 19/10/2026 (relatório recebido)

**Origem:** relatório enviado pelo executor da rodada Windows, sem nova execução
de ferramentas locais por esta alteração. **SHA testado:**
`37f48af1204f016608d635b4a8c0146e1984e4e1`.

## Resultado reproduzido e limitação

| Gate | Situação informada |
| --- | --- |
| start.cmd --lab (TEMP 006b4) | PASS — API e Vite HTTP 200 |
| UX-02 backend, Supervisor N1/N2 | PASS |
| UX-05 backend, mensagens VERIFIED N1/N2 | PASS |
| Segregação da nota privada no histórico | PASS |
| Auditor N1 tentando N2 | HTTP 404, PASS |
| Supervisor enviando como operador | HTTP 403, PASS |
| Evidência visual UX-02/05/08 | NOT_RUN/BLOCKED |
| Pacote de PNGs | AUSENTE; --check foi executado antes da captura |
| SQLite POC original | Não foi tocado, conforme relatório |

A rodada gerou **1 sessão e 2 mensagens** no TEMP. Os serviços de lab foram
encerrados e a worktree e o banco TEMP removidos. A branch funcional
`feat/006b5b-security-decisions-journal` ficou em `14e0156`.

**Não inferir**: resultado PASS da captura, aprovação de release, finalização
da SPEC ou validação do novo código deste commit a partir desse relatório.

## Defeito de preparação visual identificado após a rodada

No código testado `37f48af`, o fixture transferia N1→N2 mas deixava
a sessão no estado QUEUED em N2, tornando a evidência da Mesa de Bruno
potencialmente vazia. A correção proposta completa despacho e aceite no
backend sintético. Essa alteração exige reexecução dos testes e homologação
visual em SHA novo.

## Próximas evidências

- Executar `start.cmd --check` integral no SHA atual, e opcionalmente
  `pytest tests/test_release_ui_scope_fixture.py` isoladamente.
- Iniciar `start.cmd --lab` em novo TEMP 006b4; rodar fixture uma vez.
- Executar `scripts.release_ui_capture --lab <TEMP> --browser msedge`
  **antes** do `scripts.release_ui_evidence_gate --lab <TEMP> --check`.
- Conferir 11 PNGs e proceder à revisão manual de identidade, conteúdo,
  notas, comandos e responsividade, com SHA/runtime confirmado.
- Preservar a pasta TEMP com capturas até a aprovação/registro, eliminando
  somente após sanitização e aceite das evidências.
