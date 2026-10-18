# PR #28 — Plano de homologação manual e segurança da integração

> **Atualização operacional de 17/10/2026:** o modo recomendado para todos os testes visuais é `start.cmd --lab` (um terminal para API e frontend). Os exemplos antigos com dois arquivos `run-backend.ps1`/`run-web.ps1` e o preparador PowerShell foram preservados como evidência histórica, **não são mais necessários**. `start.cmd` **sem** `--lab` continua abrindo a POC original.

**Estado (18/10/2026):** gate automatizado `start.cmd --check` aprovado no commit `d591b2f` (**125 Pytest aprovados, 1 skipped, Ruff, 13 testes frontend, TypeScript e Vite**). SEC-01 API e AUD-01 journals aprovados no laboratório 006b4 (`audit_release_result=PASS`, 1 LIST, 1 DETAIL, 2 negativas 404), com backend atestado. SEC-02 backend/UX PASS; SEC-03 backend/STATUS PASS, **SEC-03 UI ainda pendente**. As alterações posteriores a `d591b2f` ainda precisam do gate Windows no SHA final.  
**Ambiente:** Windows PowerShell 5.1+ / Python 3.12+ / Node/npm local. Sem GitHub Actions ou serviços externos.  
**Candidato:** `feat/006b5b-security-decisions-journal`, revisão de banco **006b4** exclusiva do laboratório sintético.

## 0 — Proteção do banco POC original (bloqueante)

- **Jamais executar** `adopt`, `stamp`, `upgrade`, `upgrade-audit`, `upgrade-security`, `create` ou `--reset-users` em `data/handoff-poc.db`.
- O banco original deve ser usado **somente** em `schema_admin inspect` e `provenance_dry_run`.
- Os scripts de release usam `tempfile.TemporaryDirectory` e `$env:TEMP` para banco e credenciais **independentes**. Não se aplica migração no original.
- **Usar `start.cmd --lab` para homologação sintética:** cria SQLite 006b4 e credenciais em TEMP e inicia FastAPI + Vite no mesmo terminal. **Nunca** usar `start.cmd` sem `--lab` para testar segurança no SQLite temporário, pois esse modo usa a POC original.
- Encerrar qualquer execução anterior nas portas 8000/5173 antes dos testes browser.

## 1 — Gate automatizado reproduzível (novo)

Na branch candidata atualizada, ambiente virtual ativo:

```powershell
.\start.cmd --check
if ($LASTEXITCODE -ne 0) { throw 'Gate Python/Ruff/Frontend reprovado' }

.\.venv\Scripts\python.exe scripts\release_probe.py
if ($LASTEXITCODE -ne 0) { throw 'Gate 006b4 sintetico reprovado' }

.\.venv\Scripts\python.exe -m handoff_hub.schema_admin inspect
.\.venv\Scripts\python.exe -m handoff_hub.provenance_dry_run
```

`scripts/release_probe.py` cria um banco temporário 006b4, contas locais e sessão sintética. Via FastAPI TestClient autenticado por Bearer, verifica: leitura VERIFIED N1 autorizada; N2 negada; revogação N1 com efeito imediato; restauração do grant; trilhas `history_access_audit` e `security_decisions` sem texto sensível; falha de INSERT causando rollback do grant; falha de registro de negativa **preservando 404**. Apaga o laboratório ao final. **Não** lê nem altera o banco POC real.

### Evidências exigidas

| Gate | Aprovação |
|---|---|
| Pytest completo, Ruff, 13 frontend architecture, TypeScript, Vite | Todos aprovados no SHA final |
| `release_probe.py` | JSON `result=PASS`, `database_scope=EPHEMERAL_SYNTHETIC_ONLY`, `table_count=22` |
| `schema_admin inspect` no original | `integrity=ok`, `revision=null`, `table_count=17` |
| `provenance_dry_run` no original | `rows_written=0`, `backfill_applied=false`, `safe_for_history_authorization=false` |

## 2 — Preparar laboratório visual sem tocar no original (método vigente)

```powershell
.\start.cmd --lab
```

O comando único prepara banco, contas e credenciais TEMP, inicia API + Vite e abre o navegador. Para **retomar** a mesma massa de dados depois do Ctrl+C, execute `start.cmd --lab --lab-dir "<diretório TEMP informado na tela>"`. `start.cmd` sem `--lab` continua sendo a POC original.

