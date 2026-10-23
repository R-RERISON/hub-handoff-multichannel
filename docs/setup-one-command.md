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

A revisão independente do diff B0.1 não identificou vulnerabilidades no escopo
revisado. A auditoria transacional das mutações de equipe continua pendente para
B1/B2; a decisão formal de integração também permanece pendente. Não houve merge
ou promoção à `main`.

## Evidência local — SPEC-018 U2 — commit de implementação

Na branch local `feat/spec018-u2-operational-journeys-20261022`, a implementação
U2 foi congelada no SHA `49db5f424aaa13b9631715c3721f264499070eab`, baseada no U1
`4ad1ffed1e5202698009777135f5bd55d224a32b`. `.\start.cmd --check` confirmou o
HEAD esperado e terminou com exit code 0: **199 testes Python aprovados, 1
ignorado, Ruff aprovado, 38 testes frontend aprovados, TypeScript e Vite
aprovados (1604 módulos)**. `git diff --cached --check` passou antes do commit.

O gate foi executado no SHA de implementação informado acima. O commit e a
worktree continuam locais, sem upstream, push, merge ou deploy. `git pull
--ff-only` no checkout principal `fix/rc001-issue58-api-liveness` retornou
`Already up to date`; a branch U2 local não recebeu pull.

Na homologação integrada, o laboratório 007a2 percorreu N1→N2, nota interna,
resposta e encerramento; lifecycle administrativo DRAFT→ACTIVE→PAUSED→ARCHIVED
gerou quatro eventos persistidos. Fault injection 409 confirmou uma única
mutation e nenhuma transição no estado stale. O timeout sintético no composer
gerou um único POST, bloqueio até refresh e envio manual posterior sem duplicação.
O laboratório 006b4 confirmou revoke/restore de grant Auditor, leituras VERIFIED,
negações cross-queue 404 e diários; `release_audit_evidence` retornou PASS.
`release_probe.py` também retornou PASS em banco efêmero.

Mesa, Administração, Visão geral e Conversas da Supervisão foram verificadas
sem overflow horizontal nos quatro pares 1366×768/1920×1080 a 100%/200%. No
zoom real de 200%, o modal manteve footer/foco e rolou seus detalhes; Tab/Shift+Tab,
Enter, rolagem de tabela, retorno ao composer e estados de revoke/erro foram
exercitados. Não houve alteração de backend, RBAC, schema, migrations ou POC
original. O roteiro está em
[SPEC-018 U2 — Jornadas operacionais](qa/SPEC-018-U2-OPERATIONAL-JOURNEYS.md).

Na exploração 390×844, Administração e Conversas da Supervisão não tiveram
overflow horizontal; os campos e o botão de criação Admin ficaram empilhados
e dentro do painel. Isto não é certificação mobile nem aprovação de UX-08 da
SPEC-006C.

O gate automatizado foi repetido no SHA de implementação após o commit. T004/T005,
T009/T010, T017–T023, G09/G10 e UX-08 mobile de SPEC-006C continuam pendentes.
Nenhum PR, merge ou deploy foi realizado.

## SPEC-019 — Premium UX em todo o sistema

