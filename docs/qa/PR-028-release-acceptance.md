# PR #28 — Plano de homologação manual e segurança da integração

**Estado:** GATES MANUAIS PENDENTES. Este documento registra procedimentos, **não evidências executadas**.  
**Ambiente:** Windows PowerShell 5.1+ / Python 3.12+ / Node/npm local. Sem GitHub Actions ou serviços externos.  
**Candidato:** `feat/006b5b-security-decisions-journal`, revisão de banco **006b4** exclusiva do laboratório sintético.

## 0 — Proteção do banco POC original (bloqueante)

- **Jamais executar** `adopt`, `stamp`, `upgrade`, `upgrade-audit`, `upgrade-security`, `create` ou `--reset-users` em `data/handoff-poc.db`.
- O banco original deve ser usado **somente** em `schema_admin inspect` e `provenance_dry_run`.
- Os scripts de release usam `tempfile.TemporaryDirectory` e `$env:TEMP` para banco e credenciais **independentes**. Não se aplica migração no original.
- **Não iniciar o launcher `start.cmd` para o laboratório temporário:** o launcher possui provisionamento padrão de contas em `data/demo-credentials.txt` e não isola esse arquivo quando `HANDOFF_DB_URL` é sobrescrito. Use os dois launchers temporários gerados pelo script abaixo.
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
| Pytest completo, Ruff, 11 frontend architecture, TypeScript, Vite | Todos aprovados no SHA final |
| `release_probe.py` | JSON `result=PASS`, `database_scope=EPHEMERAL_SYNTHETIC_ONLY`, `table_count=22` |
| `schema_admin inspect` no original | `integrity=ok`, `revision=null`, `table_count=17` |
| `provenance_dry_run` no original | `rows_written=0`, `backfill_applied=false`, `safe_for_history_authorization=false` |

## 2 — Preparar laboratório visual sem tocar no original

```powershell
.\scripts\prepare-main-integration-lab.ps1
```

O script cria um diretório **novo** sob `$env:TEMP\handoff-qa-006b4-<GUID>`, com `synthetic.db`, `synthetic-credentials.txt`, `seed-synthetic.py`, `run-backend.ps1` e `run-web.ps1`. O seed Python é executado a partir do arquivo temporário (não via `python -c`), evitando perda de aspas no Windows PowerShell 5.1. Valida revision `006b4_security_decisions` e 22 tabelas. **Não** gera os arquivos no projeto, não imprime senhas e **não executa** o launcher padrão.

Abra **dois terminais** PowerShell separados e execute os caminhos completos dos launchers exibidos pelo script. No navegador: `http://127.0.0.1:5173`. Leia as contas locais em `synthetic-credentials.txt` (não publicar). O backend usa `HANDOFF_DB_URL` apenas dentro do processo desse terminal; ambos os serviços ficam em `127.0.0.1`.

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
| SEC-01 | Auditor N1 tenta abrir N2; ou usa ID de outra fila | API devolve 404 sem conteúdo/IDs de outra fila; o browser não mantém payload exibido após nova negativa | PENDENTE |
| SEC-02 | ADMIN revoga grant N1 do AUDITOR durante sessão ativa; usuário atualiza | Próxima consulta bloqueia; mensagens previamente carregadas não permanecem exibidas após a tentativa negada | PENDENTE |
| SEC-03 | ADMIN restaura grant; auditor recarrega | Acesso volta a funcionar, sem atravessar fila; logs exibem `GRANT_REVOKED` / `GRANT_ENABLED` | PENDENTE |
| AUD-01 | Verificar `schema_admin --database <synthetic.db> inspect` | `history_access_audit` e `security_decisions` possuem linhas de acesso; original não tem essas tabelas | PENDENTE |

**Observação de segurança:** o UI não pode fazer revogação de grant pelo operador/auditor; fazer alteração somente como ADMIN, e apenas no banco sintético. Não colar tokens Bearer nem dados privados em screenshots. O backend é a autoridade final; limpeza de estado no frontend é defesa adicional.

## 4 — Evidência e critérios de bloqueio da `main`

- Anexar ao PR #28 a saída dos gates, capturas de UX **sem senhas, tokens ou dados reais**, resolução utilizada, perfis e identificação dos testes aprovados.
- Qualquer falha em RBAC, isolamento por fila, persistência de auditoria obrigatória ou alteração do SQLite original **bloqueia merge**.
- Se houver apenas divergência cosmética, registrar como issue separada com prioridade/risco e decisão explícita, sem declarar gate completo aprovado.
- Se houver erro do probe ou teste manual, anexar somente mensagem de falha sanitizada. Não alterar o banco original para reproduzir o problema.
- Após os testes, encerrar API/Vite com Ctrl+C **nos dois terminais** e remover a pasta `handoff-qa-006b4-...` do `$env:TEMP`, que contém as credenciais sintéticas.

## 5 — Estado da revisão de código

Verificada a cadeia Git (`main` ancestral do head), ausência de merge automático e isolamento do schema em `006b4`. Ainda falta inspeção final completa de mudanças em 104 arquivos, análise de concorrência, revisão visual e confirmação dos gates deste novo SHA. **Nenhuma homologação visual foi realizada pelo assistente.**

**Não transformar a aprovação destes gates em declaração de prontidão corporativa:** OIDC/Entra ID, SQL Server, Teams, retenção LGPD e imutabilidade/WORM permanecem fora do escopo desta POC.


### Correção identificada no Windows — 17/10/2026

A primeira execução do preparador criou corretamente o banco sintético 006b4 com 22 tabelas, mas **interrompeu no seed**: `python -c` via PowerShell 5.1 perdeu as aspas da expressão f-string, causando `SyntaxError: invalid syntax` em `fsqlite:///`. Corrigido para criar e executar `seed-synthetic.py` dentro do diretório temporário, sem `-c`. A correção não altera o SQLite original, o FastAPI, o frontend ou as migrações. O novo script **ainda precisa ser reexecutado no Windows** para fechar o gate de preparação de laboratório; a pasta temporária da execução falha não deve ser reutilizada.


## 6 — SEC-02/03: revogação/restauração real com API do laboratório

**Ferramenta:** `scripts/release_grant_toggle.py`. Utiliza credenciais sintéticas sob `$env:TEMP` e verifica que o **ID da conta ADMIN na API é igual ao ID do banco temporário** antes de qualquer mutação; rejeita caminhos fora de `$env:TEMP\handoff-qa-006b4-*`. Nunca imprime senhas nem tokens. O comando modifica **somente** o grant `AUDITOR` da fila `n1` no banco sintético, por `PATCH /v1/admin/queue-grants`.

1. Deixe os dois launchers do laboratório ativos (backend em 8000 e Vite em 5173), **sem iniciar `start.cmd`**. Mantenha o Auditor autenticado no navegador e com uma mensagem **sintética** N1 aberta em `Segmentos verificados`.
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