O `start.cmd --lab` cria um diretório **novo** sob `$env:TEMP\handoff-qa-006b4-<id>`, com `synthetic.db` e `synthetic-credentials.txt`; valida revisão `006b4_security_decisions` e 22 tabelas. **Não** grava credenciais no repositório e inicia a API e o Vite no mesmo terminal. Somente o preparador PowerShell legado gera `seed-synthetic.py`, `run-backend.ps1` e `run-web.ps1`.

O fluxo legado `prepare-main-integration-lab.ps1` ainda existe para referência, mas **não é necessário no modo atual**. Se usado isoladamente, os dois launchers temporários gerados continuam opcionais; recomenda-se `start.cmd --lab`. No navegador: `http://127.0.0.1:5173`. Leia as contas locais em `synthetic-credentials.txt` (não publicar). O backend usa `HANDOFF_DB_URL` apenas dentro do processo desse terminal; ambos os serviços ficam em `127.0.0.1`.

Caso um serviço antigo esteja usando 8000/5173, **encerre-o**, sem reaproveitar um backend que pode estar apontando para o banco original.

## 3 — Checklist UI/UX e segurança (teste humano)

| ID | Perfil / teste | Resultado esperado | Estado |
|---|---|---|---|
| UX-01 | Login como `auditor.demo`; abrir Supervisão → Conversas → Segmentos verificados | Somente leitura; menu de filas concedidas exibe **N1**, nunca N2 | PENDENTE |
| UX-02 | Login como `supervisor.demo`; selecionar N1 e N2 | Somente filas concedidas, sem ação de envio como operador | PENDENTE |
| UX-03 | Banco sintético 006b4 inicial vazio | `schema_ready=true`, mensagem de ausência de segmentos; não inventar histórico legado | PENDENTE |
| UX-04 | Criar atendimento sintético por Laboratório e registrar mensagem na fila N1 | Mensagem do segmento VERIFIED aparece em N1 após atualização; N2 não a mostra | PENDENTE |
| UX-05 | Se existir transferência sintética N1→N2 com evidência runtime | Cada fila só enxerga suas mensagens/eventos; nota privada nunca é exibida no VERIFIED | PENDENTE |
| UX-06 | Paginação de mensagens e eventos | Controles independentes, rótulos claros, nenhum avanço para página inexistente | PENDENTE |
| UX-07 | Teclado: Tab, Shift+Tab, Enter, Space e foco visível | Botões, seleção de fila e paginação acessíveis; nenhum controle inacessível | PENDENTE |
| UX-08 | Resoluções: 1366×768, 1920×1080 e largura 390px | Sem cortes de controles, textos sobrepostos ou scroll horizontal indevido | PENDENTE |
| SEC-01 | Auditor N1 tenta abrir N2; ou usa ID de outra fila | API devolve 404 sem conteúdo/IDs de outra fila; o browser não mantém payload exibido após nova negativa | API PASS (LIST+DETAIL 404); UX pendente |
| SEC-02 | ADMIN revoga grant N1 do AUDITOR durante sessão ativa; usuário atualiza | Próxima consulta bloqueia; mensagens previamente carregadas não permanecem exibidas após a tentativa negada | PASS backend + UI, usuário confirmou |
| SEC-03 | ADMIN restaura grant; auditor recarrega | Acesso volta a funcionar, sem atravessar fila; logs exibem `GRANT_REVOKED` / `GRANT_ENABLED` | Backend + STATUS PASS; UI pendente |
| AUD-01 | Verificar `schema_admin --database <synthetic.db> inspect` | `history_access_audit` e `security_decisions` possuem linhas de acesso; original não tem essas tabelas | Journals sintéticos PASS; inspeção original separada pendente |

**Observação de segurança:** o UI não pode fazer revogação de grant pelo operador/auditor; fazer alteração somente como ADMIN, e apenas no banco sintético. Não colar tokens Bearer nem dados privados em screenshots. O backend é a autoridade final; limpeza de estado no frontend é defesa adicional.

## 3.1 — AUD-01 e SEC-01: evidências persistidas exclusivamente em TEMP