Branch de trabalho criada sobre a branch U2 publicada:
`feat/spec018-ux-premium-batch-20261022`. Base de implementação U2:
`641ea2fc3c77c7f365f36f8af939f7e404a44c84`. Commit de implementação:
`8aa60368a5a33deb8c8446b5db6126353af3286a`. A branch está publicada e [PR #62](https://github.com/R-RERISON/hub-handoff-multichannel/pull/62) permanece Draft; nenhum merge ou deploy foi feito.

O pacote é frontend-only: navegação e login acessíveis; limpeza de conteúdo
protegido em negação; orientação interna de oferta com estados explícitos;
confirmações seguras para operações de fila/equipe/administração; tabelas
semânticas; rótulos e erros em português; correção de contraste/foco e copy
factual da POC. Não altera RBAC, identidade, API, schema, migrations, SQLite
original ou entrega externa ao Teams.

### Gate automatizado local

```powershell
Remove-Item Env:HANDOFF_DB_URL -ErrorAction SilentlyContinue
.\start.cmd --check
```

Resultado real: exit code 0; **199 testes Python aprovados, 1 ignorado; Ruff
aprovado; 49 contratos frontend aprovados, 0 falhas; TypeScript aprovado; Vite
aprovado (1606 módulos)**. `git diff --check` e `npm run build` também passaram
na worktree.

### Laboratório e navegador integrado

Foi criado um laboratório sintético novo por `.\start.cmd --lab --no-browser`,
migrado offline de 006b4 para 007a2 com backup verificado e retomado pelo
launcher. Nenhuma requisição foi direcionada a `data/handoff-poc.db` ou às
credenciais do modo POC normal. A validação usou o browser integrado em Edge/
Chromium; os dados e credenciais do laboratório ficaram somente em TEMP.

| Superfície/persona | Validação observada |
|---|---|
| Login e seleção Admin | Login válido chegou à seleção de espaços; login inválido mostrou orientação genérica em português com `role=alert` assertivo; a seleção inclui botão Sair. |
| Administração | Três tabelas com caption/cabeçalhos/row headers e rolagem interna; em 390×844, 1366×768 e 1920×1080, @100%/@200%, sem overflow horizontal do documento. Criar fila foi 1 POST; a nova fila apareceu imediatamente na visão da Supervisão. Cancelar lifecycle enviou 0 PATCH; confirmar arquivamento enviou 1 PATCH. O diálogo coube em 960×540 CSS px a 200% (sem overflow/falha de contraste), focou Cancelar, aceitou Tab/Shift+Tab e devolveu foco ao botão acionador. |
| Supervisão | Visão geral, Conversas, Filas, Equipe e Laboratório verificados em 390×844 e nos dois viewports desktop a 100%/200%; sem overflow horizontal do documento. Equipe apresentou tabela semântica com caption e cabeçalhos. |
| Supervisor — Filas | Injeção sintética 403 na rotação removeu membros da tela, exibiu estado de acesso negado e permitiu revalidar com sucesso; nenhuma mutação foi enviada. |
| Supervisor — Equipe | Alteração de capacidade abriu confirmação com alvo/impacto; cancelar enviou 0 PATCH. Confirmar enviou 1 PATCH e atualizou a capacidade; a alteração sintética foi revertida com outra confirmação/1 PATCH. |
| Auditor | Navegação mostrou apenas Visão geral e Conversas; segmentos verificados permaneceram somente leitura e sem controles de resposta. A rota direta `/supervisao/filas` foi negada e o retorno levou a Conversas. |
| Operador | Oferta exibiu explicitamente ausência de orientação interna; a 200% real em 1366×768, o modal e as duas ações couberam na viewport e o foco inicial ficou em Aceitar. Aceite enviou 1 POST e moveu foco ao compositor. A resposta local informou que não foi enviada ao usuário final. |
| Operador — falhas | POST de mensagem com 503 sintético enviou 1 requisição, não foi repetido e bloqueou ações com “Resultado não confirmado”. Poll de conversa com 403 após exibir conteúdo-sentinela sintético removeu o conteúdo, a seleção e o compositor; o sentinela não permaneceu visível. |
| Responsividade e contraste | Matriz visual em todos os portais para 390×844, 1366×768 e 1920×1080, @100%/@200% reais (DPR 2 no zoom), sem overflow horizontal global. Scanner de contraste sobre texto visível nas telas/estados exercitados não encontrou pares abaixo do limiar aplicável. |

O scanner de contraste cobre apenas texto renderizado nos estados visitados; não equivale a certificação WCAG integral nem verifica todos os estados hover/não textuais. Capturas foram inspecionadas no browser integrado, mas não exportadas ao repositório. A matriz e limitações estão em [SPEC-019 Premium UX](qa/SPEC-019-PREMIUM-SYSTEM-UX.md).

### Inicialização segura para nova rodada

`.\start.cmd --lab --no-browser` cria um diretório TEMP único e imprime seu
caminho. `--lab-dir` só retoma um laboratório existente. Para lifecycle, parar
os serviços, executar upgrade offline 006b4→007a2 nesse SQLite sintético com
backup verificado, inspecionar a revisão e então retomar com
`.\start.cmd --lab --lab-dir $lab --no-browser`. Não usar `.\start.cmd` sem
`--lab` para homologar estes fluxos. Não incluir credenciais sintéticas em
relatórios, screenshots, logs ou commits.

**Pendências**: revisão independente G09 e aceite humano G10; WCAG integral e
UX-08 mobile da SPEC-006C continuam gates separados. [PR #62](https://github.com/R-RERISON/hub-handoff-multichannel/pull/62) permanece Draft; nenhum merge ou deploy foi feito.

os serviços foram encerrados após a validação; as portas 8000/5173 estão livres.
O laboratório TEMP sintético e os logs de launcher desta rodada foram removidos.

### Convergência — validação complementar

Após os ajustes de foco e contraste, uma rodada isolada em laboratório TEMP 007a2
confirmou: timeout de lifecycle com um único PATCH, estado Rascunho preservado,
feedback sem sucesso falso e foco no alerta acessível; lifecycle confirmado com um
PATCH e foco no status de sucesso; vínculo de fila adicionado e restaurado, um PATCH
por confirmação e foco no feedback acessível. O 409 de vínculo preservou o estado e
focou o alerta sem permitir nova ação antes de revalidar. Nenhum dado da POC original
foi usado.

A revisão de estilos computados no browser verificou bordas de controles, foco em
superfícies claras/escuras, estado selecionado, hover, estado desabilitado e layout
390×844. Os contratos de contraste foram ampliados; isto não substitui certificação
WCAG integral. T034 foi validado por teclado por persona e rota primária; a matriz
sanitizada está em [SPEC-019 Premium UX](qa/SPEC-019-PREMIUM-SYSTEM-UX.md).

O gate após a convergência passou com `HANDOFF_DB_URL` removido e serviços parados:
199 testes Python aprovados, 1 ignorado; Ruff aprovado; 52 contratos frontend
aprovados; TypeScript aprovado; Vite aprovou 1606 módulos.
`git diff --check` também passou após as atualizações de evidência.
O laboratório TEMP complementar e os logs foram removidos; as portas 8000/5173
estão livres. A branch publicada contém o commit de implementação
`8aa60368a5a33deb8c8446b5db6126353af3286a`; [PR #62](https://github.com/R-RERISON/hub-handoff-multichannel/pull/62) está Draft, sem merge ou deploy.

### SPEC-019 — follow-up das correções G09

Foram implementados os três ajustes da revisão independente:

- Conversas e Filas agora incluem contagem e significado no nome acessível; o
  badge visual não duplica a leitura do link.
- Após 401/403/404 de conteúdo protegido, o Operador apaga os dados e a seleção,
  retorna o painel mobile para Atendimentos e foca o título da worklist. No
  browser, um 403 sintético removeu o sentinela; o contrato também cobre os três
  status.
- Após PATCH 403 da equipe, a tabela é substituída pelo estado negado, que recebe
  foco e mantém a ação de revalidação acessível.

A validação integrada confirmou os nomes acessíveis das contagens, o 403 do
Operador em viewport 390 px e o 403 da equipe, sem ampliar permissões. O primeiro
gate completo apontou um contrato antigo que esperava o padrão anterior de
`aria-label`; o contrato foi alinhado à nova expressão e a suíte final passou:
`npm run test:architecture` — 55 aprovados; `.\start.cmd --check` — 199 testes
Python aprovados, 1 ignorado, Ruff aprovado, 55 contratos frontend aprovados,
TypeScript aprovado e Vite com 1606 módulos.

O gate foi executado com `HANDOFF_DB_URL` removido e os serviços sintéticos
parados. A evidência detalhada está em [SPEC-019 Premium UX](qa/SPEC-019-PREMIUM-SYSTEM-UX.md).
G09 ainda exige revisão independente do commit atualizado; G10 e UX-08 da
SPEC-006C continuam gates separados. [PR #62](https://github.com/R-RERISON/hub-handoff-multichannel/pull/62) permanece Draft, sem merge ou deploy.
