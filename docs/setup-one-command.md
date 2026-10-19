# Inicialização em um comando — Handoff Hub POC 0.5 / QA 006b4

**Interface única:** `start.cmd`, executado na raiz do repositório. FastAPI e Vite iniciam
no **mesmo terminal**, com logs `[API]` / `[WEB]`. `Ctrl+C` encerra ambos.
Somente localhost (`127.0.0.1:8000` e `127.0.0.1:5173`).

## Spec Kit para novas mudanças

O repositório foi inicializado com [GitHub Spec Kit](https://github.com/github/spec-kit),
skills de GitHub Copilot e scripts PowerShell. O CLI local verificado nesta rodada
é `specify-cli 1.0.13`; em outra máquina, instale-o com `uv tool install specify-cli`.
Não é necessário adicionar dependência ao runtime Python ou frontend.

No chat do Copilot, use `/speckit-specify` para uma mudança delimitada e continue
com `/speckit-clarify` se necessário, `/speckit-plan`, `/speckit-tasks`,
`/speckit-analyze`, `/speckit-implement` e `/speckit-converge`. Os novos pacotes
de especificação são criados em `specs/`; `docs/specs/` continua contendo as
especificações históricas. Consulte a constituição em
`.specify/memory/constitution.md` e as instruções de engenharia em `AGENTS.md`.
O Spec Kit não altera o uso de `start.cmd`, não migra o SQLite original e não
adiciona GitHub Actions.

### Evidência local — 2026-10-18

Na branch `feat/006b5b-security-decisions-journal`, `specify init` instalou
as skills do Copilot e os templates/scripts PowerShell; `specify check`
confirmou que a instalação está pronta para uso no VS Code. `.\start.cmd --check`
aprovou **132 testes Python, 1 ignorado, Ruff, 16 testes de arquitetura
frontend, TypeScript e build Vite**. `git diff --check` também passou. A adoção
não altera o runtime nem o banco POC; a integração à `main` depende do fluxo
normal de revisão/publicação da branch e do PR #28.

## Homologação segura — recomendado

```powershell
.\start.cmd --lab
```

O launcher prepara automaticamente um **NOVO** SQLite versionado
`006b4_security_decisions` com **22 tabelas** e cinco identidades sintéticas, cria
credenciais aleatórias em `$env:TEMP\handoff-qa-006b4-<id>\synthetic-credentials.txt`,
inicia FastAPI e React/Vite na mesma janela e abre o navegador. Ele imprime
apenas a localização do diretório e do arquivo de credenciais, **não as senhas**.
O banco da POC original não é lido, adotado, migrado nem usado para seed neste modo.

Para executar novamente no **mesmo** laboratório e preservar histórico, usuários
e grants, copie o diretório mostrado ao inicializar:

```powershell
.\start.cmd --lab --lab-dir "$env:TEMP\handoff-qa-006b4-<id>"
```

O nome entre `<id>` é um exemplo; substitua pelo diretório real.
`--lab-dir` **não** cria, reseta ou migra banco algum. O utilitário recusa
qualquer caminho que não seja diretório `handoff-qa-006b4-*` filho direto de
`$env:TEMP`, symlinks para arquivos externos, e esquemas que não sejam um
laboratório semeado 006b4 (22 tabelas) ou um laboratório migrado explicitamente
para 007a2 (24 tabelas), ambos com cinco identidades e pelo menos duas filas.
Laboratórios novos continuam fixados em 006b4; só o comando offline
`upgrade-lifecycle --confirm-offline` os promove para 007a2.

Abra `synthetic-credentials.txt` localmente em um editor, sem publicá-lo.
O launcher não aceita chave de API compartilhada no runtime do laboratório.
`start.cmd --lab --no-browser` mantém o início unificado, sem abrir aba.

### Revalidação do Auditor — somente em laboratório

Com `start.cmd --lab --lab-dir ...` em execução e uma mensagem sintética N1
visível na sessão do Auditor:

```powershell
$lab = Join-Path $env:TEMP "handoff-qa-006b4-<id>"
.\.venv\Scripts\python.exe scripts\release_grant_toggle.py --lab $lab --action status
.\.venv\Scripts\python.exe scripts\release_grant_toggle.py --lab $lab --action revoke --confirm-synthetic
```

O utilitário confere o token do banco temporário **por um GET somente leitura**
contra a API ativa e faz alterações **somente** no SQLite sintético explicitamente
selecionado. No navegador do Auditor, clicar em **Atualizar permissões** deve
esvaziar imediatamente as mensagens carregadas e remover N1.

Para restaurar:

```powershell
.\.venv\Scripts\python.exe scripts\release_grant_toggle.py --lab $lab --action restore --confirm-synthetic
```

Não compartilhar senha/token nem apontar o utilitário para o SQLite original.

## Evidência de auditoria após revoke/restore

Use o mesmo diretório TEMP, preferencialmente enquanto o laboratório ainda
está disponível. A ferramenta consulta somente o SQLite 006b4, em modo
read-only, sem tocar no banco original nem realizar requisições à API.

```powershell
$lab = Join-Path $env:TEMP 'handoff-qa-006b4-1ohg0707'
.\.venv\Scripts\python.exe -m scripts.release_audit_evidence --lab $lab
```

`PASS` confirma quatro conjuntos de evidências: grants N1/N2 corretos,
ciclo revogar/restaurar com diário, leituras verificadas LIST+DETAIL e ao
menos uma negativa de acesso auditada. `INCOMPLETE` (exit code 2) indica
quais cenários ainda não possuem evidência neste banco, sem presumir falha
do backend. A saída não inclui IDs, senha, token ou texto da conversa.

Procedimento completo de navegador e critérios de aceite em
[PR #28 — Gates visuais finais](qa/PR-028-ui-final-gates.md).

### Rodada Windows de 2026-10-18

Na base `6da3061` com correção local do painel de eventos, `start.cmd --check`
aprovou **132 testes Python, 1 ignorado, 15 contratos frontend, Ruff,
TypeScript e Vite**. A fixture de paginação, o release probe e AUD-01 passaram
no laboratório TEMP. UX-06 e teclado do histórico verificado foram exercitados
no navegador; a correção limita a área de eventos com rolagem acessível, sem
recortar a paginação inferior.

Isso não libera a `main`: UX-08 completo (capturas com viewport estável e Mesa
do Operador) e os demais cenários visuais pendentes continuam obrigatórios.
Resultados, dimensões reais, limites e indisponibilidade de publicação no
PR #28 estão no [registro de execução](qa/PR-028-ui-final-gates.md#execução-local-windows--2026-10-18).
As alterações desta rodada são entregues na branch
`feat/006b5b-security-decisions-journal`, sem integração na `main`.

## Completar evidências AUD-01 e SEC-01 (laboratório TEMP)

Quando `release_audit_evidence` retornar `INCOMPLETE` para as leituras
`LIST`/`DETAIL` ou negativas `DENIED`, execute o runner **mutável e
explícito** abaixo. Ele atesta a API de `start.cmd --lab --lab-dir $lab`
na porta 8000, cria **um atendimento e uma mensagem 100% sintéticos no
banco TEMP**, e realiza LIST/DETAIL autorizados e duas negativas 404 com
o Bearer do Auditor. Não altera grants e não solicita tokens manualmente.

```powershell
# Com start.cmd --lab --lab-dir $lab ativo em outro terminal:
.\.venv\Scripts\python.exe -m scripts.release_audit_scenarios --lab $lab --confirm-synthetic
if ($LASTEXITCODE -ne 0) { throw "Execucao sintética de auditoria reprovada" }
.\.venv\Scripts\python.exe -m scripts.release_audit_evidence --lab $lab
```

O primeiro comando **grava dados sintéticos de QA e journals no laboratório**;
o segundo permanece **estritamente read-only**. Não chamar esse runner na
POC original, nem em outras pastas fora de `$env:TEMP\handoff-qa-006b4-*`.
Consultar `docs/qa/PR-028-release-acceptance.md` para todas as evidências
e pendências visuais.

## Execução habitual da POC original

```powershell
.\start.cmd
```

**Sem `--lab`**, o comportamento histórico é preservado: FastAPI e Vite
iniciam juntos, usando apenas `data/handoff-poc.db` e as credenciais individuais
já mantidas em `data/demo-credentials.txt`, ignorado pelo Git. O launcher
não executa migrações Alembic no banco POC original. `--setup-users` e
`--reset-users` operam exclusivamente no modo POC habitual; **nunca são parte
dos gates do laboratório TEMP**.

Mesmo que a sessão PowerShell tenha herdado `HANDOFF_DB_URL` ou
`HANDOFF_POC_KEY`, a execução habitual remove essas variáveis antes de iniciar
a API ou executar o seed, evitando apontar inadvertidamente para outro banco.
Para não tocar no SQLite original durante homologação, escolha **`--lab`**.

## Testes e ferramentas

```powershell
.\start.cmd --setup-only  # dependências apenas
.\start.cmd --check       # Pytest, Ruff, testes frontend, TypeScript e Vite
.\.venv\Scripts\python.exe scripts\release_probe.py  # banco TEMP 006b4 autocontido
.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect  # POC original read-only
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run  # POC original read-only
```

`--check`, `--setup-only`, `--setup-users` e `--reset-users` não podem
ser combinados com `--lab`. O launcher recusa portas 8000 e 5173 já ocupadas,
sem matar ou conectar-se silenciosamente a outro servidor. As contas de laboratório
são criadas somente na primeira inicialização de cada diretório TEMP.

## Restrições de release

- Sem GitHub Actions, Teams real, OIDC/Entra ID ou SQL Server na POC local.
- Não executar `adopt`, `stamp`, `upgrade*` ou `create` no SQLite POC original.
- `Ctrl+C` encerra API/Vite, **mas não apaga** os dados do laboratório TEMP; remover
  o diretório de testes manualmente ao concluir a homologação e encerrar processos.
- `docs/qa/PR-028-release-acceptance.md` contém os gates UX, RBAC e auditoria para
  consolidação na `main`. PR #28 permanece Draft até homologação.

## Evidência local — SPEC-007/A1.2 — 2026-10-19

Na branch `feat/007a2-queue-lifecycle`, commit `6503d30`, `.\start.cmd --check`
terminou com exit code 0: **162 testes Python aprovados, 1 ignorado, Ruff,
16 testes de arquitetura frontend, TypeScript e Vite (1.601 módulos)**.
Os oito testes específicos do ciclo de vida passaram; o teste novo de retomada
confirma que `--lab-dir` reabre um 007a2 validado sem alterar o SQLite.

A migração offline do laboratório TEMP preservou todas as contagens 006b4,
criou as tabelas de ciclo de vida vazias e validou o backup antes do upgrade.
Depois, a Mesa Administrativa criou uma fila sintética e percorreu
DRAFT → ACTIVE → PAUSED → ARCHIVED, com quatro eventos auditados, sem
memberships/grants automáticos. O mesmo laboratório foi encerrado e retomado
com o histórico persistido.

O navegador integrado foi verificado em 1366×768 e 1920×1080, sem overflow
horizontal; o foco por Tab alcançou a confirmação da transição. As capturas
PNG verificadas foram preservadas em
`$env:TEMP\handoff-qa-006b4-air5z1nu\qa-evidence-a1.2`.
Revisão de segurança e integração continuam pendentes; não houve merge nem
promoção à `main`.

## Evidência local — SPEC-007/B0.1 — 2026-10-19

Na branch `feat/007b0-people-boundary-hardening`, commit `49a28ad`,
`.\start.cmd --check` terminou com exit code 0: **170 testes Python aprovados,
1 ignorado, Ruff, 16 testes de arquitetura frontend, TypeScript e Vite
(1.601 módulos)**. Os oito testes específicos em
`tests/test_spec007_people_boundaries.py` passaram.

O ADMIN sintético recebeu HTTP 404 em tentativas cross-operation para
capacidade, presença e membership, sem alteração ou enumeração dos dados.
Também passaram os cenários de revogação de sessão e mudança de papel após
preflight, grants parciais para operador multi-fila, capacidade insuficiente
para ocupação e remoção de membership com atendimento ativo. Todos usaram
SQLite TEMP; a POC original não foi usada.

Auditoria das mutações de equipe e revisão independente de segurança continuam
pendentes para B1/B2 e antes da integração. Não houve merge ou promoção à `main`.