**Ferramenta não intrusiva:** `python -m scripts.release_audit_evidence`. Executa apenas
`verify_database` e leituras SQLite `mode=ro` / `PRAGMA query_only`, com validação
estrita do diretório TEMP e revisão 006b4. Não faz login, requisição HTTP, seed,
migração, PATCH, nem imprime senhas, tokens, IDs, conteúdos, histórico ou nomes
reais de usuários.

```powershell
$lab = Join-Path $env:TEMP "handoff-qa-006b4-1ohg0707"
.\.venv\Scripts\python.exe -m scripts.release_audit_evidence --lab $lab
$gateExitCode = $LASTEXITCODE
Write-Host "AUD-01 exit code: $gateExitCode"
```

A saída contém exclusivamente contagens e flags de gate (sem identificadores
individuais): `security_grant_cycle`, `final_auditor_scope`,
`history_read_journal` (LIST e DETAIL para N1 do Auditor) e
`denied_access_journal`. **PASS** exige todos os quatro critérios; se faltar
algum dado, retorna `INCOMPLETE`, explica-o em `pending` e encerra com
código **2**. Isso NÃO significa necessariamente falha do produto: pode indicar
que um cenário ainda não foi executado neste laboratório. Falha de diretório
ou banco recusa a execução sem abrir o SQLite POC original.

Evidências Windows já informadas: `REVOKE` PASS, 1 `GRANT_REVOKED`,
`RESTORE` PASS, 1 `GRANT_ENABLED`, `STATUS` posterior PASS com
`auditor_has_n1=true` e sem novo evento de grant. A remoção do histórico
quando o Auditor clica em `Atualizar permissões` foi confirmada manualmente.
**Ainda falta** verificar e registrar SEC-03 na UI após restauração (N1
reaparece, N2 permanece vedada). AUD-01 foi executado posteriormente,
em 18/10/2026, e retornou PASS (1 LIST, 1 DETAIL, 2 DENIED).

**Não** executar `--reset-users` nem alterações de grant para conseguir
contagens artificiais; evidências devem refletir testes reais da sessão.

## 4 — Evidência e critérios de bloqueio da `main`

- Anexar ao PR #28 a saída dos gates, capturas de UX **sem senhas, tokens ou dados reais**, resolução utilizada, perfis e identificação dos testes aprovados.
- Qualquer falha em RBAC, isolamento por fila, persistência de auditoria obrigatória ou alteração do SQLite original **bloqueia merge**.
- Se houver apenas divergência cosmética, registrar como issue separada com prioridade/risco e decisão explícita, sem declarar gate completo aprovado.
- Se houver erro do probe ou teste manual, anexar somente mensagem de falha sanitizada. Não alterar o banco original para reproduzir o problema.
- Após os testes, encerrar API/Vite com Ctrl+C **no terminal único do `start.cmd --lab`** e remover a pasta `handoff-qa-006b4-...` do `$env:TEMP` somente quando não precisar mais dos testes sintéticos.

## 5 — Estado da revisão de código

Verificada a cadeia Git (`main` ancestral do head), ausência de merge automático e isolamento do schema em `006b4`. Ainda falta inspeção final completa de mudanças em 104 arquivos, análise de concorrência, revisão visual e confirmação dos gates deste novo SHA. **Nenhuma homologação visual foi realizada pelo assistente.**

**Não transformar a aprovação destes gates em declaração de prontidão corporativa:** OIDC/Entra ID, SQL Server, Teams, retenção LGPD e imutabilidade/WORM permanecem fora do escopo desta POC.


### Correção identificada no Windows — 17/10/2026

A primeira execução do preparador criou corretamente o banco sintético 006b4 com 22 tabelas, mas **interrompeu no seed**: `python -c` via PowerShell 5.1 perdeu as aspas da expressão f-string, causando `SyntaxError: invalid syntax` em `fsqlite:///`. Corrigido para criar e executar `seed-synthetic.py` dentro do diretório temporário, sem `-c`. A correção não altera o SQLite original, o FastAPI, o frontend ou as migrações. O novo script **ainda precisa ser reexecutado no Windows** para fechar o gate de preparação de laboratório; a pasta temporária da execução falha não deve ser reutilizada.


## 6 — SEC-02/03: revogação/restauração real com API do laboratório

**Ferramenta:** `scripts/release_grant_toggle.py`. Utiliza credenciais sintéticas sob `$env:TEMP` e verifica que o **ID da conta ADMIN na API é igual ao ID do banco temporário** antes de qualquer mutação; rejeita caminhos fora de `$env:TEMP\handoff-qa-006b4-*`. Nunca imprime senhas nem tokens. O comando modifica **somente** o grant `AUDITOR` da fila `n1` no banco sintético, por `PATCH /v1/admin/queue-grants`.

1. Mantenha `start.cmd --lab --lab-dir <diretório>` ativo no mesmo terminal (API em 8000, Vite em 5173); **não inicie `start.cmd` sem `--lab`**. Mantenha o Auditor autenticado no navegador e com uma mensagem **sintética** N1 aberta em `Segmentos verificados`.
2. Substitua o valor de `$lab` abaixo pelo diretório TEMP efetivamente criado pelo seu preparador (não utilize o caminho `data\handoff-poc.db`):

```powershell
$lab = Join-Path $env:TEMP 'handoff-qa-006b4-2912f1b7191a4648984c856d4e53b6a2'
$python = '.\.venv\Scripts\python.exe'
& $python scripts\release_grant_toggle.py --lab $lab --action status
& $python scripts\release_grant_toggle.py --lab $lab --action revoke --confirm-synthetic
if ($LASTEXITCODE -ne 0) { throw 'Revogação sintética falhou' }
```

3. No navegador do Auditor, **não faça logout nem recarregue a página**. Clique em **Atualizar permissões**. Resultado esperado: a seleção, a listagem e o conteúdo de N1 desaparecem **imediatamente ao clicar**, antes de a API devolver o novo conjunto de grants. Quando a resposta chegar, o seletor informa que não há fila concedida; nenhum histórico ou conteúdo privado deve ficar visível. O backend deve negar explicitamente N1 para o Auditor em chamadas subsequentes.
4. Restaure o grant, ainda somente no laboratório:

```powershell
& $python scripts\release_grant_toggle.py --lab $lab --action restore --confirm-synthetic
if ($LASTEXITCODE -ne 0) { throw 'Restauração sintética falhou' }
```

5. No navegador, clique **Atualizar permissões**. N1 deve voltar ao seletor e ser consultável, sem conferir permissão N2 ao Auditor. O script confere persistência e o incremento auditado `GRANT_REVOKED`/`GRANT_ENABLED`; a auditoria de cada consulta do histórico continua sendo responsabilidade do backend.

**Não usar esse procedimento em `data/handoff-poc.db` e não compartilhar o arquivo `synthetic-credentials.txt`.** A ausência de WebSocket/SSE implica que conteúdo previamente carregado só será limpo quando houver uma ação de revalidação, troca de fila, nova consulta, logout ou navegação que remonte a tela; não afirmar revogação proativa em tempo real na interface.

### Correções de UI decorrentes das capturas

- Antes de consultar grants novamente, a UI limpa `queues`, `queueId`, `listing`, `selectedId`, `detail` e a paginação. Enquanto o resultado não chega, informa que está validando permissões.
- Falha de `/v1/me/queues` esvazia permissões e conteúdo; erro no endpoint de listagem/detalhe mantém `detail=null`, sem conteúdo residual.
- A barra lateral agora identifica `POC 0.5` e explica que `Conversas` conta apenas atendimentos correntes, não segmentos históricos.
- Metadados de histórico usam texto maior, foco visível e painéis de altura mínima mais compacta. O acabamento precisa de nova avaliação em 390px, 1366×768 e 1920×1080 após a atualização.

**Evidência existente:** cinco capturas mostram a mesma sessão N1→N2, os segmentos independentes (mensagens `bom dia`/ `claro`), a nota interna apenas na mesa do destinatário e confirmação de outbox local. Isso não comprova, isoladamente, a revogação em sessão nem paginação/teclado/responsividade.

**Estado:** novas modificações de frontend, utilitário Python e testes estáticos publicados na branch candidata; os gates automatizados do novo SHA e o teste visual de revogação ainda estão pendentes. Não promover a `main` com base nos testes antigos.


### Windows — falha do primeiro `release_grant_toggle.py` e correção de segurança

O gate automático no HEAD `f3a94b2` concluiu **111/111 Pytest (96.78s), Ruff, 13/13 arquitetura frontend, TypeScript/Vite** e `release_probe.py=PASS` (2 reads, 4 decisões de segurança; SQLite TEMP 006b4, sem payload sensível). A execução de `release_grant_toggle.py --action revoke` falhou com diagnóstico excessivamente genérico. **Não há comprovação de que o grant tenha sido revogado** nessa tentativa.

**Correção da ferramenta:** novas versões fazem LOGIN via FastAPI `TestClient` explicitamente ligado ao banco `$lab/synthetic.db` (credenciais permanecem locais). Antes de qualquer PATCH, usam o token sintético recém-criado para fazer **somente GET `/v1/auth/me`** em `127.0.0.1:8000`; a API precisa reconhecer esse token e devolver o mesmo ID, username e papel AUDITOR do banco. Um backend da POC original, mesmo com mesmos usernames, não possui essa sessão sintética e é rejeitado **antes de qualquer mutação**, sem tentativa de senha no original. O PATCH administrativo é executado pelo `TestClient` **diretamente no banco TEMP**; sucesso é corroborado por `queue_role_grants` e por `security_decisions`.

Diagnósticos permitidos são literais/limitados (`API local indisponivel na porta 8000`, `API local nao reconhece a sessao do SQLite sintetico`, operação TEMP devolveu HTTP específico, etc.), sem credenciais, tokens, sessão ou resposta da API. Os testes automatizados adicionais exercitam rejeição de diretório fora do TEMP, bloqueio de escrita quando a atestação falha, revogação e restauração transacionais no banco sintético, e 401 de uma API diferente.

**Pré-condições de execução:** usar preferencialmente **um único `start.cmd --lab --lab-dir <diretório TEMP>`** ativo com ambos os serviços. Nunca iniciar `start.cmd` sem `--lab` durante a homologação, pois ele usa o SQLite original. Se houver falha, enviar apenas a mensagem de diagnóstico sanitizada do utilitário, nunca `synthetic-credentials.txt`.

**Estado:** nova correção e testes ainda não homologados no Windows. Não promover à `main`.


### 17/10/2026 — Diagnóstico de atestação com `start.cmd --lab`

O laboratório `handoff-qa-006b4-1ohg0707` foi criado por `start.cmd --lab` e o usuário executou, posteriormente, `release_grant_toggle.py --action status` e `--action restore --confirm-synthetic`. Ambos foram **REPROVADOS ANTES DO PATCH** com `API local nao reconhece a sessao do SQLite sintetico`. Não há evidência de alteração de grant; o bloqueio preventivo está correto. **Ainda não foi comprovado se a porta 8000 executava o laboratório correto no momento do teste.**

Correção **diagnóstica**: o utilitário agora inclui o HTTP status literal de `GET /v1/auth/me` (`401/403`: token TEMP não reconhecido, possível banco diferente; `404`: servidor inesperado/rota ausente; demais: endpoint indisponível), sem corpo da resposta, token, password, usuário ou caminho real. Instruções atualizadas para `start.cmd --lab --lab-dir`, não `run-backend.ps1`.

Dois testes novos exercitam a atestação **de verdade** entre instâncias FastAPI distintas com engines SQLAlchemy independentes: mesma base TEMP deve aceitar sessão sintética; base TEMP diferente (mesmos usernames, mas contas/sessões distintas) deve retornar 401 e impedir o PATCH. O utilitário **não reduz o requisito de atestação**. Revisão Windows pendente.

Procedimento objetivo de reteste:

```powershell
# Encerre quaisquer processos nas portas 8000/5173 antes de iniciar.
# Terminal A: manter aberto e confirmar que aparece lab 1ohg0707
.\start.cmd --lab --lab-dir "$env:TEMP\handoff-qa-006b4-1ohg0707"

# Terminal B: executar apenas STATUS ate obter PASS
$lab = Join-Path $env:TEMP 'handoff-qa-006b4-1ohg0707'
.\.venv\Scripts\python.exe scripts\release_grant_toggle.py --lab $lab --action status
```

Se retornar `HTTP 401` ou `403`, conferir o diretório exibido no terminal A, identificar o processo que escuta na porta 8000 e validar que nenhum outro servidor está ligado a um SQLite diferente. **Não executar revoke/restore enquanto STATUS não for PASS.** Apenas depois disso seguir SEC-02/SEC-03 com a UI do Auditor aberta.


### 18/10/2026 — AUD-01 / SEC-01: executar cenário de auditoria somente em TEMP

O gate Windows no commit `d591b2f` concluiu **125 Pytest aprovados, 1 ignorado,
Ruff, 13 arquitetura frontend, TypeScript e build Vite aprovados**.
`python -m scripts.release_audit_evidence --lab $lab` retornou
`INCOMPLETE`, com **ciclo de grant PASS, escopo final PASS,
LIST=0, DETAIL=0 e DENIED=0**. Esse status não representa regressão
de segurança: faltam os cenários reais do Auditor neste SQLite.

**Executor opcional e explicitamente mutável:**
`scripts/release_audit_scenarios.py` é diferente do relatório read-only:
exige `--confirm-synthetic`, verifica o banco 006b4 do diretório TEMP e
utiliza credenciais sintéticas locais para emitir Bearer via TestClient
ligado **explicitamente** a `$lab/synthetic.db`. Emite apenas
`GET /v1/auth/me` para a API real na porta 8000 para comprovar que
o backend em execução usa esse mesmo banco. Falha de atestação impede
criar qualquer atendimento de prova. Ele então cria **uma conversa e
uma mensagem exclusivamente sintéticas** no laboratório, executa LIST
e DETAIL N1 autorizados (200), tenta LIST e DETAIL N2 (404), verifica
que as respostas negadas não incluem conteúdo/ID da conversa sintética,
e checa acréscimos aos diários via `release_audit_evidence.collect`.
Não imprime tokens, senhas, IDs ou conteúdos. Não precisa alterar grants.

```powershell
# Primeiro, feche o launcher TEMP anterior (Ctrl+C), faça git fetch + ff-only,
# rode start.cmd --check; mantenha start.cmd --lab --lab-dir no terminal A.
$lab = Join-Path $env:TEMP "handoff-qa-006b4-1ohg0707"

# Terminal B, com o backend do mesmo laboratório ativo:
.\.venv\Scripts\python.exe -m scripts.release_audit_scenarios --lab $lab --confirm-synthetic
if ($LASTEXITCODE -ne 0) { throw "Cenario sintetico AUD-01/SEC-01 reprovado" }

# Reexecutar a auditoria estritamente read-only:
.\.venv\Scripts\python.exe -m scripts.release_audit_evidence --lab $lab
if ($LASTEXITCODE -ne 0) { throw "Auditoria sintetica nao concluida" }
```

Este executor gera **evidências de API**, não confirma a UI, teclado,
responsividade ou a segregação visual N1→N2 do navegador. Esses gates
continuam sujeitos à matriz `docs/qa/PR-028-ui-final-gates.md`.

**Estado:** runner e testes adicionais publicados na branch candidata,
mas **não foram executados ainda no Windows**. Manter PR Draft e `main`
intocada até receber evidências.


### 18/10/2026 — Evidências de AUD-01 e SEC-01 concluídas no laboratório

O usuário executou, em `TEMP_SYNTHETIC_006B4_ONLY`, o cenário opt-in
`scripts.release_audit_scenarios` e obteve `result=PASS`,
`live_api_attested=true`, LIST N1=200, DETAIL N1=200,
LIST N2=404 e DETAIL N2=404. O runner registrou 1 nova leitura LIST,
1 nova leitura DETAIL e 2 decisões DENIED. A verificação estritamente
read-only subsequente `scripts.release_audit_evidence` retornou
`result=PASS` com os quatro gates internos PASS, `pending=[]`,
`auditor_has_n1=true`, `auditor_has_n2=false`, 1 evento de
revogação e 1 de restauração. Foi declarada ausência de alterações no
banco original em ambos os relatórios. **Isso não substitui os gates
manuais de interface nem a inspeção separada do banco original.**

**UX-06 revisão posterior ao gate:** o código React de paginação passou
a limpar imediatamente o estado de lista/detalhe ao navegar, a marcar
loading antes de requisitar a página seguinte, a bloquear botões de
paginação durante carregamento e a expor rótulos acessíveis. O teste
de contrato frontend foi ampliado de 13 para 14 casos. **Esta revisão
ainda depende de novo `start.cmd --check` e teste manual no navegador.**
